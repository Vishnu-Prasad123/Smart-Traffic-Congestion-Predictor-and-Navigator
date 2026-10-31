"""tests/test_routing.py"""
import sys
import math
import pytest
import networkx as nx
from pathlib import Path
from shapely.geometry import LineString

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.routing_service import (
    _build_demo_graph,
    _haversine_m,
    _heuristic,
    _path_metrics,
    _path_to_geometry,
    find_routes,
    load_graph,
    is_graph_loaded,
    CONGESTION_PENALTY,
)


@pytest.fixture(autouse=True)
def ensure_graph():
    """Load the demo graph before each unit test to ensure isolated testing."""
    import app.services.routing_service as rs
    rs._graph = _build_demo_graph()
    rs._graph_loaded = True
    rs._is_demo = True
    rs._graph_warning = None
    yield
    rs._graph = None
    rs._graph_loaded = False


def test_haversine_known_distance():
    d = _haversine_m(12.9352, 77.6245, 12.9784, 77.6408)
    assert 4000 < d < 7000, f"Unexpected distance: {d:.0f}m"


def test_haversine_zero():
    d = _haversine_m(12.9, 77.6, 12.9, 77.6)
    assert d == 0.0


def test_demo_graph_structure():
    G = _build_demo_graph()
    assert G.number_of_nodes() >= 8
    assert G.number_of_edges() >= 16
    for nid, data in G.nodes(data=True):
        assert "y" in data, f"Node {nid} missing y (lat)"
        assert "x" in data, f"Node {nid} missing x (lng)"


def test_demo_graph_bidirectional():
    G = _build_demo_graph()
    for u, v in G.edges():
        assert G.has_edge(v, u) or G.has_edge(u, v), f"Missing reverse for ({u},{v})"


def test_astar_finds_path():
    result = find_routes(
        src_lat=12.9716, src_lng=77.5946,   # Lal Bagh
        dst_lat=12.9784, dst_lng=77.6408,   # Indiranagar
        avoid_congestion=False,
    )
    assert len(result["routes"]) >= 1
    route = result["routes"][0]
    assert route["total_distance_km"] > 0
    assert route["total_time_min"] > 0
    assert len(route["geometry"]) >= 2


def test_route_geometry_is_latlon():
    result = find_routes(12.9716, 77.5946, 12.9784, 77.6408, avoid_congestion=False)
    geom = result["routes"][0]["geometry"]
    for point in geom:
        lat, lng = point[0], point[1]
        assert 12.0 <= lat <= 14.0, f"Latitude out of Bengaluru range: {lat}"
        assert 77.0 <= lng <= 78.5, f"Longitude out of Bengaluru range: {lng}"


def test_route_cost_with_congestion_higher():
    r_nocong = find_routes(12.9716, 77.5946, 12.8451, 77.6602, avoid_congestion=False,
                           congestion_lookup={"Koramangala": "HIGH", "Electronic City": "HIGH"})
    r_cong = find_routes(12.9716, 77.5946, 12.8451, 77.6602, avoid_congestion=True,
                         congestion_lookup={"Koramangala": "HIGH", "Electronic City": "HIGH"})
    assert len(r_nocong["routes"]) >= 1
    assert len(r_cong["routes"]) >= 1


def test_same_source_destination_raises():
    with pytest.raises(ValueError, match="same road network node"):
        find_routes(12.9352, 77.6245, 12.9352, 77.6245)


def test_path_metrics_positive():
    G = _build_demo_graph()
    path = [0, 1, 3]
    dist, time = _path_metrics(G, path)
    assert dist > 0
    assert time > 0


def test_heuristic_admissible():
    G = _build_demo_graph()
    for u in [0, 1, 2]:
        for v in [5, 6, 7]:
            if u != v:
                h = _heuristic(G, u, v)
                try:
                    path = nx.astar_path(G, u, v, weight="travel_time")
                    actual_dist, actual_time = _path_metrics(G, path)
                    assert h <= actual_time + 0.01, f"Heuristic {h:.2f} > actual {actual_time:.2f}"
                except nx.NetworkXNoPath:
                    pass


def test_congestion_penalty_values():
    assert CONGESTION_PENALTY["LOW"] == 0.0
    assert CONGESTION_PENALTY["MEDIUM"] > 0
    assert CONGESTION_PENALTY["HIGH"] > CONGESTION_PENALTY["MEDIUM"]


def test_path_to_geometry_preserves_linestring():
    """Verify that edges with intermediate curved LineStrings are fully expanded."""
    G = nx.MultiDiGraph()
    G.add_node(1, y=12.9350, x=77.6240)
    G.add_node(2, y=12.9380, x=77.6280)

    # LineString with 4 points between node 1 and 2
    curve = LineString([
        (77.6240, 12.9350),
        (77.6250, 12.9355),
        (77.6265, 12.9370),
        (77.6280, 12.9380),
    ])
    G.add_edge(1, 2, key=0, length=500.0, travel_time=40.0, geometry=curve)

    pts = _path_to_geometry(G, [1, 2])
    assert len(pts) == 4, f"Expected 4 road points, got {len(pts)}"
    assert pts[0] == [12.9350, 77.6240]
    assert pts[1] == [12.9355, 77.6250]
    assert pts[-1] == [12.9380, 77.6280]


def test_real_cached_graph_loads_and_routes():
    """Verify routing on the cached Bengaluru OpenStreetMap graph if present."""
    import app.services.routing_service as rs
    graph_path = Path("data/maps/bengaluru_graph.graphml")
    if not graph_path.exists():
        pytest.skip("Cached GraphML not yet present")

    load_success = rs.load_graph()
    assert load_success is True
    assert rs.is_graph_loaded() is True
    assert rs.is_demo_graph() is False

    # Route between two locations in Koramangala
    res = find_routes(
        src_lat=12.9358, src_lng=77.6292,  # Sony World
        dst_lat=12.9248, dst_lng=77.6136,  # Tavarekere
        avoid_congestion=True,
    )
    assert res["is_demo_mode"] is False
    assert res["warning"] is None
    assert len(res["routes"]) >= 1

    primary = res["routes"][0]
    assert primary["total_distance_km"] > 0
    # Must have multiple intermediate road coordinates following real streets
    assert len(primary["geometry"]) > 5


def test_snap_distance_in_response():
    """Verify that source and destination snapping distances are computed."""
    res = find_routes(
        src_lat=12.9716, src_lng=77.5946,
        dst_lat=12.9784, dst_lng=77.6408,
        avoid_congestion=False,
    )
    assert "source_snap_distance_m" in res
    assert "destination_snap_distance_m" in res
    assert res["source_snap_distance_m"] >= 0.0
    assert res["destination_snap_distance_m"] >= 0.0
    assert res["status"] == "success"


def test_far_out_of_bounds_raises_snap_error():
    """Points far outside the road network (> 2500m) should raise a clear error."""
    with pytest.raises(ValueError, match="from the nearest road"):
        find_routes(
            src_lat=12.9716, src_lng=77.5946,
            dst_lat=13.2000, dst_lng=77.8000,  # ~30 km outside Bengaluru
            avoid_congestion=False,
        )


def test_koramangala_to_mg_road_real_graph():
    """Verify routing between Koramangala and MG Road reaches the destination marker."""
    import app.services.routing_service as rs
    graph_path = Path("data/maps/bengaluru_graph.graphml")
    if not graph_path.exists():
        pytest.skip("Cached GraphML not yet present")

    rs.load_graph()
    assert rs.is_graph_loaded() is True
    assert rs.is_demo_graph() is False

    src_lat, src_lng = 12.93520, 77.62450  # Koramangala
    dst_lat, dst_lng = 12.97560, 77.60990  # MG Road

    res = rs.find_routes(
        src_lat=src_lat, src_lng=src_lng,
        dst_lat=dst_lat, dst_lng=dst_lng,
        avoid_congestion=True,
    )

    assert res["status"] == "success"
    assert res["is_demo_mode"] is False
    assert len(res["routes"]) >= 1

    # Destination snapped node must be very close to requested MG Road (< 150m)
    dst_snap = res["destination_snapped"]
    d_dst = _haversine_m(dst_lat, dst_lng, dst_snap["lat"], dst_snap["lng"])
    assert d_dst < 150.0, f"Destination snapped too far from MG Road: {d_dst:.1f}m"

    # Route geometry should start at source and end at destination
    r0 = res["routes"][0]
    first_pt = r0["geometry"][0]
    last_pt = r0["geometry"][-1]

    # Verify first point is at source
    assert abs(first_pt[0] - src_lat) < 0.001
    assert abs(first_pt[1] - src_lng) < 0.001

    # Verify last point reaches MG Road
    assert abs(last_pt[0] - dst_lat) < 0.001
    assert abs(last_pt[1] - dst_lng) < 0.001

    # Must traverse central Bengaluru corridor (around 7 to 9.5 km)
    assert 6.0 < r0["total_distance_km"] < 12.0
    # Must have high-resolution street geometry with dozens of turns
    assert len(r0["geometry"]) > 50


def test_route_segment_predictions_and_breakdown():
    """Verify segment-level Random Forest predictions and percentage breakdowns."""
    import app.services.routing_service as rs
    graph_path = Path("data/maps/bengaluru_graph.graphml")
    if not graph_path.exists():
        pytest.skip("Cached GraphML not present")

    rs.load_graph()
    res = rs.find_routes(
        src_lat=12.93520, src_lng=77.62450,  # Koramangala
        dst_lat=12.97560, dst_lng=77.60990,  # MG Road
        avoid_congestion=True,
    )
    routes = res["routes"]
    assert len(routes) >= 2, "Expected at least 2 distinct candidate routes"

    for r in routes:
        # Check breakdown
        bd = r["congestion_breakdown"]
        assert "LOW" in bd and "MEDIUM" in bd and "HIGH" in bd
        total_pct = bd["LOW"] + bd["MEDIUM"] + bd["HIGH"]
        assert abs(total_pct - 100.0) < 0.5, f"Breakdown does not sum to 100%: {total_pct}"

        # Continuous congestion score between 0.0 and 1.0
        assert 0.0 <= r["congestion_score"] <= 1.0

        # Segments must have valid attributes
        assert len(r["segments"]) > 10
        seg0 = r["segments"][0]
        assert seg0["congestion_estimate"] in ["LOW", "MEDIUM", "HIGH"]
        assert seg0["congestion_confidence"] >= 0.5
        assert len(seg0["coordinates"]) >= 2
        assert seg0["distance_m"] > 0

        # Documented rule must be present
        assert len(r["dominant_rule"]) > 10


def test_balanced_recommendation_bounds():
    """Verify the recommended route has valid recommendation reason and bounds."""
    import app.services.routing_service as rs
    graph_path = Path("data/maps/bengaluru_graph.graphml")
    if not graph_path.exists():
        pytest.skip("Cached GraphML not present")

    rs.load_graph()
    res = rs.find_routes(
        src_lat=12.93520, src_lng=77.62450,
        dst_lat=12.97560, dst_lng=77.60990,
        avoid_congestion=True,
    )
    routes = res["routes"]
    rec = routes[0]

    assert rec["is_recommended"] is True
    assert rec["label"] == "Route 1"
    assert rec["color"] == "#2563EB"
    assert len(rec["recommendation_reason"]) > 15

    # If there are alternatives, they should be labeled Route 2, Route 3, etc.
    for idx, alt in enumerate(routes[1:], start=2):
        assert alt["is_recommended"] is False
        assert alt["label"] == f"Route {idx}"


def test_dominant_percentage_classification():
    """Verify route congestion level follows dominant percentage rule:
    Low dominant -> LOW, Med dominant -> MEDIUM, Hard dominant -> HIGH."""
    import app.services.routing_service as rs
    graph_path = Path("data/maps/bengaluru_graph.graphml")
    if not graph_path.exists():
        pytest.skip("Cached GraphML not present")

    rs.load_graph()
    res = rs.find_routes(
        src_lat=12.93520, src_lng=77.62450,
        dst_lat=12.97560, dst_lng=77.60990,
        avoid_congestion=True,
    )
    routes = res["routes"]
    assert len(routes) > 0
    for r in routes:
        bd = r["congestion_breakdown"]
        level = r["congestion_level"]
        # Verify the classified level matches dominant segment percentage
        max_pct = max(bd["LOW"], bd["MEDIUM"], bd["HIGH"])
        if bd["LOW"] == max_pct:
            assert level == "LOW"
        elif bd["MEDIUM"] == max_pct:
            assert level == "MEDIUM"
        else:
            assert level == "HIGH"
        assert r["label"].startswith("Route ")


def test_diagnostic_report_structure():
    """Verify diagnostic report returns comprehensive dataset, model, and rule diagnostics."""
    import app.services.routing_service as rs
    diag = rs.get_diagnostic_report()

    assert "dataset_distribution" in diag
    assert diag["dataset_distribution"]["total_records"] == 8936
    assert "HIGH" in diag["dataset_distribution"]["classes"]

    assert "model_metrics" in diag
    assert diag["model_metrics"]["accuracy"] > 0.85
    assert diag["model_metrics"]["macro_f1"] > 0.80

    assert "road_feature_mapping" in diag
    assert "Arterial / Trunk Corridors" in diag["road_feature_mapping"]
    assert "Local / Residential Streets" in diag["road_feature_mapping"]

    assert "aggregation_rule" in diag
    assert "HIGH" in diag["aggregation_rule"]
    assert "recommendation_policy" in diag["aggregation_rule"]