import logging

import aiosmtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_reset_email(to_email: str, token: str) -> bool:
    reset_link = f"{settings.APP_URL}/auth/reset-password-form?token={token}"

    text_content = f"""
    Сброс пароля

    Вы запросили сброс пароля для вашего аккаунта.

    Перейдите по ссылке, чтобы установить новый пароль:
    {reset_link}

    Ссылка действительна в течение 1 часа.

    Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
    """

    msg = MIMEText(text_content, "plain")
    msg["Subject"] = "Сброс пароля - Mafia Game"
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            timeout=30,
        )
        return True
    except (aiosmtplib.SMTPException, OSError, TimeoutError) as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        return False