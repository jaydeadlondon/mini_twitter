from typing import Optional
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int

    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if isinstance(v, str):
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data.get("POSTGRES_USER"),
                password=info.data.get("POSTGRES_PASSWORD"),
                host=info.data.get("POSTGRES_SERVER"),
                port=info.data.get("POSTGRES_PORT"),
                path=info.data.get("POSTGRES_DB") or "",
            )
        )

    SECRET_KEY: str
    ALGORITHM: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
