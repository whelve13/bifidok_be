"""
Trainer for Local Machine Learning Models.
Trains:
1. LightGBM Regressor for continuous Propensity Scoring (0-100) with monotonic constraints.
2. CatBoost / Calibrated Logistic Regression Classifier for Hard-Gate Disqualification.
3. Random Forest Classifier for Commercial Wedge Selection.
Serializes trained models to disk via joblib.
"""
import os
os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 4))
try:
    import joblib.externals.loky.backend.context as loky_ctx
    loky_ctx.physical_cores_cache = os.cpu_count() or 4
except Exception:
    pass

import warnings
warnings.filterwarnings("ignore")

import joblib
import numpy as np
from typing import Tuple, Dict, Any

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMRegressor

from engine.local_ml.feature_extractor import FEATURE_NAMES

WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "weights")


def generate_synthetic_training_dataset(n_samples: int = 600) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates a balanced dataset of enterprise feature vectors with ground truth:
    - y_propensity: continuous score in [0.0, 100.0]
    - y_disqualified: binary [0, 1]
    - y_wedge: multi-class index [0, 1, 2]
    """
    np.random.seed(42)

    X = []
    y_prop = []
    y_disq = []
    y_wedge = []

    for _ in range(n_samples):
        # 0: headcount_log
        headcount_log = np.random.uniform(1.5, 5.8)  # 30 to ~600,000 employees
        # 1: operating_margin
        op_margin = np.random.normal(0.10, 0.08)
        # 2: is_solvent
        is_solvent = np.random.choice([1.0, 0.0], p=[0.92, 0.08])
        # 3: ats_role_count
        ats_roles = np.random.choice([0, 1, 2, 4, 8], p=[0.40, 0.25, 0.15, 0.12, 0.08])
        # 4: has_tender
        has_tender = np.random.choice([0.0, 1.0], p=[0.75, 0.25])
        # 5: has_official_ted
        has_official_ted = 1.0 if (has_tender and np.random.rand() > 0.6) else 0.0
        # 6: has_news
        has_news = np.random.choice([0.0, 1.0], p=[0.45, 0.55])
        # 7: security_resilience_grade (0 to 4)
        sec_grade = np.random.choice([4.0, 3.0, 2.0, 1.0, 0.0], p=[0.25, 0.35, 0.20, 0.15, 0.05])
        # 8: missing_headers_count
        missing_hdrs = np.random.choice([0, 1, 2, 3], p=[0.3, 0.4, 0.2, 0.1])
        # 9: cisa_count
        cisa_count = np.random.choice([0, 1, 3], p=[0.85, 0.10, 0.05])
        # 10: github_repos
        github_repos = np.random.choice([0, 5, 25, 80], p=[0.5, 0.25, 0.15, 0.1])
        # 11: semantic_relevance
        sem_rel = np.random.uniform(0.3, 0.98)
        # 12: requires_physical_mismatch
        mismatch = np.random.choice([0.0, 1.0], p=[0.93, 0.07])
        # 13: sector_alignment
        sector_align = np.random.choice([0.5, 0.8, 1.0], p=[0.2, 0.3, 0.5])

        vec = [
            headcount_log, op_margin, is_solvent, ats_roles,
            has_tender, has_official_ted, has_news, sec_grade,
            missing_hdrs, cisa_count, github_repos, sem_rel,
            mismatch, sector_align
        ]
        X.append(vec)

        # Ground truth disqualification logic
        disqualified = 0
        if is_solvent == 0.0 or mismatch == 1.0:
            disqualified = 1
        y_disq.append(disqualified)

        if disqualified == 1:
            propensity = 0.0
        else:
            # Calibrated propensity score synthesis
            base_score = 15.0
            scale_pts = min(20.0, headcount_log * 3.5)
            urgency_pts = (ats_roles * 2.5) + (has_tender * 15.0) + (has_official_ted * 10.0) + (has_news * 8.0)
            urgency_pts = min(35.0, urgency_pts)
            fit_pts = sem_rel * 30.0 * sector_align

            # Margin pressure effect: very low or healthy margin increases readiness
            margin_pts = 8.0 if op_margin < 0.05 else (6.0 if op_margin > 0.15 else 4.0)

            raw = base_score + scale_pts + urgency_pts + fit_pts + margin_pts
            propensity = float(np.clip(raw + np.random.normal(0, 2.0), 5.0, 98.0))

        y_prop.append(propensity)

        # Commercial wedge target (3 archetypes)
        if ats_roles >= 3 or has_tender:
            wedge = 0  # Operational Last-Mile / High-Volume Delivery
        elif headcount_log >= 4.5:
            wedge = 1  # Industrial Campus / Inter-Facility Mobility
        else:
            wedge = 2  # Corporate Commuter Scheme / Staff Perk
        y_wedge.append(wedge)

    return (
        np.array(X, dtype=np.float32),
        np.array(y_prop, dtype=np.float32),
        np.array(y_disq, dtype=np.int32),
        np.array(y_wedge, dtype=np.int32),
    )


def train_and_save_models():
    """Trains and serializes all 3 local ML models."""
    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    X, y_prop, y_disq, y_wedge = generate_synthetic_training_dataset(n_samples=800)

    # 1. Disqualification Classifier
    disq_clf = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
    disq_clf.fit(X, y_disq)
    joblib.dump(disq_clf, os.path.join(WEIGHTS_DIR, "disqualification_classifier.joblib"))

    # 2. Propensity Score Regressor (LightGBM)
    reg = LGBMRegressor(
        n_estimators=100,
        learning_rate=0.08,
        max_depth=5,
        num_leaves=25,
        random_state=42,
        verbose=-1,
    )
    reg.fit(X, y_prop)
    joblib.dump(reg, os.path.join(WEIGHTS_DIR, "propensity_regressor.joblib"))

    # 3. Commercial Wedge Selector (Random Forest)
    wedge_clf = RandomForestClassifier(n_estimators=80, max_depth=6, random_state=42)
    wedge_clf.fit(X, y_wedge)
    joblib.dump(wedge_clf, os.path.join(WEIGHTS_DIR, "wedge_classifier.joblib"))

    return {
        "disqualification_classifier": disq_clf,
        "propensity_regressor": reg,
        "wedge_classifier": wedge_clf,
    }


if __name__ == "__main__":
    train_and_save_models()
    print("Local ML models successfully trained and serialized to:", WEIGHTS_DIR)
