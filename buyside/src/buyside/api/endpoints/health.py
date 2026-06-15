from fastapi import APIRouter

router = APIRouter()


@router.get("", status_code=200)
async def health_check() -> dict[str, str]:
    """Verify application availability."""
    return {"status": "healthy"}
