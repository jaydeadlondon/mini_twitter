import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

likes_table = Table(
    "likes",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("post_id", UUID(as_uuid=True), ForeignKey("posts.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class Post(Base):
    __tablename__ = "posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    author = relationship("User", backref="posts")

    liked_by = relationship("User", secondary=likes_table, backref="liked_posts")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    post_id = Column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False, index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User", backref="comments")
    post = relationship("Post", backref="comments")


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)

    file_path = Column(String, nullable=False)
    filename = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", backref="media")
