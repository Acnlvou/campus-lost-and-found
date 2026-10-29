from ..core.config import RUNTIME_DIR
from .base import Base
from .seed import seed
from .session import SessionLocal, engine

# 注册模型到 Base.metadata，确保 create_all 与 alembic autogenerate 能看到全部表
from . import models  # noqa: F401


def init_db(seed_data: bool = True) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    if seed_data:
        with SessionLocal() as db:
            seed(db)
