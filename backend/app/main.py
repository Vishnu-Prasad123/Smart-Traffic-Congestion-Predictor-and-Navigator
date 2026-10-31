"""
backend/app/main.py
--------------------
FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import health, predict, routes, traffic, model
from app.services import ml_service, routing_service, traffic_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("=== Smart Traffic Navigator API starting up ===")

    # Load ML model
    model_ok = ml_service.load_model()
    logger.info(f"ML Model loaded: {model_ok} | Demo mode: {ml_service.is_demo_mode()}")

    # Load road graph (may download from OSMnx on first run)
    graph_ok = routing_service.load_graph()
    logger.info(f"Road graph loaded: {graph_ok}")

    # Load traffic data
    data_ok = traffic_service.load_traffic_data()
    logger.info(f"Traffic data loaded: {data_ok}")

    logger.info("=== Startup complete. API ready. ===")
    yield
    logger.info("=== Shutting down ===")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="""
Smart Traffic Congestion Predictor & Navigator - Bengaluru, India.

Combines Random Forest ML for congestion estimation with A* routing on the
Bengaluru road network (OpenStreetMap). See /docs for interactive API docs.

**Important**: Road-level congestion is estimated from area-level data.
This is NOT a real-time traffic monitoring system.
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(predict.router, prefix="/api", tags=["Prediction"])
app.include_router(routes.router, prefix="/api", tags=["Routing"])
app.include_router(traffic.router, prefix="/api", tags=["Analytics"])
app.include_router(model.router, prefix="/api", tags=["Model"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "status": "running",
    }
