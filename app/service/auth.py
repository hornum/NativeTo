import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.cache_redis import redis_client
from app.db.models import User, RefreshToken, UserLanguage
from app.config import settings
from app.db.session import db_dependency
from app.tasks import send_verification_email


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


async def _issue_tokens(db: AsyncSession, user_id: int) -> dict:
    access_token = _create_access_token(user_id)
    refresh_token = _create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            token=_hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
                       + timedelta(days=settings.refresh_token_expire_days),
        )
    )

    return {"access_token": access_token, "refresh_token": refresh_token}


async def register_user(
        db: AsyncSession, username: str, email: str, password: str, native_l: str, learning_l: str, learning_level: str
) -> dict:
    existing = await db.execute(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(username=username, email=email, hashed_password=_hash_password(password))
    db.add(user)
    await db.flush()

    db.add(UserLanguage(user_id=user.id, language=native_l, level="native"))
    db.add(UserLanguage(user_id=user.id, language=learning_l, level=learning_level))

    tokens = await _issue_tokens(db, user.id)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="User already exists")

    verify_token = secrets.token_urlsafe(32)
    try:
        await redis_client.set(f"verify:{verify_token}", user.id, ex=86400)
        send_verification_email.delay(user.email, verify_token)
    except Exception:
        pass # TODO: заменить на logger.warning — письмо не ушло, но аккаунт создан

    return {**tokens, "user_id": user.id}


async def login_user(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    tokens = await _issue_tokens(db, user.id)

    await db.commit()

    return {**tokens, "user_id": user.id}


async def logout_user(db: AsyncSession, refresh_token: str) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == _hash_token(refresh_token))
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
        await db.commit()


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == _hash_token(refresh_token))
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=401, detail="Token not found")

    if token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    user_id = token.user_id
    await db.delete(token)
    tokens = await _issue_tokens(db, user_id)

    await db.commit()

    return tokens


async def get_current_user(
    db: db_dependency,
    token: Annotated[str, Depends(oauth2_bearer)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)

    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_verified_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user


async def verify_user(db: AsyncSession, user_id: int) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="User is already verified")

    user.is_verified = True
    await db.commit()
