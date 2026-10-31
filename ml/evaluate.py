"""
ml/evaluate.py
--------------
Evaluate the trained Random Forest on the held-out test set.
Saves genuine metrics and feature importances as JSON.
"""
import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    classification_report,
)
from sklearn.model_selection import train_test_split
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "ml"))

ARTIFACTS_DIR = BASE_DIR / "ml" / "artifacts"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
FEATURE_IMPORTANCE_PATH = ARTIFACTS_DIR / "feature_importance.json"
MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "cleaned_traffic.csv"

from preprocessing import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TARGET_COLUMN


def evaluate():
    if not MODEL_PATH.exists():
        logger.error("Model not found. Run train.py first.")
        return None

    pipeline = joblib.load(MODEL_PATH)
    df = pd.read_csv(PROCESSED_DATA_PATH)

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    available = [c for c in feature_cols if c in df.columns]
    X = df[available]
    y = df[TARGET_COLUMN].astype(str)

    # Reproduce same test split as train.py
    _, X_temp, _, y_temp = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
    _, X_test, _, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp)

    y_pred = pipeline.predict(X_test)
    classes = sorted(y.unique().tolist())

    acc = accuracy_score(y_test, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=classes, zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

    metrics = {
        "model": "RandomForestClassifier",
        "accuracy": round(float(acc), 4),
        "classes": classes,
        "precision_per_class": {c: round(float(p), 4) for c, p in zip(classes, precision)},
        "recall_per_class": {c: round(float(r), 4) for c, r in zip(classes, recall)},
        "f1_per_class": {c: round(float(fv), 4) for c, fv in zip(classes, f1)},
        "support_per_class": {c: int(s) for c, s in zip(classes, support)},
        "macro_f1": round(float(f1.mean()), 4),
        "confusion_matrix": cm,
        "test_set_size": int(len(X_test)),
        "total_records": int(len(df)),
        "n_features": len(available),
        "feature_names": available,
        "is_demo_mode": False,
    }

    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics -> {METRICS_PATH}")

    # Feature importances
    rf = pipeline.named_steps["classifier"]
    importances = rf.feature_importances_
    all_feature_names = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    all_feature_names = all_feature_names[:len(importances)]
    importance_dict = dict(
        sorted(
            {n: round(float(v), 6) for n, v in zip(all_feature_names, importances)}.items(),
            key=lambda x: -x[1],
        )
    )
    with open(FEATURE_IMPORTANCE_PATH, "w") as f:
        json.dump(importance_dict, f, indent=2)
    logger.info(f"Saved feature importance -> {FEATURE_IMPORTANCE_PATH}")

    logger.info(f"Test Accuracy: {acc:.4f} | Macro F1: {f1.mean():.4f}")
    print(classification_report(y_test, y_pred, labels=classes, zero_division=0))
    return metrics


if __name__ == "__main__":
    result = evaluate()
    if result:
        print(json.dumps(result, indent=2))
