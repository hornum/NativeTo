from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.models import User
from app.db.session import db_dependency
from app.schemas.catalog import CatalogFilters
from app.service.auth import get_current_user

from app.service.catalog import get_users_catalog

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])
user_dependency = Annotated[User, Depends(get_current_user)]


@router.get("")
async def get_catalog(
        db: db_dependency,
        curr_user: user_dependency,
        filters: Annotated[CatalogFilters, Depends()],
):
    return await get_users_catalog(db, curr_user.id, filters)
