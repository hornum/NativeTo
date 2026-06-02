import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, RefreshToken
from app.config import settings
from app.db.session import db_dependency

SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


async def register_user(db: AsyncSession, username: str, email: str, password: str) -> dict:
    existing_username = await db.execute(select(User).where(User.username == username))
    existing_email = await db.execute(select(User).where(User.email == email))
    if existing_username.scalar_one_or_none() or existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(username=username, email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "user_id": user.id}


async def login_user(db: AsyncSession, username: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token, "user_id": user.id}


async def logout_user(db: AsyncSession, refresh_token: str) -> None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    )
    token = result.scalar_one_or_none()
    if token:
        await db.delete(token)
        await db.commit()


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=401, detail="Token not found")

    if token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expired")

    await db.delete(token)
    await db.commit()

    new_refresh = create_refresh_token()
    new_access = create_access_token(token.user_id)

    db.add(
        RefreshToken(
            user_id=token.user_id,
            token=new_refresh,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await db.commit()

    return {"access_token": new_access, "refresh_token": new_refresh}


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError:
        raise credentials_exception

    user = await db.get(User, user_id)

    if user is None:
        raise credentials_exception

    return user
