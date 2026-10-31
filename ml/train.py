"""
ml/train.py
-----------
Train a Random Forest classifier on the Bangalore Traffic Pulse dataset.
"""
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "ml"))

ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
PREPROCESSOR_PATH = ARTIFACTS_DIR / "preprocessor.joblib"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "cleaned_traffic.csv"
TRAIN_SPLIT_PATH = ARTIFACTS_DIR / "train_split_info.json"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

from preprocessing import (
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    TARGET_COLUMN,
    build_preprocessor,
    run_preprocessing,
)


def load_data():
    if not PROCESSED_DATA_PATH.exists():
        logger.info("Processed data not found. Running preprocessing...")
        run_preprocessing()
    df = pd.read_csv(PROCESSED_DATA_PATH)
    return df


def train():
    df = load_data()
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    available_features = [c for c in feature_cols if c in df.columns]
    X = df[available_features]
    y = df[TARGET_COLUMN].astype(str)

    # Verify no target leakage
    leakage_cols = [c for c in X.columns if "congestion" in c.lower() or "label" in c.lower()]
    if leakage_cols:
        raise AssertionError(f"Potential target leakage in features: {leakage_cols}")

    # 70 / 15 / 15 stratified split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    logger.info(f"Split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    # Save split info for reporting
    split_info = {
        "total": len(df),
        "train": len(X_train),
        "val": len(X_val),
        "test": len(X_test),
        "features": available_features,
        "target": TARGET_COLUMN,
    }
    with open(TRAIN_SPLIT_PATH, "w") as f:
        json.dump(split_info, f, indent=2)

    preprocessor = build_preprocessor()
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    full_pipeline = Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", rf),
    ])

    full_pipeline.fit(X_train, y_train)
    val_score = full_pipeline.score(X_val, y_val)
    logger.info(f"Validation accuracy: {val_score:.4f}")

    joblib.dump(full_pipeline, MODEL_PATH)
    logger.info(f"Saved model -> {MODEL_PATH}")

    # Save preprocessor separately for inference convenience
    joblib.dump(full_pipeline.named_steps["preprocessor"], PREPROCESSOR_PATH)
    logger.info(f"Saved preprocessor -> {PREPROCESSOR_PATH}")

    return full_pipeline, X_test, y_test, available_features


if __name__ == "__main__":
    pipeline, X_test, y_test, features = train()
    logger.info("Training complete.")
    print(f"Model saved to: {MODEL_PATH}")
    print(f"Run evaluate.py to generate metrics.")
