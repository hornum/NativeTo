from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select

from app.db.models import User
from app.db.session import db_dependency
from app.schemas.users import UserProfile, UserLanguageSchema, EditUserProfile, AddLanguage
from app.service.auth import get_current_user
from app.service.users import get_user_with_langs, get_users_catalog, patch_user_data, add_language, delete_user_lang

router = APIRouter(prefix="/api/v1/users", tags=["Users"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.get("/me")
async def get_me(db: db_dependency, curr_user: user_dependency) -> UserProfile:
    return await get_user_with_langs(db, curr_user.id)

@router.patch("/me")
async def patch_me(db: db_dependency, curr_user: user_dependency, data: EditUserProfile) -> UserProfile:
    return await patch_user_data(db, curr_user.id, data.model_dump(exclude_none=True))


@router.get("/catalog")
async def get_catalog(db: db_dependency, curr_user: user_dependency):
    return await get_users_catalog(db, curr_user.id)

@router.post("/me/languages")
async def add_user_language(db: db_dependency, curr_user: user_dependency, lang: AddLanguage) -> UserLanguageSchema:
    return await add_language(db, curr_user.id, lang.language, lang.level)

@router.delete("/me/languages", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_language(db: db_dependency, curr_user: user_dependency, lang_id: int):
    await delete_user_lang(db, curr_user.id, lang_id)
