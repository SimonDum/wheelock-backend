from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
from app.schemas import DefectReport


# Configuration email
email_conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

fm = FastMail(email_conf)


async def send_email_notification(report: DefectReport):
    """Envoie un email à l'admin pour signaler un socle défectueux"""
    html_content = f"""
    <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #f5f5f5;">
            <div style="background-color: #6c757d; color: white; padding: 15px; border-bottom: 3px solid #495057;">
                <h2 style="margin: 0; font-size: 18px;">SIGNALEMENT DE SOCLE DEFECTUEUX</h2>
            </div>
            
            <div style="background-color: white; padding: 20px; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong>ID du socle</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            {report.stand_id}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong>Localisation</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            {report.location or "Non precisee"}
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #6c757d; color: #adb5bd; padding: 10px; text-align: center; font-size: 12px;">
                <p style="margin: 0;">Wheelock Application - Notification automatique</p>
            </div>
        </body>
    </html>
    """
    
    message = MessageSchema(
        subject=f"ALERTE - Socle defectueux - {report.stand_id}",
        recipients=[settings.ADMIN_EMAIL],
        body=html_content,
        subtype=MessageType.html,
    )
    
    await fm.send_message(message)
