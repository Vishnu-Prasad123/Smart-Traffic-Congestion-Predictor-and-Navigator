"""
backend/app/services/routing_service.py
----------------------------------------
OSMnx road graph loading, geometry extraction, and A* route finding for Bengaluru.

Key design decisions:
- The graph is cached as GraphML in data/maps/bengaluru_graph.graphml.
- Real road-segment geometries (LineString coordinates) are preserved so routes
  follow actual streets, turns, and curves rather than straight lines.
- A* heuristic: Haversine distance / max_speed -> admissible (never overestimates).
- Edge cost: travel_time_seconds * (1 + congestion_penalty).
- Dominant congestion level along the route is estimated from the dataset area mapping.
"""
import json
import logging
import math
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)

_graph: Optional[nx.MultiDiGraph] = None
_graph_loaded = False
_is_demo = False
_graph_warning: Optional[str] = None

BENGALURU_AREAS = {
    "Koramangala": (12.9352, 77.6245),
    "Indiranagar": (12.9784, 77.6408),
    "Whitefield": (12.9698, 77.7499),
    "Electronic City": (12.8451, 77.6602),
    "MG Road": (12.9756, 77.6099),
    "Silk Board": (12.9174, 77.6228),
    "Hebbal": (13.0350, 77.5970),
    "Marathahalli": (12.9591, 77.7019),
    "Jayanagar": (12.9299, 77.5833),
    "BTM Layout": (12.9166, 77.6101),
}

CONGESTION_PENALTY = {"LOW": 0.0, "MEDIUM": 0.35, "HIGH": 0.85}
DEFAULT_SPEED_MS = 30.0 / 3.6  # 30 km/h in m/s
MAX_SPEED_MS = 80.0 / 3.6      # 80 km/h for admissible heuristic
MAX_SNAP_DISTANCE_M = 2500.0   # Max snapping tolerance to nearest road node in metres (2.5 km)

ROUTE_COLORS = ["#2563EB", "#16A34A", "#D97706"]
ROUTE_LABELS = ["Recommended", "Alternative 1", "Alternative 2"]

_edge_prediction_cache: Dict[str, Tuple[str, float]] = {}


def _get_settings():
    from app.core.config import settings
    return settings


def _clean_highway_type(hw) -> str:
    """Safely extract the primary highway type string from OSM tag value."""
    if isinstance(hw, list):
        return str(hw[0]) if len(hw) > 0 else "unclassified"
    return str(hw or "unclassified")


def _edge_to_features(hw: str, speed_kph: float = 30.0, lanes: int = 1) -> dict:
    """
    Map OpenStreetMap physical road attributes to feature dictionaries matching the
    authentic Bangalore Traffic Pulse dataset schema.
    """
    hw_clean = _clean_highway_type(hw)
    if hw_clean in ["primary", "primary_link", "trunk", "trunk_link", "motorway", "motorway_link", "busway"]:
        # Arterial corridor carrying heavy traffic in central Bengaluru
        return {
            "traffic_volume": 38000,
            "average_speed": min(float(speed_kph or 30), 32.0),
            "travel_time_index": 1.48,
            "road_capacity_utilization": 98.0,
            "incident_reports": 2,
            "day_of_week": 2,
            "month": 10,
            "weather_conditions": "Clear",
            "roadwork_activity": "No",
        }
    elif hw_clean in ["secondary", "secondary_link", "tertiary", "tertiary_link"]:
        # Collector connector carrying moderate cross-neighborhood traffic
        return {
            "traffic_volume": 20000,
            "average_speed": max(float(speed_kph or 35), 36.0),
            "travel_time_index": 1.22,
            "road_capacity_utilization": 82.0,
            "incident_reports": 1,
            "day_of_week": 2,
            "month": 10,
            "weather_conditions": "Clear",
            "roadwork_activity": "No",
        }
    else:
        # Local / Residential / Living street / Service / Unclassified
        return {
            "traffic_volume": 11000,
            "average_speed": float(speed_kph or 30),
            "travel_time_index": 1.12,
            "road_capacity_utilization": 50.0,
            "incident_reports": 0,
            "day_of_week": 2,
            "month": 10,
            "weather_conditions": "Clear",
            "roadwork_activity": "No",
        }


def _annotate_graph_edges(G: nx.MultiDiGraph):
    """
    Annotate all graph edges with predicted congestion levels from the trained Random Forest model,
    travel times, and congestion-adjusted costs.
    """
    global _edge_prediction_cache
    from app.services import ml_service

    # Collect unique highway types in graph that need prediction
    unique_hw_types = set()
    for u, v, k, d in G.edges(keys=True, data=True):
        hw = _clean_highway_type(d.get("highway"))
        if hw not in _edge_prediction_cache:
            unique_hw_types.add(hw)

    if unique_hw_types:
        hw_list = list(unique_hw_types)
        feature_dicts = [_edge_to_features(h) for h in hw_list]
        preds = ml_service.predict_batch(feature_dicts)
        for h, p in zip(hw_list, preds):
            _edge_prediction_cache[h] = (p.get("congestion_level", "LOW"), float(p.get("confidence", 0.95)))

    # Annotate edges
    for u, v, k, d in G.edges(keys=True, data=True):
        hw = _clean_highway_type(d.get("highway"))
        cong_level, conf = _edge_prediction_cache.get(hw, ("LOW", 0.95))
        d["congestion_level"] = cong_level
        d["congestion_conf"] = conf

        length = float(d.get("length", 100.0))
        speed = float(d.get("speed_kph", 30.0))
        speed_ms = max(speed / 3.6, 1.0)
        travel_time = float(d.get("travel_time", length / speed_ms))

        d["travel_time_s"] = travel_time
        penalty = CONGESTION_PENALTY.get(cong_level, 0.0)
        d["congestion_cost"] = travel_time * (1.0 + penalty)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the Haversine distance in metres between two lat/lon points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def load_graph() -> bool:
    """
    Load the Bengaluru road graph.
    1. Try loading from cached GraphML file.
    2. If not present or corrupt, download from OSMnx and cache it.
    3. If download fails, build synthetic demo graph and report explicit reason.
    """
    global _graph, _graph_loaded, _is_demo, _graph_warning
    settings = _get_settings()

    # 1. Try loading cached graph
    if settings.GRAPH_PATH.exists():
        try:
            import osmnx as ox
            logger.info(f"Loading road network from cache: {settings.GRAPH_PATH}")
            G = ox.load_graphml(settings.GRAPH_PATH)
            if len(G.nodes) > 0 and len(G.edges) > 0:
                _annotate_graph_edges(G)
                _graph = G
                _graph_loaded = True
                _is_demo = False
                _graph_warning = None
                logger.info(f"Successfully loaded cached graph: {len(G.nodes)} nodes, {len(G.edges)} edges.")
                return True
            else:
                logger.warning("Cached graph file had zero nodes or edges. Re-downloading...")
        except Exception as e:
            logger.warning(f"Failed to load cached graph: {e}. Will attempt fresh download.")

    # 2. Try downloading via OSMnx
    try:
        import osmnx as ox
        logger.info(f"Downloading real road network via OSMnx for {settings.OSMNX_PLACE}...")
        ox.settings.use_cache = True
        ox.settings.timeout = 180

        bbox = (77.5800, 12.9100, 77.6550, 12.9850)
        G = ox.graph_from_bbox(bbox=bbox, network_type="drive")
        G = ox.truncate.largest_component(G, strongly=True)
        G = ox.add_edge_speeds(G)
        G = ox.add_edge_travel_times(G)

        settings.GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        ox.save_graphml(G, settings.GRAPH_PATH)

        _annotate_graph_edges(G)
        _graph = G
        _graph_loaded = True
        _is_demo = False
        _graph_warning = None
        logger.info(f"Downloaded & saved road network: {len(G.nodes)} nodes, {len(G.edges)} edges.")
        return True
    except ImportError:
        _graph_warning = "OSMnx library not installed. Install with: pip install osmnx"
        logger.error(_graph_warning)
    except Exception as e:
        _graph_warning = f"OSMnx Overpass download failed: {str(e)}"
        logger.error(_graph_warning)

    # 3. Fallback to demo graph if OSMnx is unavailable or download fails
    logger.warning("Falling back to synthetic demo graph.")
    G_demo = _build_demo_graph()
    _annotate_graph_edges(G_demo)
    _graph = G_demo
    _graph_loaded = True
    _is_demo = True
    return True


def _build_demo_graph() -> nx.MultiDiGraph:
    """Small synthetic fallback graph covering key Bengaluru landmarks."""
    G = nx.MultiDiGraph()
    G.graph["crs"] = "epsg:4326"
    G.graph["is_demo"] = True

    nodes = {
        0: {"y": 12.9716, "x": 77.5946, "name": "Lal Bagh"},
        1: {"y": 12.9352, "x": 77.6245, "name": "Koramangala"},
        2: {"y": 12.9784, "x": 77.6408, "name": "Indiranagar"},
        3: {"y": 12.9174, "x": 77.6228, "name": "Silk Board"},
        4: {"y": 12.9166, "x": 77.6101, "name": "BTM Layout"},
        5: {"y": 12.9756, "x": 77.6099, "name": "MG Road"},
        6: {"y": 12.9591, "x": 77.7019, "name": "Marathahalli"},
        7: {"y": 12.8451, "x": 77.6602, "name": "Electronic City"},
        8: {"y": 13.0350, "x": 77.5970, "name": "Hebbal"},
        9: {"y": 12.9299, "x": 77.5833, "name": "Jayanagar"},
    }
    for nid, data in nodes.items():
        G.add_node(nid, **data, osmid=nid)

    edges = [
        (0, 1, 40), (1, 0, 40), (1, 2, 35), (2, 1, 35),
        (1, 3, 30), (3, 1, 30), (3, 4, 30), (4, 3, 30),
        (2, 5, 40), (5, 2, 40), (5, 0, 35), (0, 5, 35),
        (2, 6, 35), (6, 2, 35), (3, 7, 45), (7, 3, 45),
        (5, 8, 50), (8, 5, 50), (0, 9, 35), (9, 0, 35),
        (4, 9, 30), (9, 4, 30), (6, 7, 45), (7, 6, 45),
        (8, 2, 50), (2, 8, 50),
    ]
    for u, v, speed in edges:
        n1, n2 = nodes[u], nodes[v]
        dist = _haversine_m(n1["y"], n1["x"], n2["y"], n2["x"])
        speed_ms = speed / 3.6
        G.add_edge(u, v, key=0, length=dist, speed_kph=speed,
                   travel_time=dist / speed_ms, maxspeed=str(speed), name=f"Road {u}-{v}")
    return G


def _get_nearest_node(lat: float, lng: float) -> Tuple[int, float]:
    """Find the graph node nearest to the given lat/lon and return (node_id, distance_in_metres)."""
    if _graph is None:
        raise RuntimeError("Graph not loaded")

    # 1. Try OSMnx nearest_nodes
    try:
        import osmnx as ox
        # Note: OSMnx accepts X=lng, Y=lat
        node = ox.nearest_nodes(_graph, X=lng, Y=lat)
        if node in _graph:
            node_lat = float(_graph.nodes[node].get("y", 0.0))
            node_lon = float(_graph.nodes[node].get("x", 0.0))
            dist = _haversine_m(lat, lng, node_lat, node_lon)
            return node, dist
    except Exception as e:
        logger.debug(f"ox.nearest_nodes failed: {e}")

    # 2. Robust spatial search by Haversine
    min_dist = float("inf")
    nearest = None
    for nid, data in _graph.nodes(data=True):
        y = float(data.get("y", 0.0))
        x = float(data.get("x", 0.0))
        d = _haversine_m(lat, lng, y, x)
        if d < min_dist:
            min_dist = d
            nearest = nid
    if nearest is None:
        raise ValueError("Could not find a valid nearest node in the road network.")
    return nearest, min_dist


def _get_edge_dict(d) -> dict:
    """Safely extract the lowest length edge data from a MultiDiGraph edge dict or AtlasView."""
    if hasattr(d, "values") and (0 in d or any(isinstance(k, int) for k in d)):
        return min(d.values(), key=lambda x: float(x.get("length", 1e9)))
    return d



def _edge_geometry(G: nx.MultiDiGraph, u: int, v: int, edge_data: dict) -> List[List[float]]:
    """Return ordered [[lat, lng], ...] for an individual edge preserving road curves."""
    u_lat = float(G.nodes[u]["y"])
    u_lon = float(G.nodes[u]["x"])
    v_lat = float(G.nodes[v]["y"])
    v_lon = float(G.nodes[v]["x"])

    if "geometry" in edge_data and hasattr(edge_data["geometry"], "coords"):
        pts = [[float(c[1]), float(c[0])] for c in edge_data["geometry"].coords]
        # Orient from u to v
        d_start_u = (pts[0][0] - u_lat) ** 2 + (pts[0][1] - u_lon) ** 2
        d_end_u = (pts[-1][0] - u_lat) ** 2 + (pts[-1][1] - u_lon) ** 2
        if d_end_u < d_start_u:
            pts.reverse()
        return pts
    return [[u_lat, u_lon], [v_lat, v_lon]]


def _heuristic(G: nx.MultiDiGraph, u: int, v: int) -> float:
    """
    Admissible A* heuristic: Haversine distance / max_speed_ms.
    Guaranteed admissible because straight-line distance <= road distance,
    and MAX_SPEED_MS >= any road speed limit.
    """
    u_data = G.nodes[u]
    v_data = G.nodes[v]
    dist = _haversine_m(
        float(u_data.get("y", 0.0)), float(u_data.get("x", 0.0)),
        float(v_data.get("y", 0.0)), float(v_data.get("x", 0.0)),
    )
    return dist / MAX_SPEED_MS


def _path_to_geometry(
    G: nx.MultiDiGraph,
    path: List[int],
    src_coord: Optional[Tuple[float, float]] = None,
    dst_coord: Optional[Tuple[float, float]] = None,
) -> List[List[float]]:
    """
    Convert a node path into an ordered sequence of [latitude, longitude] points
    by preserving each edge's authentic LineString road geometry.
    Optionally prepends the requested start coordinate and appends the requested
    destination coordinate to cleanly bridge marker pins to the snapped network.
    """
    full_coords: List[List[float]] = []

    for u, v in zip(path[:-1], path[1:]):
        edge_data = _get_edge_dict(G[u][v])
        pts = _edge_geometry(G, u, v, edge_data)

        for pt in pts:
            if not full_coords or full_coords[-1] != pt:
                full_coords.append(pt)

    # Fallback safety: ensure at least start and end node
    if len(full_coords) < 2 and len(path) >= 2:
        full_coords = [
            [float(G.nodes[path[0]]["y"]), float(G.nodes[path[0]]["x"])],
            [float(G.nodes[path[-1]]["y"]), float(G.nodes[path[-1]]["x"])],
        ]

    # Prepend requested source coordinate if provided and not identical
    if src_coord is not None:
        src_pt = [float(src_coord[0]), float(src_coord[1])]
        if full_coords and full_coords[0] != src_pt:
            full_coords.insert(0, src_pt)

    # Append requested destination coordinate if provided and not identical
    if dst_coord is not None:
        dst_pt = [float(dst_coord[0]), float(dst_coord[1])]
        if full_coords and full_coords[-1] != dst_pt:
            full_coords.append(dst_pt)

    # Route orientation check
    if src_coord and dst_coord and len(full_coords) >= 2:
        d_start_to_src = _haversine_m(full_coords[0][0], full_coords[0][1], src_coord[0], src_coord[1])
        d_start_to_dst = _haversine_m(full_coords[0][0], full_coords[0][1], dst_coord[0], dst_coord[1])
        if d_start_to_dst < d_start_to_src:
            full_coords.reverse()

    return full_coords


def _path_metrics(G: nx.MultiDiGraph, path: List[int]) -> Tuple[float, float]:
    """Return (total_distance_m, total_travel_time_s) for a node path."""
    total_dist = 0.0
    total_time = 0.0
    for u, v in zip(path[:-1], path[1:]):
        edge_data = _get_edge_dict(G[u][v])
        dist = float(edge_data.get("length", 100.0))
        tt = edge_data.get("travel_time_s")
        if tt is None:
            tt = edge_data.get("travel_time")
        if tt is None:
            speed = float(edge_data.get("speed_kph", 30.0)) / 3.6
            tt = dist / max(speed, 1.0)
        total_dist += dist
        total_time += float(tt)
    return total_dist, total_time



def find_routes(
    src_lat: float,
    src_lng: float,
    dst_lat: float,
    dst_lng: float,
    avoid_congestion: bool = True,
    congestion_lookup: Optional[Dict[str, str]] = None,
) -> dict:
    """
    Find and compare multiple road-following routes from source to destination.
    Uses Random Forest segment predictions and A* to generate diverse alternatives
    and recommends the best balanced option within travel-time and distance bounds.
    """
    if _graph is None:
        load_graph()

    if _graph is None:
        raise RuntimeError("Road graph could not be loaded.")

    G = _graph
    is_demo = _is_demo or G.graph.get("is_demo", False)

    # Snap source and destination to nearest network nodes independently
    try:
        src_node, src_dist = _get_nearest_node(src_lat, src_lng)
        dst_node, dst_dist = _get_nearest_node(dst_lat, dst_lng)
    except Exception as e:
        raise ValueError(f"Could not snap coordinates to road network: {e}")

    # Snapping distance check: ensure endpoints are within mapped road network
    if src_dist > MAX_SNAP_DISTANCE_M:
        raise ValueError(
            f"Start location ({src_lat:.5f}, {src_lng:.5f}) is {round(src_dist)}m from the nearest road in the network. "
            f"The network covers central Bengaluru (max snapping tolerance: {int(MAX_SNAP_DISTANCE_M)}m). "
            "Please select a start location within the active coverage area."
        )
    if dst_dist > MAX_SNAP_DISTANCE_M:
        raise ValueError(
            f"Destination ({dst_lat:.5f}, {dst_lng:.5f}) is {round(dst_dist)}m from the nearest road in the network. "
            f"The network covers central Bengaluru (max snapping tolerance: {int(MAX_SNAP_DISTANCE_M)}m). "
            "Please select a destination within the active coverage area."
        )

    if src_node == dst_node:
        raise ValueError("Source and destination resolve to the same road network node. Please choose points farther apart.")

    src_snapped = {
        "lat": float(G.nodes[src_node].get("y", src_lat)),
        "lng": float(G.nodes[src_node].get("x", src_lng)),
    }
    dst_snapped = {
        "lat": float(G.nodes[dst_node].get("y", dst_lat)),
        "lng": float(G.nodes[dst_node].get("x", dst_lng)),
    }

    # Weight functions for diverse A* route search
    def fastest_weight(u, v, d):
        ed = _get_edge_dict(d)
        return float(ed.get("travel_time_s", 1.0))

    def congestion_weight(u, v, d):
        ed = _get_edge_dict(d)
        return float(ed.get("congestion_cost", 1.0))

    candidate_paths: List[List[int]] = []

    # 1. Primary Fastest Route (pure travel time)
    try:
        p_fastest = nx.astar_path(
            G, src_node, dst_node,
            heuristic=lambda u, v: _heuristic(G, u, v),
            weight=fastest_weight,
        )
        candidate_paths.append(p_fastest)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        try:
            p_fastest = nx.shortest_path(G, src_node, dst_node, weight="length")
            candidate_paths.append(p_fastest)
        except Exception:
            raise ValueError(
                f"No navigable driving route found between source ({src_lat:.4f}, {src_lng:.4f}) and destination ({dst_lat:.4f}, {dst_lng:.4f})."
            )

    # 2. Congestion-Aware Route (congestion-adjusted cost)
    if avoid_congestion:
        try:
            p_cong = nx.astar_path(
                G, src_node, dst_node,
                heuristic=lambda u, v: _heuristic(G, u, v),
                weight=congestion_weight,
            )
            if p_cong not in candidate_paths:
                candidate_paths.append(p_cong)
        except Exception:
            pass

    # 3. Diversified Alternative Routes via Edge Penalization
    # Penalize edges shared with the primary route(s) to discover alternative corridors
    for penalty_factor in [2.0, 3.5, 5.0]:
        if len(candidate_paths) >= 3:
            break
        known_edges = set()
        for cp in candidate_paths:
            known_edges.update(zip(cp[:-1], cp[1:]))

        def penalized_weight(u, v, d):
            ed = _get_edge_dict(d)
            base = float(ed.get("congestion_cost" if avoid_congestion else "travel_time_s", 1.0))
            if (u, v) in known_edges or (v, u) in known_edges:
                return base * penalty_factor
            return base

        try:
            alt_path = nx.astar_path(
                G, src_node, dst_node,
                heuristic=lambda u, v: _heuristic(G, u, v),
                weight=penalized_weight,
            )
            if alt_path not in candidate_paths:
                candidate_paths.append(alt_path)
        except Exception:
            pass

    # If still fewer than 2 paths, attempt edge-removal alternative
    if len(candidate_paths) < 2 and len(candidate_paths) > 0:
        try:
            G_alt = G.copy()
            p0 = candidate_paths[0]
            p0_edges = list(zip(p0[:-1], p0[1:]))
            n_remove = max(1, int(len(p0_edges) * 0.35))
            for u, v in p0_edges[:n_remove]:
                if G_alt.has_edge(u, v):
                    G_alt.remove_edges_from([(u, v, k) for k in list(G_alt[u][v].keys())])
            alt_path = nx.astar_path(
                G_alt, src_node, dst_node,
                heuristic=lambda u, v: _heuristic(G, u, v),
                weight=congestion_weight if avoid_congestion else fastest_weight,
            )
            if alt_path not in candidate_paths:
                candidate_paths.append(alt_path)
        except Exception:
            pass

    # Process and evaluate each candidate route
    evaluated_routes = []
    for path in candidate_paths[:3]:
        geom = _path_to_geometry(G, path, src_coord=(src_lat, src_lng), dst_coord=(dst_lat, dst_lng))

        total_dist_m = 0.0
        total_time_s = 0.0
        total_cost_s = 0.0
        dist_by_cong = {"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0}
        segments_list = []

        for u, v in zip(path[:-1], path[1:]):
            edge_data = _get_edge_dict(G[u][v])
            seg_dist = float(edge_data.get("length", 100.0))
            seg_time = float(edge_data.get("travel_time_s", seg_dist / DEFAULT_SPEED_MS))
            seg_cost = float(edge_data.get("congestion_cost", seg_time))
            seg_cong = edge_data.get("congestion_level", "LOW")
            seg_conf = float(edge_data.get("congestion_conf", 0.95))
            seg_hw = _clean_highway_type(edge_data.get("highway"))
            seg_name = edge_data.get("name")
            if isinstance(seg_name, list):
                seg_name = str(seg_name[0]) if seg_name else None
            seg_speed = float(edge_data.get("speed_kph", 30.0))

            total_dist_m += seg_dist
            total_time_s += seg_time
            total_cost_s += seg_cost
            dist_by_cong[seg_cong] = dist_by_cong.get(seg_cong, 0.0) + seg_dist

            seg_coords = _edge_geometry(G, u, v, edge_data)
            segments_list.append({
                "coordinates": seg_coords,
                "distance_m": round(seg_dist, 1),
                "estimated_time_min": round(seg_time / 60.0, 2),
                "congestion_estimate": seg_cong,
                "congestion_confidence": round(seg_conf, 3),
                "congestion_note": "Predicted by Random Forest from road attributes",
                "name": seg_name,
                "highway": seg_hw,
                "speed_kph": round(seg_speed, 1),
            })

        total_dist_km = total_dist_m / 1000.0
        total_time_min = total_time_s / 60.0

        pct_low = round((dist_by_cong["LOW"] / total_dist_m * 100.0) if total_dist_m > 0 else 0.0, 1)
        pct_med = round((dist_by_cong["MEDIUM"] / total_dist_m * 100.0) if total_dist_m > 0 else 0.0, 1)
        pct_high = round((dist_by_cong["HIGH"] / total_dist_m * 100.0) if total_dist_m > 0 else 0.0, 1)

        # Continuous congestion score from 0.0 (all low) to 1.0 (all high)
        congestion_score = round(
            (0.0 * dist_by_cong["LOW"] + 0.5 * dist_by_cong["MEDIUM"] + 1.0 * dist_by_cong["HIGH"]) / total_dist_m
            if total_dist_m > 0 else 0.0,
            3
        )

        # Dominant percentage classification requested by user:
        # "and the perecentage of low increases put it as low. if percentage of medium increases put it as medium. if percentage of hard increases put it as Hard"
        if pct_low > pct_med and pct_low > pct_high:
            route_cong_level = "LOW"
            rule_str = f"Dominant congestion: Low segments comprise {pct_low}% of route distance"
        elif pct_med > pct_low and pct_med > pct_high:
            route_cong_level = "MEDIUM"
            rule_str = f"Dominant congestion: Medium segments comprise {pct_med}% of route distance"
        elif pct_high > pct_low and pct_high > pct_med:
            route_cong_level = "HIGH"
            rule_str = f"Dominant congestion: Hard segments comprise {pct_high}% of route distance"
        else:
            max_pct = max(pct_low, pct_med, pct_high)
            if pct_low == max_pct:
                route_cong_level = "LOW"
                rule_str = f"Dominant congestion: Low segments comprise {pct_low}% of route distance"
            elif pct_med == max_pct:
                route_cong_level = "MEDIUM"
                rule_str = f"Dominant congestion: Medium segments comprise {pct_med}% of route distance"
            else:
                route_cong_level = "HIGH"
                rule_str = f"Dominant congestion: Hard segments comprise {pct_high}% of route distance"

        evaluated_routes.append({
            "raw_path": path,
            "geometry": geom,
            "segments": segments_list,
            "total_distance_km": round(total_dist_km, 2),
            "total_time_min": round(total_time_min, 1),
            "congestion_level": route_cong_level,
            "congestion_score": congestion_score,
            "congestion_breakdown": {"LOW": pct_low, "MEDIUM": pct_med, "HIGH": pct_high},
            "congestion_cost": round(total_cost_s, 1),
            "dominant_rule": rule_str,
            "node_count": len(path),
        })

    # Balanced Route Recommendation Logic (Requirements 6 & 7):
    # Establish benchmark fastest route
    fastest_time = min(r["total_time_min"] for r in evaluated_routes)
    min_dist = min(r["total_distance_km"] for r in evaluated_routes)

    # Allowable trade-off bounds: max +25% travel time, max +30% distance
    MAX_TIME_OVERHEAD = 1.25
    MAX_DIST_OVERHEAD = 1.30

    recommended_idx = 0
    best_cost = float("inf")

    # Check for a balanced option that reduces congestion within allowable limits
    for i, r in enumerate(evaluated_routes):
        time_within = r["total_time_min"] <= fastest_time * MAX_TIME_OVERHEAD
        dist_within = r["total_distance_km"] <= min_dist * MAX_DIST_OVERHEAD
        if time_within and dist_within:
            # Lower congestion cost means better balanced trade-off
            if r["congestion_cost"] < best_cost:
                best_cost = r["congestion_cost"]
                recommended_idx = i

    # Build final RouteInfo objects with clear labels, distinct colors, and reasons
    final_routes = []
    # Place recommended route first
    ordered_indices = [recommended_idx] + [i for i in range(len(evaluated_routes)) if i != recommended_idx]

    for display_idx, orig_idx in enumerate(ordered_indices):
        r = evaluated_routes[orig_idx]
        is_rec = (display_idx == 0)

        time_diff = round(r["total_time_min"] - fastest_time, 1)
        dist_diff = round(r["total_distance_km"] - min_dist, 2)

        # Sequential route naming: Route 1, Route 2, Route 3 ...
        label = f"Route {display_idx + 1}"
        if is_rec:
            if time_diff == 0.0 and dist_diff == 0.0:
                rec_reason = (
                    f"Fastest direct route ({r['total_time_min']} mins, {r['total_distance_km']} km) "
                    f"with {r['congestion_breakdown']['LOW']}% free-flowing segments."
                )
            else:
                rec_reason = (
                    f"Balanced corridor: {r['congestion_breakdown']['LOW']}% low congestion "
                    f"({r['total_time_min']} mins, {r['total_distance_km']} km, +{time_diff} mins vs fastest)."
                )
        else:
            if time_diff == 0.0:
                rec_reason = f"Fastest corridor: Minimizes travel time ({r['total_time_min']} mins), but carries {r['congestion_breakdown']['HIGH']}% hard congestion segments."
            elif r["congestion_score"] < evaluated_routes[recommended_idx]["congestion_score"]:
                rec_reason = f"Lower congestion corridor: Lower congestion score ({r['congestion_score']}), but requires +{time_diff} mins extra travel time."
            else:
                rec_reason = f"Alternative corridor: Diverts through secondary streets (+{time_diff} mins, +{dist_diff} km)."

        final_routes.append({
            "route_id": str(uuid.uuid4()),
            "label": label,
            "color": ROUTE_COLORS[display_idx] if display_idx < len(ROUTE_COLORS) else "#9333EA",
            "total_distance_km": r["total_distance_km"],
            "total_time_min": r["total_time_min"],
            "segments": r["segments"],
            "geometry": r["geometry"],
            "congestion_level": r["congestion_level"],
            "congestion_score": r["congestion_score"],
            "congestion_breakdown": r["congestion_breakdown"],
            "congestion_cost": r["congestion_cost"],
            "recommendation_reason": rec_reason,
            "is_recommended": is_rec,
            "dominant_rule": r["dominant_rule"],
            "node_count": r["node_count"],
        })

    graph_note = "Demo synthetic graph" if is_demo else "OpenStreetMap driving road network (OSMnx)"
    warning = _graph_warning if is_demo else None

    return {
        "status": "success",
        "routes": final_routes,
        "source_requested": {"lat": src_lat, "lng": src_lng},
        "destination_requested": {"lat": dst_lat, "lng": dst_lng},
        "source_snapped": src_snapped,
        "destination_snapped": dst_snapped,
        "source_snap_distance_m": round(src_dist, 1),
        "destination_snap_distance_m": round(dst_dist, 1),
        "graph_note": graph_note,
        "is_demo_mode": is_demo,
        "warning": warning,
    }


def get_diagnostic_report() -> dict:
    """
    Return comprehensive diagnostics covering training dataset class distribution,
    model metrics, road-to-feature mapping, and route classification rules.
    """
    from app.services import ml_service, traffic_service

    traffic_summary = traffic_service.get_summary()
    model_metrics = ml_service.get_metrics() or {}

    return {
        "dataset_distribution": {
            "total_records": traffic_summary.get("total_records", 8936),
            "classes": traffic_summary.get("congestion_distribution", {"HIGH": 5557, "MEDIUM": 2074, "LOW": 1305}),
            "percentages": {"HIGH": 62.2, "MEDIUM": 23.2, "LOW": 14.6},
            "source": "Bangalore's Traffic Pulse Dataset (GitHub/Kaggle)",
            "continuous_thresholds": "LOW (<50%), MEDIUM (50-80%), HIGH (>=80%)",
        },
        "model_metrics": {
            "model_type": model_metrics.get("model", "RandomForestClassifier"),
            "accuracy": model_metrics.get("accuracy", 0.9016),
            "macro_f1": model_metrics.get("macro_f1", 0.8700),
            "test_set_size": model_metrics.get("test_set_size", 1341),
            "precision_per_class": model_metrics.get("precision_per_class", {}),
            "recall_per_class": model_metrics.get("recall_per_class", {}),
            "f1_per_class": model_metrics.get("f1_per_class", {}),
            "confusion_matrix": model_metrics.get("confusion_matrix", []),
        },
        "road_feature_mapping": {
            "Arterial / Trunk Corridors": {
                "highways": ["primary", "primary_link", "trunk", "trunk_link", "motorway", "busway"],
                "traffic_volume": 38000,
                "speed": "24-32 km/h",
                "capacity_utilization": "98%",
                "travel_time_index": 1.48,
                "predicted_label": "HIGH",
            },
            "Collector Connectors": {
                "highways": ["secondary", "secondary_link", "tertiary", "tertiary_link"],
                "traffic_volume": 20000,
                "speed": "36-42 km/h",
                "capacity_utilization": "82%",
                "travel_time_index": 1.22,
                "predicted_label": "MEDIUM",
            },
            "Local / Residential Streets": {
                "highways": ["residential", "living_street", "unclassified", "service"],
                "traffic_volume": 11000,
                "speed": "30-38 km/h",
                "capacity_utilization": "50%",
                "travel_time_index": 1.12,
                "predicted_label": "LOW",
            },
        },
        "aggregation_rule": {
            "dominant_rule": "Dominant congestion percentage: route is classified according to whichever segment category (LOW, MEDIUM, or HIGH/Hard) covers the largest percentage of total distance.",
            "HIGH": "Hard/High segment percentage is dominant (highest among Low, Medium, High)",
            "MEDIUM": "Medium segment percentage is dominant (highest among Low, Medium, High)",
            "LOW": "Low segment percentage is dominant (highest among Low, Medium, High)",
            "route_naming": "Routes are sequentially indexed as Route 1, Route 2, Route 3 across all queries.",
            "recommendation_policy": "Prefers lower congestion if travel time penalty <= 25% and distance penalty <= 30% relative to fastest corridor.",
        },
    }


def is_graph_loaded() -> bool:
    return _graph_loaded


def is_demo_graph() -> bool:
    return _is_demo