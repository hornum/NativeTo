from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.db.cache_redis import redis_client
from app.db.session import db_dependency
from app.schemas.auth import UserRegister, TokenResponse, RefreshRequest, TokenPair
from app.service.auth import register_user, refresh_tokens, logout_user, login_user, verify_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(db: db_dependency, data: UserRegister):
    return await register_user(
        db=db,
        username=data.username,
        email=str(data.email),
        password=data.password,
        native_l=data.native_language,
        learning_l=data.learning_language,
        learning_level=data.learning_level,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    return await login_user(db, data.username, data.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: db_dependency):
    return await refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout(body: RefreshRequest, db: db_dependency):
    await logout_user(db, body.refresh_token)
    return {"message": "Successfully logged out"}


@router.get("/verify")
async def verify(db: db_dependency, token: str) -> dict:
    verification_uid = await redis_client.get(f"verify:{token}")
    if verification_uid is None:
        raise HTTPException(401, detail="Invalid verification token")

    user_id = int(verification_uid)
    await verify_user(db, user_id)
    await redis_client.delete(f"verify:{token}")
    return {"message": "Email verified"}
