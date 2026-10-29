from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "v1.0-rc"
ALLOW_SELF_CLAIM = True
CATEGORIES = ("数码设备", "证件卡片", "学习用品", "生活用品", "其他")
LABELS = {
    "OPEN": "待认领",
    "CLAIMED": "已认领",
    "PENDING": "待审核",
    "APPROVED": "已通过",
    "REJECTED": "已拒绝",
    "CLOSED": "已关闭",
    "FOUND": "招领",
    "LOST": "寻物",
}

# backend/app/core/config.py -> parents[0]=core, [1]=app, [2]=backend, [3]=项目根
BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
RUNTIME_DIR = BACKEND_DIR / "data" / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DATABASE_URL = f"sqlite:///{(RUNTIME_DIR / 'campus.sqlite').as_posix()}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CAMPUS_",
        extra="ignore",
    )

    app_name: str = "校园失物招领系统"
    api_prefix: str = "/api"
    database_url: str = DEFAULT_DATABASE_URL
    secret_key: str = ""
    seed: bool = True
    frontend_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
