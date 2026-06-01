import smtplib
import socket
from email.mime.text import MIMEText
from app.core.config import settings

def send_reset_email(to_email: str, token: str) -> bool:
    reset_link = f"http://localhost:8000/auth/reset-password-form?token={token}"

    subject = "Сброс пароля - Mafia Game"
    text_content = f"""
    Сброс пароля

    Вы запросили сброс пароля для вашего аккаунта.

    Перейдите по ссылке, чтобы установить новый пароль:
    {reset_link}

    Ссылка действительна в течение 1 часа.

    Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
    """

    msg = MIMEText(text_content, "plain")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
        return True
    except (smtplib.SMTPException, socket.error, TimeoutError) as e:
        
        return False