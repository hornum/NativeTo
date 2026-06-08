from app.celery_app import celery_app

from app.config import settings


@celery_app.task
def send_verification_email(email: str, token: str) -> None:
    verification_link = f"{settings.BASE_URL}/api/v1/auth/verify?token={token}"
    print(f"[EMAIL] Verification link for {email}: {verification_link}")
