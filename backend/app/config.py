import os
import re

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


def resolve_file_path(stored_path: str) -> str:
    """将数据库中存储的文件路径映射为当前环境的有效路径。

    处理场景：模板在本地 Windows 上传（路径如 D:\\project\\...\\uploads\\xxx.docx），
    但运行在 Docker Linux 容器中（路径如 /app/uploads/xxx.docx）。
    只要文件名相同，就映射到当前 UPLOAD_DIR 下。
    """
    if os.path.exists(stored_path):
        return stored_path

    filename = os.path.basename(stored_path)
    if not filename:
        return stored_path

    # 尝试在当前 UPLOAD_DIR 下按相对路径查找
    # stored_path 可能是 .../uploads/contracts/xxx.docx 或 .../uploads/xxx.docx
    upload_dir = settings.UPLOAD_DIR
    rel = _extract_upload_relative(stored_path)
    if rel:
        candidate = os.path.join(upload_dir, rel)
        if os.path.exists(candidate):
            return candidate

    # 直接在 UPLOAD_DIR 下按文件名查找
    candidate = os.path.join(upload_dir, filename)
    if os.path.exists(candidate):
        return candidate

    # 在 UPLOAD_DIR 子目录中也找一下
    for root, _dirs, files in os.walk(upload_dir):
        if filename in files:
            return os.path.join(root, filename)

    return stored_path


# 匹配 uploads/ 后面的相对路径部分（如 contracts/xxx.docx 或 xxx.docx）
_UPLOAD_RE = re.compile(r'[\\/]uploads[\\/](.+)$')


def _extract_upload_relative(stored_path: str) -> str | None:
    """从存储路径中提取 uploads/ 之后的相对路径"""
    # 统一用 / 分隔来匹配
    normalized = stored_path.replace("\\", "/")
    m = _UPLOAD_RE.search(normalized)
    if m:
        return m.group(1)
    return None


settings = Settings()
