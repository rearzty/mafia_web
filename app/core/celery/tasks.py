import logging

from .app import celery_app
import asyncio

from app.core.email import send_reset_email


@celery_app.task
def send_reset_email_task(to_email: str, token: str):
    logging.info("send_reset_email")
    return asyncio.run(send_reset_email(to_email, token))
