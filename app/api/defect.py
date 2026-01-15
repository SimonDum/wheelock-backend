from fastapi import APIRouter, BackgroundTasks
from app.schemas import DefectReport
from app.core.email import send_email_notification

router = APIRouter(prefix="/api", tags=["defect"])


@router.post("/report-defect")
async def report_defect(report: DefectReport, background_tasks: BackgroundTasks):
    """
    Endpoint pour signaler un socle defectueux.
    Envoie automatiquement un email a l'admin.
    """
    background_tasks.add_task(send_email_notification, report)
    
    return {
        "status": "success",
        "message": "Signalement enregistre. L'administrateur sera notifie.",
        "stand_id": report.stand_id
    }
