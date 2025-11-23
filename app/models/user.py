import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

follows_table = Table(
    "follows",
    Base.metadata,
    Column("follower_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("followed_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    following = relationship(
        "User",
        secondary=follows_table,
        primaryjoin=id == follows_table.c.follower_id,
        secondaryjoin=id == follows_table.c.followed_id,
        backref="followers",
    )
