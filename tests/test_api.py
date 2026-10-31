"""tests/test_api.py - API integration tests using httpx + FastAPI TestClient"""
import sys
import pytest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client. Graph loading uses the demo graph (no OSMnx download)."""
    import app.services.routing_service as rs
    rs._graph = rs._build_demo_graph()
    rs._graph_loaded = True

    import app.services.ml_service as ml
    ml._pipeline = None  # Force demo prediction mode for tests
    ml._is_demo_mode = True

    import app.services.traffic_service as ts
    ts._df = ts._generate_minimal_df()
    ts._is_demo = True

    from app.main import app
    with TestClient(app) as c:
        yield c


# -- Health ----------------------------------------------------------------------
def test_health_returns_200(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_health_response_schema(client):
    r = client.get("/api/health").json()
    assert "status" in r
    assert "model_loaded" in r
    assert "graph_loaded" in r
    assert r["status"] == "ok"


def test_root_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Smart Traffic" in r.json().get("app", "")


# -- Prediction ------------------------------------------------------------------
VALID_PAYLOAD = {
    "traffic_volume": 3000,
    "average_speed": 25,
    "travel_time_index": 2.0,
    "road_capacity_utilization": 70,
    "incident_reports": 2,
    "day_of_week": 1,
    "month": 6,
    "weather_conditions": "Rainy",
    "roadwork_activity": "Yes",
}

def test_predict_returns_200(client):
    r = client.post("/api/predict-congestion", json=VALID_PAYLOAD)
    assert r.status_code == 200, r.text


def test_predict_schema(client):
    data = client.post("/api/predict-congestion", json=VALID_PAYLOAD).json()
    assert "congestion_level" in data
    assert data["congestion_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert "probabilities" in data
    assert "confidence" in data
    assert 0.0 <= data["confidence"] <= 1.0


def test_predict_probabilities_sum_to_one(client):
    data = client.post("/api/predict-congestion", json=VALID_PAYLOAD).json()
    proba = data["probabilities"]
    total = proba["LOW"] + proba["MEDIUM"] + proba["HIGH"]
    assert abs(total - 1.0) < 0.01, f"Probabilities sum to {total}"


def test_predict_invalid_volume(client):
    bad = {**VALID_PAYLOAD, "traffic_volume": -999}
    r = client.post("/api/predict-congestion", json=bad)
    assert r.status_code == 422


def test_predict_invalid_tti(client):
    bad = {**VALID_PAYLOAD, "travel_time_index": 0.5}  # below 1.0
    r = client.post("/api/predict-congestion", json=bad)
    assert r.status_code == 422


def test_predict_missing_required_field(client):
    bad = {k: v for k, v in VALID_PAYLOAD.items() if k != "traffic_volume"}
    r = client.post("/api/predict-congestion", json=bad)
    assert r.status_code == 422


def test_predict_invalid_weather(client):
    bad = {**VALID_PAYLOAD, "weather_conditions": "Tornado"}
    r = client.post("/api/predict-congestion", json=bad)
    assert r.status_code == 422


# -- Routing ---------------------------------------------------------------------
VALID_ROUTE = {
    "source": {"lat": 12.9716, "lng": 77.5946},
    "destination": {"lat": 12.9784, "lng": 77.6408},
    "avoid_congestion": True,
}

def test_routes_returns_200(client):
    r = client.post("/api/routes", json=VALID_ROUTE)
    assert r.status_code == 200, r.text


def test_routes_schema(client):
    data = client.post("/api/routes", json=VALID_ROUTE).json()
    assert "routes" in data
    assert len(data["routes"]) >= 1
    route = data["routes"][0]
    assert "total_distance_km" in route
    assert "total_time_min" in route
    assert "geometry" in route
    assert route["total_distance_km"] > 0


def test_routes_geometry_is_list_of_pairs(client):
    data = client.post("/api/routes", json=VALID_ROUTE).json()
    geom = data["routes"][0]["geometry"]
    assert isinstance(geom, list)
    assert all(len(p) == 2 for p in geom)


def test_routes_invalid_lat(client):
    bad = {"source": {"lat": 999, "lng": 77.6}, "destination": {"lat": 12.9, "lng": 77.6}}
    r = client.post("/api/routes", json=bad)
    assert r.status_code == 422


def test_routes_missing_destination(client):
    bad = {"source": {"lat": 12.9, "lng": 77.6}}
    r = client.post("/api/routes", json=bad)
    assert r.status_code == 422


# -- Traffic Summary -------------------------------------------------------------
def test_traffic_summary_200(client):
    r = client.get("/api/traffic/summary")
    assert r.status_code == 200


def test_traffic_summary_schema(client):
    data = client.get("/api/traffic/summary").json()
    assert "total_records" in data
    assert "congestion_distribution" in data
    assert data["total_records"] > 0


# -- Model Metrics ---------------------------------------------------------------
def test_model_metrics_200(client):
    r = client.get("/api/model/metrics")
    assert r.status_code == 200


def test_model_metrics_untrained(client):
    """When model is not trained, returns model_trained=False with a message."""
    data = client.get("/api/model/metrics").json()
    assert "model_trained" in data
    if not data["model_trained"]:
        assert len(data.get("training_message", "")) > 0


def test_model_metrics_real_trained_data(client):
    """Verify that when real model metrics are present, metrics are populated and not demo mode."""
    r = client.get("/api/model/metrics")
    assert r.status_code == 200
    data = r.json()
    assert data["model_trained"] is True
    assert data["is_demo_mode"] is False
    assert data["accuracy"] > 0.85
    assert data["total_records"] == 8936


def test_diagnostic_report_200(client):
    """Verify that the diagnostic report endpoint returns 200 with full metrics."""
    r = client.get("/api/traffic/diagnostic-report")
    assert r.status_code == 200
    data = r.json()
    assert "dataset_distribution" in data
    assert "model_metrics" in data
    assert "road_feature_mapping" in data
    assert "aggregation_rule" in data
    assert data["dataset_distribution"]["total_records"] == 8936

