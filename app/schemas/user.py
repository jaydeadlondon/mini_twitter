from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr
    bio: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
