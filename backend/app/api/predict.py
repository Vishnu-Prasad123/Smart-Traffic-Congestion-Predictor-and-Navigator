"""backend/app/api/predict.py"""
from fastapi import APIRouter, HTTPException
from app.schemas.traffic import PredictionRequest, PredictionResponse, ProbabilityBreakdown, CongestionLevel
from app.services import ml_service

router = APIRouter()

@router.post("/predict-congestion", response_model=PredictionResponse)
async def predict_congestion(request: PredictionRequest):
    try:
        result = ml_service.predict({
            "traffic_volume": request.traffic_volume,
            "average_speed": request.average_speed,
            "travel_time_index": request.travel_time_index,
            "road_capacity_utilization": request.road_capacity_utilization,
            "incident_reports": request.incident_reports,
            "day_of_week": request.day_of_week,
            "month": request.month,
            "weather_conditions": request.weather_conditions.value,
            "roadwork_activity": request.roadwork_activity.value,
        })
        proba = result.get("probabilities", {"LOW": 0.33, "MEDIUM": 0.34, "HIGH": 0.33})
        return PredictionResponse(
            congestion_level=CongestionLevel(result["congestion_level"]),
            probabilities=ProbabilityBreakdown(**proba),
            confidence=result.get("confidence", 0.5),
            is_demo_mode=result.get("is_demo_mode", False),
            warning=result.get("warning"),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
