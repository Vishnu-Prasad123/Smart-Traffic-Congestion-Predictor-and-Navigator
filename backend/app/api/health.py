"""backend/app/api/health.py"""
from fastapi import APIRouter
from app.schemas.traffic import HealthResponse
from app.services import ml_service, routing_service
from app.core.config import settings

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        model_loaded=ml_service.is_model_loaded(),
        graph_loaded=routing_service.is_graph_loaded(),
        demo_mode=routing_service.is_demo_graph() or ml_service.is_demo_mode(),
        version=settings.VERSION,
    )