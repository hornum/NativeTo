import logging

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)


@celery_app.task
def send_verification_email(email: str, token: str) -> None:
    verification_link = f"{settings.BASE_URL}/api/v1/auth/verify?token={token}"
    logger.info("[EMAIL] Verification link for %s: %s", email, verification_link)
