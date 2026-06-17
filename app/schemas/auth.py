from pydantic import BaseModel, EmailStr

from app.schemas.users import UserSex


class UserRegister(BaseModel):
    username: str
    name: str
    sex: UserSex = UserSex.other
    password: str
    native_language: str
    learning_language: str
    learning_level: str = "beginner"
    email: EmailStr


class UserLogin(BaseModel):
    username: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class TokenResponse(TokenPair):
    user_id: int


class RefreshRequest(BaseModel):
    refresh_token: str
