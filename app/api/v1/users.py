from typing import Annotated

from fastapi import APIRouter, Depends, status, UploadFile

from app.db.models import User
from app.db.session import db_dependency
from app.schemas.users import UserProfile, UserLanguageSchema, EditUserProfile, AddLanguage
from app.service.auth import get_current_user
from app.service.avatar import upload_avatar_service
from app.service.presence import get_status
from app.service.users import get_user_with_langs, patch_user_data, add_language, delete_user_lang

router = APIRouter(prefix="/api/v1/users", tags=["Users"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.get("/me")
async def get_me(db: db_dependency, curr_user: user_dependency) -> UserProfile:
    return await get_user_with_langs(db, curr_user.id)


@router.patch("/me")
async def patch_me(db: db_dependency, curr_user: user_dependency, data: EditUserProfile) -> UserProfile:
    return await patch_user_data(db, curr_user.id, data.model_dump(exclude_none=True))


@router.post("/me/languages")
async def add_user_language(db: db_dependency, curr_user: user_dependency, lang: AddLanguage) -> UserLanguageSchema:
    return await add_language(db, curr_user.id, lang.language, lang.level)

@router.delete("/me/languages", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_language(db: db_dependency, curr_user: user_dependency, lang_id: int):
    await delete_user_lang(db, curr_user.id, lang_id)


@router.get("/{user_id}/status")
async def user_status(user_id: int, curr_user: user_dependency):
    return await get_status(user_id)


@router.put("/me/avatar")
async def upload_avatar(db: db_dependency, curr_user: user_dependency, file: UploadFile):
    url = await upload_avatar_service(db, curr_user.id, file)
    return url
