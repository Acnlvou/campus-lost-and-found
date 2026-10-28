from fastapi import APIRouter

from ...core.config import VERSION

router = APIRouter()


@router.get("/health", summary="健康检查")
def health_check() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
