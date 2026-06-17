from fastapi import HTTPException
from sqlalchemy import select, or_, and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import User, UserLanguage
from app.schemas.users import UserProfile, UserLanguageSchema, UserLanguageLevel


def build_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id, username=user.username, name=user.name, sex=user.sex,
        email=user.email, avatar_url=user.avatar_url,
        bio=user.bio, country=user.country, age=user.age,
        languages=[UserLanguageSchema(id=l.id, language=l.language, level=l.level) for l in user.languages]
    )


async def get_user_model(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .options(joinedload(User.languages))
        .where(User.id == user_id)
    )
    return result.unique().scalar_one_or_none()


async def get_user_with_langs(db: AsyncSession, user_id: int) -> UserProfile | None:
    result = await db.execute(
        select(User)
        .options(joinedload(User.languages))
        .where(User.id == user_id)
    )
    user = result.unique().scalar_one_or_none()
    if user is None:
        return None

    return build_profile(user)


async def delete_user_lang(db: AsyncSession, user_id: int, lang_id: int) -> None:
    user = await get_user_with_langs(db, user_id)
    lang_to_delete = next((l for l in user.languages if l.id == lang_id), None)
    if not lang_to_delete:
        raise HTTPException(status_code=404, detail="Language not found")

    remaining = [l for l in user.languages if l.id != lang_id]
    has_native = any(l.level == "native" for l in remaining)
    has_learning = any(l.level != "native" for l in remaining)

    if not has_native and not has_learning:
        raise HTTPException(status_code=400, detail="At least one native and one learning language is required")

    await db.execute(
        delete(UserLanguage).where(and_(UserLanguage.user_id == user_id,UserLanguage.id == lang_id))
    )
    await db.commit()


async def patch_user_data(db: AsyncSession, user_id: int, data: dict) -> UserProfile:
    user = await get_user_model(db, user_id)

    if data.get("bio") is not None:
        user.bio = data["bio"]
    if data.get("name") is not None:
        user.name = data["name"]
    if data.get("country") is not None:
        user.country = data["country"]
    if data.get("age") is not None:
        user.age = data["age"]
    if data.get("sex") is not None:
        user.sex = data["sex"]

    if data.get("username") is not None:
        new_username = data["username"]
        existing_user = await db.execute(
            select(User).where(User.username == new_username, User.id != user_id)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already exists")

        user.username = data["username"]

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Username already exists")

    return build_profile(user)


async def add_language(db: AsyncSession, user_id: int, language: str, level: UserLanguageLevel) -> UserLanguageSchema:
    existing_l_name = await db.execute(
        select(UserLanguage).where(UserLanguage.user_id == user_id, UserLanguage.language == language)
    )
    if existing_l_name.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Language already exists")

    if level == "native":
        existing_native_l = await db.execute(
            select(UserLanguage)
            .where(UserLanguage.user_id == user_id, UserLanguage.level == UserLanguageLevel.native)
        )
        if existing_native_l.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Native language already set")

    new_language = UserLanguage(user_id=user_id, language=language, level=level)
    db.add(new_language)
    await db.commit()
    return UserLanguageSchema(id=new_language.id, language=new_language.language, level=new_language.level)
