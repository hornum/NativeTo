from enum import Enum

from pydantic import BaseModel, EmailStr


class UserLanguageLevel(str, Enum):
    native = "native"
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class UserLanguageSchema(BaseModel):
    id: int
    language: str
    level: UserLanguageLevel


class AddLanguage(BaseModel):
    language: str
    level: UserLanguageLevel


class UserProfile(BaseModel):
    id: int
    username: str
    name: str
    email: str
    avatar_url: str | None = None
    bio: str | None = None
    country: str | None = None
    age: int | None = None
    languages: list[UserLanguageSchema] = []


class EditUserProfile(BaseModel):
    username: str | None = None
    name: str | None = None
    bio: str | None = None
    country: str | None = None
    age: int | None = None
