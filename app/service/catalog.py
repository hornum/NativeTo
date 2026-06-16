from fastapi import HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import User, UserLanguage
from app.schemas.catalog import CatalogFilters
from app.schemas.users import UserProfile
from app.service.users import get_user_with_langs, build_profile


async def get_users_catalog(db: AsyncSession, user_id: int, filters: CatalogFilters) -> list[UserProfile]:
    me = await get_user_with_langs(db, user_id)

    if me is None:
        raise HTTPException(status_code=404, detail="User not found")

    my_native = [l.language for l in me.languages if l.level == "native"]
    my_learning = [l.language for l in me.languages if l.level != "native"]

    if not my_native and not my_learning:
        return []

    query = (
        select(User)
        .options(joinedload(User.languages))
        .join(User.languages)
        .where(
            User.id != user_id,
            or_(
                and_(UserLanguage.level != "native", UserLanguage.language.in_(my_native)),
                and_(UserLanguage.level == "native", UserLanguage.language.in_(my_learning)),
            )
        )
    )
    if filters.country is not None:
        query = query.where(User.country == filters.country)
    if filters.min_age is not None:
        query = query.where(User.age >= filters.min_age)
    if filters.max_age is not None:
        query = query.where(User.age <= filters.max_age)

    query = query.distinct().limit(filters.limit).offset(filters.offset)

    result = await db.execute(query)
    users = result.unique().scalars().all()
    return [build_profile(u) for u in users]
