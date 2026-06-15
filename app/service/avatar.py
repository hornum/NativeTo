from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import User
from app.db.s3 import s3_client

ALLOWED_FILE_TYPES = {"image/jpeg", "image/png", "image/webp"}


async def upload_avatar_service(db: AsyncSession, user_id: int, file: UploadFile):
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    ext = file.filename.removeprefix("image/")
    key = f"user_{user_id}.{ext}"

    s3_client.upload_fileobj(
        file.file,
        settings.MINIO_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type},
    )

    url = f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{key}"

    user = await db.get(User, user_id)
    user.avatar_url = url
    await db.commit()

    return url
