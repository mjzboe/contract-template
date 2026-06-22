import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contract"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    UPLOAD_DIR: str = "./uploads"
    CORS_ORIGINS: str = "http://localhost:5173"
    LIBREOFFICE_PATH: str = "/usr/bin/libreoffice"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 将 UPLOAD_DIR 转为绝对路径，避免工作目录变化导致文件找不到
        if not os.path.isabs(self.UPLOAD_DIR):
            self.UPLOAD_DIR = os.path.abspath(self.UPLOAD_DIR)


settings = Settings()
