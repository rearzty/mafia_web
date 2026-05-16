import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def send_reset_email(to_email: str, token: str):
    reset_link = f"http://localhost:8000/auth/reset-password-form?token={token}"
    subject = "Сброс пароля - Mafia Game"
    text_content = f"""
    Сброс пароля

    Вы запросили сброс пароля для вашего аккаунта.

    Перейдите по ссылке ниже, чтобы установить новый пароль:
    {reset_link}

    Ссылка действительна в течение 1 часа.

    Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #333;">Сброс пароля</h2>
        <p>Вы запросили сброс пароля для вашего аккаунта в игре <strong>Mafia Game</strong>.</p>
        <p>Нажмите на кнопку ниже, чтобы установить новый пароль:</p>
        <p>
            <a href="{reset_link}" 
               style="display: inline-block; 
                      padding: 12px 24px; 
                      background-color: #007bff; 
                      color: white; 
                      text-decoration: none; 
                      border-radius: 5px;
                      margin: 20px 0;">
                Сбросить пароль
            </a>
        </p>
        <p>Или скопируйте ссылку в браузер:</p>
        <code style="background: #f4f4f4; padding: 10px; display: block; word-break: break-all;">
            {reset_link}
        </code>
        <p><strong>Ссылка действительна в течение 1 часа.</strong></p>
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
        <p style="color: #666; font-size: 12px;">
            Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
        </p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        # Отправляем через SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        return False
