from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from app.schemas import DefectReport
from app.core.email import send_email_notification
from app.database import get_db
from app import models

router = APIRouter(prefix="/api/public", tags=["defect"])
logger = logging.getLogger(__name__)


@router.post("/report-defect")
async def report_defect(
    report: DefectReport,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint pour signaler un groupe de docks défectueux.
    Persiste le signalement en base et envoie un email à l'admin.
    """
    # Vérifier que le groupe existe
    group = await db.get(models.DocksGroup, report.group_id)
    if not group:
        raise HTTPException(
            status_code=404,
            detail=f"Le groupe de docks avec l'ID {report.group_id} n'existe pas"
        )
    
    # Créer et sauvegarder le rapport en base de données
    try:
        defect_report = models.DefectReport(
            group_id=report.group_id,
            group_name=group.name,  # Sauvegarde du nom pour l'historique
            location=report.location,
            status="pending"
        )
        db.add(defect_report)
        await db.commit()
        await db.refresh(defect_report)
        logger.info(f"Défaut signalé pour le groupe {group.name} (ID: {report.group_id}, rapport: {defect_report.id})")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du défaut pour le groupe {report.group_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'enregistrement du signalement"
        )

    # Envoyer l'email en arrière-plan (seulement en production)
    try:
        from app.core.config import settings
        if settings.ENV == "production":
            background_tasks.add_task(send_email_notification, report, group.name)
            logger.info(f"Email de notification programmé pour le groupe {group.name}")
        else:
            logger.info(f"Email désactivé en {settings.ENV}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email pour le groupe {report.group_id}: {e}")

    return {
        "status": "success",
        "message": "Signalement enregistré. L'administrateur sera notifié.",
        "group_id": report.group_id,
        "group_name": group.name,
        "report_id": defect_report.id
    }