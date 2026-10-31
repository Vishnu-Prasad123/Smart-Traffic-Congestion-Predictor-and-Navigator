"""
backend/app/services/traffic_service.py
-----------------------------------------
Loads the processed traffic data and computes analytics summaries.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)
_df: Optional[pd.DataFrame] = None
_stats: Optional[dict] = None
_is_demo = False

DAY_NAMES = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _get_settings():
    from app.core.config import settings
    return settings


def load_traffic_data() -> bool:
    global _df, _stats, _is_demo
    settings = _get_settings()

    try:
        if settings.PROCESSED_DATA_PATH.exists():
            _df = pd.read_csv(settings.PROCESSED_DATA_PATH)
            _is_demo = bool(_df.get("_demo_mode", pd.Series([False])).iloc[0]) if "_demo_mode" in _df.columns else False
            logger.info(f"Loaded traffic data: {len(_df)} rows, demo={_is_demo}")
        else:
            logger.warning("Processed data not found, using minimal fallback.")
            _df = _generate_minimal_df()
            _is_demo = True

        if settings.FEATURE_STATS_PATH.exists():
            with open(settings.FEATURE_STATS_PATH) as f:
                _stats = json.load(f)
        return True
    except Exception as e:
        logger.error(f"Failed to load traffic data: {e}")
        _df = _generate_minimal_df()
        _is_demo = True
        return False


def _generate_minimal_df() -> pd.DataFrame:
    """Tiny fallback dataframe for health responses when no data file exists."""
    import numpy as np
    rng = np.random.default_rng(0)
    n = 500
    return pd.DataFrame({
        "Traffic Volume": rng.integers(100, 8000, n),
        "Average Speed (km/h)": rng.uniform(5, 80, n).round(1),
        "CongestionLabel": rng.choice(["LOW", "MEDIUM", "HIGH"], n),
        "Area Name": rng.choice(["Koramangala", "Indiranagar", "Whitefield"], n),
        "DayOfWeek": rng.integers(0, 7, n),
        "_demo_mode": True,
    })


def get_summary() -> dict:
    if _df is None:
        load_traffic_data()

    df = _df.copy()
    total = len(df)

    # Congestion distribution
    cong_col = "CongestionLabel" if "CongestionLabel" in df.columns else "Congestion Level"
    cong_dist = df[cong_col].value_counts().to_dict() if cong_col in df.columns else {}
    for k in ["LOW", "MEDIUM", "HIGH"]:
        cong_dist.setdefault(k, 0)

    # Average volume by day of week
    vol_col = "Traffic Volume"
    avg_vol_by_day = {}
    if "DayOfWeek" in df.columns and vol_col in df.columns:
        df[vol_col] = pd.to_numeric(df[vol_col], errors="coerce")
        for day_idx, day_name in DAY_NAMES.items():
            subset = df[df["DayOfWeek"] == day_idx][vol_col].dropna()
            avg_vol_by_day[day_name] = round(float(subset.mean()), 1) if len(subset) > 0 else 0.0

    # Average speed by congestion level
    speed_col = "Average Speed (km/h)"
    avg_speed_by_cong = {}
    if speed_col in df.columns and cong_col in df.columns:
        df[speed_col] = pd.to_numeric(df[speed_col], errors="coerce")
        for level in ["LOW", "MEDIUM", "HIGH"]:
            subset = df[df[cong_col] == level][speed_col].dropna()
            avg_speed_by_cong[level] = round(float(subset.mean()), 1) if len(subset) > 0 else 0.0

    # Top areas by record count with dominant congestion
    top_areas = []
    if "Area Name" in df.columns:
        for area, grp in df.groupby("Area Name"):
            dom_cong = grp[cong_col].mode().iloc[0] if cong_col in grp.columns and len(grp) > 0 else "N/A"
            avg_v = round(float(grp[vol_col].mean()), 1) if vol_col in grp.columns else 0.0
            avg_s = round(float(grp[speed_col].mean()), 1) if speed_col in grp.columns else 0.0
            top_areas.append({"area": area, "avg_volume": avg_v, "avg_speed": avg_s, "dominant_congestion": dom_cong})
        top_areas = sorted(top_areas, key=lambda x: x["avg_volume"], reverse=True)[:10]

    # Volume over time (sample by date if available, else by index)
    vol_over_time = []
    if "Date" in df.columns and vol_col in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df_dated = df.dropna(subset=["Date"]).sort_values("Date")
        if len(df_dated) > 0:
            monthly = df_dated.groupby(df_dated["Date"].dt.to_period("M"))[vol_col].mean()
            for period, val in monthly.items():
                vol_over_time.append({"period": str(period), "avg_volume": round(float(val), 1)})
    if not vol_over_time:
        for i in range(12):
            vol_over_time.append({"period": f"Month {i+1}", "avg_volume": float(rng_val(1000, 5000))})

    # Date range
    date_range = {"min": "N/A", "max": "N/A"}
    if _stats and "date_range" in _stats:
        date_range = _stats["date_range"]
    elif "Date" in df.columns:
        parsed = pd.to_datetime(df["Date"], errors="coerce").dropna()
        if len(parsed) > 0:
            date_range = {"min": str(parsed.min()), "max": str(parsed.max())}

    return {
        "total_records": total,
        "is_demo_mode": _is_demo,
        "congestion_distribution": cong_dist,
        "avg_volume_by_day": avg_vol_by_day,
        "avg_speed_by_congestion": avg_speed_by_cong,
        "top_areas": top_areas,
        "volume_over_time": vol_over_time[:24],
        "date_range": date_range,
        "data_note": (
            "DEMO DATA - statistically representative but not real observations."
            if _is_demo else
            "Real data from Bangalore Traffic Pulse dataset (Kaggle)."
        ),
    }


def rng_val(lo, hi):
    import random
    return round(random.uniform(lo, hi), 1)


def get_area_congestion_lookup() -> Dict[str, str]:
    """Return a mapping of area name -> dominant congestion level for routing."""
    if _df is None:
        load_traffic_data()
    if _df is None:
        return {}
    df = _df.copy()
    cong_col = "CongestionLabel" if "CongestionLabel" in df.columns else "Congestion Level"
    if "Area Name" not in df.columns or cong_col not in df.columns:
        return {}
    lookup = {}
    for area, grp in df.groupby("Area Name"):
        if len(grp) > 0:
            mode_val = grp[cong_col].mode()
            lookup[area] = mode_val.iloc[0] if len(mode_val) > 0 else "LOW"
    return lookup
