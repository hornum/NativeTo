from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.db.session import db_dependency
from app.schemas.auth import UserRegister, TokenResponse, RefreshRequest
from app.service.auth import register_user, refresh_tokens, logout_user, login_user

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
async def register(db: db_dependency, data: UserRegister):
    return await register_user(db, data.username, str(data.email), data.password)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: db_dependency,
):
    return await login_user(db, data.username, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: db_dependency):
    return await refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout(body: RefreshRequest, db: db_dependency):
    await logout_user(db, body.refresh_token)
    return {"message": "Successfully logged out"}
