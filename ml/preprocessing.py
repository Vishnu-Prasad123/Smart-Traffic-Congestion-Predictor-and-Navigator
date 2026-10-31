"""
ml/preprocessing.py
-------------------
Preprocessing pipeline for Bangalore Traffic Pulse dataset.

If the real Kaggle CSV is missing, a clearly-labelled demo dataset is generated.
All decisions and thresholds are documented inline.
"""

import os
import json
import logging
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
from sklearn.impute import SimpleImputer
import joblib

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "Banglore_traffic_Dataset.csv"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
PREPROCESSOR_PATH = ARTIFACTS_DIR / "preprocessor.joblib"
PROCESSED_DATA_PATH = PROCESSED_DIR / "cleaned_traffic.csv"
FEATURE_STATS_PATH = PROCESSED_DIR / "feature_stats.json"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

NUMERIC_FEATURES = [
    "Traffic Volume",
    "Average Speed (km/h)",
    "Travel Time Index",
    "Road Capacity Utilization (%)",
    "Incident Reports",
    "DayOfWeek",
    "Month",
]
CATEGORICAL_FEATURES = ["Weather Conditions", "Roadwork and Construction Activity"]
TARGET_COLUMN = "CongestionLabel"


def generate_demo_dataset(n_rows=5000):
    """Generate a clearly-labelled demo dataset when real data is unavailable."""
    rng = np.random.default_rng(42)
    areas = [
        "Koramangala", "Indiranagar", "Whitefield", "Electronic City",
        "MG Road", "Silk Board", "Hebbal", "Marathahalli",
        "Jayanagar", "BTM Layout",
    ]
    roads = [
        "100 Feet Road", "Outer Ring Road", "Hosur Road", "Old Airport Road",
        "Bannerghatta Road", "NH 44", "Tumkur Road", "Bellary Road",
        "Sarjapur Road", "Kanakapura Road",
    ]
    weathers = ["Clear", "Rainy", "Cloudy", "Foggy"]
    roadworks = ["Yes", "No"]
    n = n_rows
    dates = pd.date_range("2023-01-01", periods=n, freq="h")
    volume = rng.integers(100, 8001, n)
    speed = rng.uniform(5, 80, n)
    capacity = rng.uniform(10, 110, n)
    tti = rng.uniform(1.0, 4.5, n)
    incidents = rng.integers(0, 11, n)
    score = (
        0.4 * (volume / 8000)
        + 0.3 * (1 - speed / 80)
        + 0.2 * (capacity / 110)
        + 0.1 * (tti / 4.5)
    )
    congestion = pd.cut(score, bins=[0, 0.35, 0.65, 1.1], labels=["Low", "Medium", "High"])
    df = pd.DataFrame({
        "Date": dates.strftime("%Y-%m-%d"),
        "Area Name": rng.choice(areas, n),
        "Road/Intersection Name": rng.choice(roads, n),
        "Traffic Volume": volume,
        "Average Speed (km/h)": speed.round(1),
        "Travel Time Index": tti.round(2),
        "Congestion Level": congestion,
        "Road Capacity Utilization (%)": capacity.round(1),
        "Incident Reports": incidents,
        "Environmental Impact": rng.uniform(50, 200, n).round(1),
        "Weather Conditions": rng.choice(weathers, n, p=[0.5, 0.25, 0.15, 0.1]),
        "Roadwork and Construction Activity": rng.choice(roadworks, n, p=[0.2, 0.8]),
        "_demo_mode": True,
    })
    return df


def load_raw_data():
    if RAW_DATA_PATH.exists():
        logger.info(f"Loading real dataset from {RAW_DATA_PATH}")
        df = pd.read_csv(RAW_DATA_PATH, encoding="utf-8")
        df.columns = df.columns.str.strip()
        df["_demo_mode"] = False
        return df, False
    else:
        logger.warning(f"Real dataset not found at {RAW_DATA_PATH}. Generating demo data.")
        df = generate_demo_dataset()
        return df, True


def normalize_weather(val: str) -> str:
    """Normalize weather labels across Kaggle dataset, demo data, and user input."""
    v = str(val).strip().capitalize()
    if v in ["Rain", "Rainy"]:
        return "Rain"
    if v in ["Overcast", "Cloudy"]:
        return "Overcast"
    if v in ["Fog", "Foggy"]:
        return "Fog"
    if v in ["Windy"]:
        return "Windy"
    if v in ["Clear"]:
        return "Clear"
    return "Unknown"


def clean_data(df, is_demo):
    df = df.copy()
    for old, new in [
        ("Average Speed", "Average Speed (km/h)"),
        ("Road Capacity Utilization", "Road Capacity Utilization (%)"),
        ("Travel Time Index", "Travel Time Index"),
    ]:
        candidates = [c for c in df.columns if old.lower() in c.lower()]
        if candidates and new not in df.columns:
            df = df.rename(columns={candidates[0]: new})

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        try:
            df["DayOfWeek"] = df["Date"].dt.day_of_week
        except AttributeError:
            df["DayOfWeek"] = df["Date"].dt.dayofweek
        df["Month"] = df["Date"].dt.month
    else:
        df["DayOfWeek"] = 0
        df["Month"] = 1

    if "Weather Conditions" in df.columns:
        df["Weather Conditions"] = df["Weather Conditions"].apply(normalize_weather)

    if "Congestion Level" in df.columns:
        # Check if numeric (real dataset float) or string categorical (demo mode)
        c_num = pd.to_numeric(df["Congestion Level"], errors="coerce")
        if c_num.notna().sum() > len(df) * 0.5:
            # Numeric percentage: bin into standard traffic tiers LOW (<50%), MEDIUM (50-80%), HIGH (>=80%)
            df[TARGET_COLUMN] = pd.cut(
                c_num,
                bins=[-float("inf"), 50.0, 80.0, float("inf")],
                labels=["LOW", "MEDIUM", "HIGH"]
            )
        else:
            raw_c = df["Congestion Level"].astype(str).str.strip().str.upper()
            df[TARGET_COLUMN] = raw_c.map({"LOW": "LOW", "MEDIUM": "MEDIUM", "HIGH": "HIGH"})
    else:
        cap = pd.to_numeric(df.get("Road Capacity Utilization (%)", pd.Series([50]*len(df))), errors="coerce").fillna(50)
        df[TARGET_COLUMN] = pd.cut(cap, bins=[-float("inf"), 40, 75, float("inf")],
                                   labels=["LOW", "MEDIUM", "HIGH"])

    for col in NUMERIC_FEATURES:
        if col not in df.columns:
            df[col] = float("nan")
    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            df[col] = "Unknown"

    df = df.dropna(subset=[TARGET_COLUMN])
    df = df.drop_duplicates()
    logger.info(f"Cleaned dataset: {len(df)} rows, is_demo={is_demo}")
    return df


def build_preprocessor():
    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("encoder", OrdinalEncoder(
            categories=[["Clear", "Overcast", "Fog", "Rain", "Windy", "Unknown"],
                        ["Yes", "No", "Unknown"]],
            handle_unknown="use_encoded_value",
            unknown_value=-1,
        )),
    ])
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def run_preprocessing():
    df_raw, is_demo = load_raw_data()
    df = clean_data(df_raw, is_demo)
    df.to_csv(PROCESSED_DATA_PATH, index=False)
    logger.info(f"Saved cleaned data -> {PROCESSED_DATA_PATH}")

    stats = {
        "is_demo_mode": is_demo,
        "total_records": len(df),
        "congestion_distribution": df[TARGET_COLUMN].value_counts().to_dict(),
        "numeric_stats": {
            col: df[col].dropna().describe().to_dict()
            for col in NUMERIC_FEATURES if col in df.columns
        },
        "date_range": {
            "min": str(df["Date"].min()) if "Date" in df.columns and not df["Date"].isna().all() else "N/A",
            "max": str(df["Date"].max()) if "Date" in df.columns and not df["Date"].isna().all() else "N/A",
        },
        "areas": df["Area Name"].value_counts().head(10).to_dict() if "Area Name" in df.columns else {},
    }
    with open(FEATURE_STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    logger.info(f"Saved feature stats -> {FEATURE_STATS_PATH}")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    preprocessor = build_preprocessor()
    preprocessor.fit(X)
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    logger.info(f"Saved preprocessor -> {PREPROCESSOR_PATH}")
    return {**stats, "preprocessor_path": str(PREPROCESSOR_PATH)}


if __name__ == "__main__":
    result = run_preprocessing()
    print(json.dumps(result, indent=2, default=str))
