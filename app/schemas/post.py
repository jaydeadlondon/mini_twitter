from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class MediaResponse(BaseModel):
    id: UUID
    url: str
    model_config = ConfigDict(from_attributes=True)


class PostCreate(BaseModel):
    content: str
    media_ids: list[UUID] = []


class PostResponse(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    author_username: str

    media: list[MediaResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: UUID
    content: str
    author_username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
