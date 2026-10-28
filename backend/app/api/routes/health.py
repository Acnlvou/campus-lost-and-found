from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="健康检查")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
