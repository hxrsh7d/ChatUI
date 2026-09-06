from fastapi import APIRouter

from metrics import metrics

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    return metrics.snapshot()
