"""tests/test_preprocessing.py"""
import sys
import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "ml"))

from preprocessing import (
    generate_demo_dataset,
    clean_data,
    build_preprocessor,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET_COLUMN,
)


def test_demo_dataset_shape():
    df = generate_demo_dataset(n_rows=200)
    assert len(df) == 200
    assert "Congestion Level" in df.columns
    assert "_demo_mode" in df.columns
    assert df["_demo_mode"].all()


def test_demo_dataset_no_nulls_in_key_columns():
    df = generate_demo_dataset(n_rows=500)
    for col in ["Traffic Volume", "Average Speed (km/h)", "Congestion Level"]:
        assert df[col].notna().all(), f"Null found in {col}"


def test_congestion_level_distribution():
    df = generate_demo_dataset(n_rows=1000)
    cleaned = clean_data(df, is_demo=True)
    dist = cleaned[TARGET_COLUMN].value_counts()
    # All three levels should be present
    assert set(dist.index) == {"LOW", "MEDIUM", "HIGH"}
    # No level should dominate to > 80%
    max_frac = dist.max() / dist.sum()
    assert max_frac < 0.80, f"One class dominates: {max_frac:.2%}"


def test_clean_data_drops_nulls_in_target():
    df = generate_demo_dataset(n_rows=200)
    df.loc[0:10, "Congestion Level"] = None
    cleaned = clean_data(df, is_demo=True)
    assert cleaned[TARGET_COLUMN].notna().all()


def test_clean_data_adds_day_of_week():
    df = generate_demo_dataset(n_rows=100)
    cleaned = clean_data(df, is_demo=True)
    assert "DayOfWeek" in cleaned.columns
    assert cleaned["DayOfWeek"].between(0, 6).all()


def test_preprocessor_transforms_correctly():
    df = generate_demo_dataset(n_rows=300)
    cleaned = clean_data(df, is_demo=True)
    X = cleaned[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)
    assert X_transformed.shape[0] == len(cleaned)
    # 7 numeric + 2 categorical = 9 features
    assert X_transformed.shape[1] == len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)


def test_no_target_leakage():
    df = generate_demo_dataset(n_rows=100)
    cleaned = clean_data(df, is_demo=True)
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    available = [c for c in feature_cols if c in cleaned.columns]
    leakage = [c for c in available if "congestion" in c.lower() and c != TARGET_COLUMN]
    assert len(leakage) == 0, f"Target leakage detected: {leakage}"


def test_real_dataset_preprocessing():
    """Verify loading and preprocessing on the real Bangalore Traffic Pulse dataset."""
    from preprocessing import RAW_DATA_PATH, load_raw_data
    if not RAW_DATA_PATH.exists():
        pytest.skip("Real dataset not present at data/raw/Banglore_traffic_Dataset.csv")

    df_raw, is_demo = load_raw_data()
    assert is_demo is False
    assert len(df_raw) == 8936
    assert "Congestion Level" in df_raw.columns

    cleaned = clean_data(df_raw, is_demo=False)
    assert len(cleaned) == 8936
    assert TARGET_COLUMN in cleaned.columns
    assert set(cleaned[TARGET_COLUMN].unique()) == {"LOW", "MEDIUM", "HIGH"}

    X = cleaned[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    prep = build_preprocessor()
    X_trans = prep.fit_transform(X)
    assert X_trans.shape[0] == 8936
    assert X_trans.shape[1] == len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)
