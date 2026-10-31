"""backend/app/api/routes.py"""
from fastapi import APIRouter, HTTPException
from app.schemas.traffic import RouteRequest, RouteResponse, RouteInfo, RouteSegment, Coordinate, CongestionLevel
from app.services import routing_service, traffic_service

router = APIRouter()

@router.post("/routes", response_model=RouteResponse)
async def calculate_routes(request: RouteRequest):
    if not routing_service.is_graph_loaded():
        raise HTTPException(status_code=503, detail="Road graph not yet loaded. Please try again in a moment.")
    try:
        congestion_lookup = traffic_service.get_area_congestion_lookup()
        result = routing_service.find_routes(
            src_lat=request.source.lat,
            src_lng=request.source.lng,
            dst_lat=request.destination.lat,
            dst_lng=request.destination.lng,
            avoid_congestion=request.avoid_congestion,
            congestion_lookup=congestion_lookup,
        )
        routes = []
        for r in result["routes"]:
            segs = []
            for s in r.get("segments", []):
                cong = s.get("congestion_estimate")
                segs.append(RouteSegment(
                    coordinates=s["coordinates"],
                    distance_m=s["distance_m"],
                    estimated_time_min=s["estimated_time_min"],
                    congestion_estimate=CongestionLevel(cong) if cong else None,
                    congestion_confidence=s.get("congestion_confidence"),
                    congestion_note=s.get("congestion_note", "Predicted by Random Forest from road attributes"),
                    name=s.get("name"),
                    highway=s.get("highway"),
                    speed_kph=s.get("speed_kph"),
                ))
            cong_level = r.get("congestion_level")
            routes.append(RouteInfo(
                route_id=r["route_id"],
                label=r["label"],
                color=r["color"],
                total_distance_km=r["total_distance_km"],
                total_time_min=r["total_time_min"],
                segments=segs,
                geometry=r["geometry"],
                congestion_level=CongestionLevel(cong_level) if cong_level else None,
                congestion_score=r.get("congestion_score"),
                congestion_breakdown=r.get("congestion_breakdown"),
                congestion_cost=r.get("congestion_cost"),
                recommendation_reason=r.get("recommendation_reason"),
                is_recommended=r.get("is_recommended", False),
                dominant_rule=r.get("dominant_rule"),
                node_count=r["node_count"],
            ))
        return RouteResponse(
            status="success",
            routes=routes,
            source_requested=request.source,
            destination_requested=request.destination,
            source_snapped=Coordinate(**result["source_snapped"]),
            destination_snapped=Coordinate(**result["destination_snapped"]),
            source_snap_distance_m=result.get("source_snap_distance_m", 0.0),
            destination_snap_distance_m=result.get("destination_snap_distance_m", 0.0),
            graph_note=result["graph_note"],
            is_demo_mode=result.get("is_demo_mode", False),
            warning=result.get("warning"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route calculation failed: {str(e)}")
