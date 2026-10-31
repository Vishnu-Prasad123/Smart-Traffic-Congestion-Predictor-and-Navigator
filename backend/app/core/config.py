"""
backend/app/core/config.py
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings:
    APP_NAME: str = "Smart Traffic Navigator API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    ).split(",")
    MODEL_PATH: Path = BASE_DIR / "ml" / "artifacts" / "model.joblib"
    PREPROCESSOR_PATH: Path = BASE_DIR / "ml" / "artifacts" / "preprocessor.joblib"
    METRICS_PATH: Path = BASE_DIR / "ml" / "artifacts" / "metrics.json"
    FEATURE_IMPORTANCE_PATH: Path = BASE_DIR / "ml" / "artifacts" / "feature_importance.json"
    PROCESSED_DATA_PATH: Path = BASE_DIR / "data" / "processed" / "cleaned_traffic.csv"
    FEATURE_STATS_PATH: Path = BASE_DIR / "data" / "processed" / "feature_stats.json"
    GRAPH_PATH: Path = BASE_DIR / "data" / "maps" / "bengaluru_graph.graphml"
    OSMNX_PLACE: str = "Koramangala, Bengaluru, Karnataka, India"
    OSMNX_RADIUS_M: int = 5000
    DEFAULT_SPEED_KMH: float = 30.0

settings = Settings()
