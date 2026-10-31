"""backend/app/api/model.py"""
from fastapi import APIRouter, HTTPException
from app.schemas.traffic import ModelMetricsResponse
from app.services import ml_service, traffic_service
from app.core.config import settings

router = APIRouter()

@router.get("/model/metrics", response_model=ModelMetricsResponse)
async def model_metrics():
    metrics = ml_service.get_metrics()
    fi = ml_service.get_feature_importance()

    stats_path = settings.FEATURE_STATS_PATH
    is_demo = False
    total_records = 0
    if stats_path.exists():
        import json
        with open(stats_path) as f:
            stats = json.load(f)
        is_demo = stats.get("is_demo_mode", False)
        total_records = stats.get("total_records", 0)

    if metrics is None:
        return ModelMetricsResponse(
            model_trained=False,
            is_demo_mode=is_demo,
            training_message="Model has not been trained yet. Run: cd ml && python train.py && python evaluate.py",
        )

    return ModelMetricsResponse(
        model_trained=True,
        model=metrics.get("model"),
        accuracy=metrics.get("accuracy"),
        macro_f1=metrics.get("macro_f1"),
        precision_per_class=metrics.get("precision_per_class"),
        recall_per_class=metrics.get("recall_per_class"),
        f1_per_class=metrics.get("f1_per_class"),
        confusion_matrix=metrics.get("confusion_matrix"),
        classes=metrics.get("classes"),
        test_set_size=metrics.get("test_set_size"),
        total_records=metrics.get("total_records", total_records),
        n_features=metrics.get("n_features"),
        feature_names=metrics.get("feature_names"),
        feature_importance=fi,
        is_demo_mode=is_demo,
        training_message="Model trained and evaluated on held-out test set.",
    )
