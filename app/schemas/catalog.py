from pydantic import BaseModel, Field


class CatalogFilters(BaseModel):
    country: str | None = None
    min_age: int | None = Field(None, ge=0)
    max_age: int | None = Field(None, ge=0, le=100)
    gender: str | None = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
