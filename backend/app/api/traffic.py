"""backend/app/api/traffic.py"""
from fastapi import APIRouter, HTTPException
from app.schemas.traffic import TrafficSummaryResponse, AreaTrafficStat
from app.services import traffic_service

router = APIRouter()

@router.get("/traffic/summary", response_model=TrafficSummaryResponse)
async def traffic_summary():
    try:
        data = traffic_service.get_summary()
        top_areas = [AreaTrafficStat(**a) for a in data.get("top_areas", [])]
        return TrafficSummaryResponse(
            total_records=data["total_records"],
            is_demo_mode=data["is_demo_mode"],
            congestion_distribution=data["congestion_distribution"],
            avg_volume_by_day=data["avg_volume_by_day"],
            avg_speed_by_congestion=data["avg_speed_by_congestion"],
            top_areas=top_areas,
            volume_over_time=data["volume_over_time"],
            date_range=data["date_range"],
            data_note=data["data_note"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute traffic summary: {str(e)}")


@router.get("/traffic/diagnostic-report")
async def diagnostic_report():
    """
    Returns complete diagnostic analysis of dataset distribution, model metrics,
    road feature mappings, and defensible route classification rules.
    """
    try:
        from app.services import routing_service
        return routing_service.get_diagnostic_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate diagnostic report: {str(e)}")

