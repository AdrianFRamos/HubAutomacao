import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    REDIS_URL: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    APP_PORT: int = Field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    SECRET_KEY: str = Field(default_factory=lambda: os.getenv("SECRET_KEY", "change-me"))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")))
    ALGORITHM: str = Field(default_factory=lambda: os.getenv("ALGORITHM", "HS256"))
    WORKSPACE_ROOT: str = Field(default_factory=lambda: os.getenv("WORKSPACE_ROOT", "/srv/automations"))
    DB_USER: str = Field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    DB_PASSWORD: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    DB_HOST: str = Field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    DB_PORT: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    DB_NAME: str = Field(default_factory=lambda: os.getenv("DB_NAME", "automacao"))
    @property
    def assembled_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
settings = Settings()
