"""
backend/app/schemas/traffic.py
Pydantic request/response models for all API endpoints.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class CongestionLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    HARD = "HARD"


class WeatherCondition(str, Enum):
    CLEAR = "Clear"
    RAIN = "Rain"
    OVERCAST = "Overcast"
    FOG = "Fog"
    WINDY = "Windy"
    RAINY = "Rainy"
    CLOUDY = "Cloudy"
    FOGGY = "Foggy"
    UNKNOWN = "Unknown"


class RoadworkActivity(str, Enum):
    YES = "Yes"
    NO = "No"
    UNKNOWN = "Unknown"


# -- Prediction -----------------------------------------------------------------
class PredictionRequest(BaseModel):
    traffic_volume: float = Field(..., ge=0, le=100000, description="Vehicle count per observation window")
    average_speed: float = Field(..., ge=0, le=200, description="Average speed in km/h")
    travel_time_index: float = Field(..., ge=1.0, le=10.0, description="Ratio of travel time to free-flow")
    road_capacity_utilization: float = Field(..., ge=0, le=200, description="Percentage of road capacity used")
    incident_reports: int = Field(default=0, ge=0, le=100)
    day_of_week: int = Field(default=0, ge=0, le=6, description="0=Monday, 6=Sunday")
    month: int = Field(default=1, ge=1, le=12)
    weather_conditions: WeatherCondition = WeatherCondition.CLEAR
    roadwork_activity: RoadworkActivity = RoadworkActivity.NO

    @field_validator("travel_time_index")
    @classmethod
    def tti_must_be_positive(cls, v):
        if v < 1.0:
            raise ValueError("Travel Time Index must be >= 1.0 (cannot be faster than free-flow)")
        return v


class ProbabilityBreakdown(BaseModel):
    LOW: float
    MEDIUM: float
    HIGH: float


class PredictionResponse(BaseModel):
    congestion_level: CongestionLevel
    probabilities: ProbabilityBreakdown
    confidence: float
    model_version: str = "RandomForestClassifier-v1"
    is_demo_mode: bool = False
    warning: Optional[str] = None


# -- Routing --------------------------------------------------------------------
class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class RouteRequest(BaseModel):
    source: Coordinate
    destination: Coordinate
    avoid_congestion: bool = Field(default=True, description="Weight A* cost by congestion estimates")


class RouteSegment(BaseModel):
    coordinates: List[List[float]]  # [[lat, lng], ...]
    distance_m: float
    estimated_time_min: float
    congestion_estimate: Optional[CongestionLevel] = None
    congestion_confidence: Optional[float] = None
    congestion_note: str = "Predicted by Random Forest from road attributes"
    name: Optional[str] = None
    highway: Optional[str] = None
    speed_kph: Optional[float] = None


class RouteInfo(BaseModel):
    route_id: str
    label: str  # "Recommended" | "Alternative 1" | "Alternative 2"
    color: str  # hex for map display
    total_distance_km: float
    total_time_min: float
    segments: List[RouteSegment]
    geometry: List[List[float]]  # full polyline as [[lat, lng], ...]
    congestion_level: Optional[CongestionLevel] = None
    congestion_score: Optional[float] = Field(default=None, description="Continuous congestion score 0.0 (low) to 1.0 (high)")
    congestion_breakdown: Optional[Dict[str, float]] = Field(default=None, description="Percentage of distance by congestion class: LOW, MEDIUM, HIGH")
    congestion_cost: Optional[float] = Field(default=None, description="Total congestion-adjusted travel cost (seconds)")
    recommendation_reason: Optional[str] = Field(default=None, description="Explanation for route recommendation or alternative trade-off")
    is_recommended: bool = False
    dominant_rule: Optional[str] = Field(default=None, description="Defensible rule applied for route-level classification")
    node_count: int


class RouteResponse(BaseModel):
    status: str = "success"
    routes: List[RouteInfo]
    source_requested: Optional[Coordinate] = None
    destination_requested: Optional[Coordinate] = None
    source_snapped: Coordinate
    destination_snapped: Coordinate
    source_snap_distance_m: Optional[float] = 0.0
    destination_snap_distance_m: Optional[float] = 0.0
    graph_note: str = "Road network from OpenStreetMap via OSMnx"
    is_demo_mode: bool = False
    warning: Optional[str] = None


# -- Diagnostics ----------------------------------------------------------------
class DiagnosticReportResponse(BaseModel):
    dataset_distribution: Dict[str, Any]
    model_metrics: Dict[str, Any]
    road_feature_mapping: Dict[str, Any]
    aggregation_rule: Dict[str, Any]
    sample_route_breakdown: Optional[Dict[str, Any]] = None



# -- Traffic Summary -------------------------------------------------------------
class CongestionDistribution(BaseModel):
    LOW: int
    MEDIUM: int
    HIGH: int


class AreaTrafficStat(BaseModel):
    area: str
    avg_volume: float
    avg_speed: float
    dominant_congestion: str


class TrafficSummaryResponse(BaseModel):
    total_records: int
    is_demo_mode: bool
    congestion_distribution: Dict[str, int]
    avg_volume_by_day: Dict[str, float]
    avg_speed_by_congestion: Dict[str, float]
    top_areas: List[AreaTrafficStat]
    volume_over_time: List[Dict[str, Any]]
    date_range: Dict[str, str]
    data_note: str


# -- Model Metrics --------------------------------------------------------------
class ModelMetricsResponse(BaseModel):
    model_trained: bool
    model: Optional[str] = None
    accuracy: Optional[float] = None
    macro_f1: Optional[float] = None
    precision_per_class: Optional[Dict[str, float]] = None
    recall_per_class: Optional[Dict[str, float]] = None
    f1_per_class: Optional[Dict[str, float]] = None
    confusion_matrix: Optional[List[List[int]]] = None
    classes: Optional[List[str]] = None
    test_set_size: Optional[int] = None
    total_records: Optional[int] = None
    n_features: Optional[int] = None
    feature_names: Optional[List[str]] = None
    feature_importance: Optional[Dict[str, float]] = None
    is_demo_mode: bool = False
    training_message: str = ""


# -- Health ---------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    graph_loaded: bool
    demo_mode: bool
    version: str
