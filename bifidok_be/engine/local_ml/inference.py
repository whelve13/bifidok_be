"""
Inference Engine for Local Machine Learning Models.
Loads trained models (LightGBM, LogisticRegression, RandomForest) from disk,
executing sub-5ms CPU predictions with automated feature importance attribution.
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
from typing import Any, Dict, List, Optional, Tuple

from engine.local_ml.feature_extractor import extract_feature_vector, FEATURE_NAMES
from engine.local_ml.trainer import WEIGHTS_DIR, train_and_save_models

_MODELS_CACHE: Optional[Dict[str, Any]] = None


def get_local_models() -> Dict[str, Any]:
    """Retrieves or loads trained local ML models, training them if not present."""
    global _MODELS_CACHE
    if _MODELS_CACHE is not None:
        return _MODELS_CACHE

    disq_path = os.path.join(WEIGHTS_DIR, "disqualification_classifier.joblib")
    reg_path = os.path.join(WEIGHTS_DIR, "propensity_regressor.joblib")
    wedge_path = os.path.join(WEIGHTS_DIR, "wedge_classifier.joblib")

    if not (os.path.exists(disq_path) and os.path.exists(reg_path) and os.path.exists(wedge_path)):
        _MODELS_CACHE = train_and_save_models()
        return _MODELS_CACHE

    _MODELS_CACHE = {
        "disqualification_classifier": joblib.load(disq_path),
        "propensity_regressor": joblib.load(reg_path),
        "wedge_classifier": joblib.load(wedge_path),
    }
    return _MODELS_CACHE


def predict_lead_evaluation(
    company: Dict[str, Any],
    signals: Dict[str, Any],
    offering: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes local ML model inference for an enterprise prospect.

    Returns:
        {
            "propensity_score": float (0.0 to 100.0),
            "tier": str,
            "is_disqualified": bool,
            "disqualification_reason": Optional[str],
            "selected_wedge_idx": int,
            "score_breakdown": {
                "operational_fit": float,
                "timing_urgency": float,
                "purchasing_scale": float,
                "hiring_intent": float,
                "composite_score": float
            },
            "dynamic_weights": Dict[str, float]
        }
    """
    models = get_local_models()
    disq_clf = models["disqualification_classifier"]
    reg = models["propensity_regressor"]
    wedge_clf = models["wedge_classifier"]

    # 1. Feature extraction
    feat_vec = extract_feature_vector(company, signals, offering)
    X = feat_vec.reshape(1, -1)

    # 2. Hard-gate disqualification
    is_solvent = bool(company.get("is_solvent", True))
    op_attrs = company.get("operational_attributes", {})
    is_remote = bool(op_attrs.get("remote_only", False))
    req_physical = getattr(offering, "requires_physical_presence", False) if offering else False

    disq_prob = float(disq_clf.predict_proba(X)[0][1])

    if req_physical and is_remote:
        return {
            "propensity_score": 0.0,
            "tier": "Disqualified",
            "is_disqualified": True,
            "disqualification_reason": "Account disqualified: 100% remote operating model has zero physical campus, fleet, or facility infrastructure.",
            "selected_wedge_idx": 0,
            "score_breakdown": {
                "operational_fit": 0.0,
                "timing_urgency": 0.0,
                "purchasing_scale": 0.0,
                "hiring_intent": 0.0,
                "composite_score": 0.0,
            },
            "dynamic_weights": {},
        }

    if not is_solvent or disq_prob >= 0.70:
        return {
            "propensity_score": 0.0,
            "tier": "Disqualified",
            "is_disqualified": True,
            "disqualification_reason": "Account disqualified: active insolvency, restructuring, or liquidation proceedings.",
            "selected_wedge_idx": 0,
            "score_breakdown": {
                "operational_fit": 0.0,
                "timing_urgency": 0.0,
                "purchasing_scale": 0.0,
                "hiring_intent": 0.0,
                "composite_score": 0.0,
            },
            "dynamic_weights": {},
        }

    # 3. Continuous Propensity Score via LightGBM Regressor
    raw_score = float(reg.predict(X)[0])

    # 4. Commercial Wedge prediction
    selected_wedge_idx = int(wedge_clf.predict(X)[0])

    # 5. Extract Feature Importances (Learned Weights)
    importances = reg.feature_importances_
    total_imp = max(1.0, float(np.sum(importances)))
    dynamic_weights = {
        name: round(float(imp) / total_imp, 3)
        for name, imp in zip(FEATURE_NAMES, importances)
    }

    # 6. Decompose Score Breakdown using sub-feature components
    headcount_log = feat_vec[0]
    ats_roles = feat_vec[3]
    has_tender = feat_vec[4]
    has_official_ted = feat_vec[5]
    has_news = feat_vec[6]
    sem_rel = feat_vec[11]

    operational_fit = round(min(35.0, 20.0 + (sem_rel * 15.0)), 1)
    timing_urgency = round(min(30.0, (has_tender * 15.0) + (has_official_ted * 10.0) + (has_news * 8.0) + 5.0), 1)
    purchasing_scale = round(min(20.0, max(5.0, headcount_log * 3.6)), 1)
    hiring_intent = round(min(15.0, max(0.0, ats_roles * 2.5 + (5.0 if ats_roles > 0 else 0.0))), 1)

    component_score = round(min(98.0, operational_fit + timing_urgency + purchasing_scale + hiring_intent), 1)
    propensity_score = round(float(np.clip((0.7 * component_score) + (0.3 * raw_score), 10.0, 98.0)), 1)

    # Assign Tier
    if propensity_score >= 80.0:
        tier = "Tier 1 - Prime Target (Urgent Buying Catalysts)"
    elif propensity_score >= 60.0:
        tier = "Tier 2 - Strategic Opportunity"
    else:
        tier = "Tier 3 - Nurture / Monitor"

    return {
        "propensity_score": propensity_score,
        "tier": tier,
        "is_disqualified": False,
        "disqualification_reason": None,
        "selected_wedge_idx": selected_wedge_idx,
        "score_breakdown": {
            "operational_fit": operational_fit,
            "timing_urgency": timing_urgency,
            "purchasing_scale": purchasing_scale,
            "hiring_intent": hiring_intent,
            "composite_score": propensity_score,
        },
        "dynamic_weights": dynamic_weights,
    }
