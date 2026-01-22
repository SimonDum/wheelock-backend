from fastapi import APIRouter, BackgroundTasks, Depends
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
    Endpoint pour signaler un socle defectueux.
    Persiste le signalement en base et envoie un email a l'admin.
    """
    # Créer et sauvegarder le rapport en base de données
    try:
        defect_report = models.DefectReport(
            stand_id=report.stand_id,
            location=report.location,
            status="pending"
        )
        db.add(defect_report)
        await db.commit()
        await db.refresh(defect_report)
        logger.info(f"Défaut signalé pour le stand {report.stand_id} (id rapport: {defect_report.id})")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du défaut pour le stand {report.stand_id}: {e}")
        return {
            "status": "error",
            "message": "Erreur lors de l'enregistrement du signalement.",
            "stand_id": report.stand_id
        }

    # Envoyer l'email en arrière-plan
    try:
        background_tasks.add_task(send_email_notification, report)
        logger.info(f"Email de notification programmé pour le stand {report.stand_id}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email pour le stand {report.stand_id}: {e}")

    return {
        "status": "success",
        "message": "Signalement enregistre. L'administrateur sera notifie.",
        "stand_id": report.stand_id,
        "report_id": defect_report.id
    }