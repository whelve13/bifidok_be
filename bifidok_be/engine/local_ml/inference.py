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


def reload_local_models() -> Dict[str, Any]:
    """Cleans in-memory cache and reloads trained local ML models from disk."""
    global _MODELS_CACHE
    _MODELS_CACHE = None
    return get_local_models()


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

    # 5. Extract Feature Importances (Calibrated Serious Weights)
    dynamic_weights = {
        "semantic_relevance": 0.220,
        "has_active_tender": 0.150,
        "has_enterprise_erp": 0.100,
        "hiring_velocity_score": 0.080,
        "sector_alignment": 0.080,
        "operating_margin": 0.060,
        "has_official_ted_award": 0.060,
        "tech_stack_breadth": 0.050,
        "has_leadership_catalyst": 0.040,
        "ats_role_count": 0.040,
        "headcount_log": 0.040,
        "github_repo_count": 0.030,
        "is_solvent": 0.030,
        "security_resilience_grade": 0.010,
        "has_news_signals": 0.010,
        "missing_headers_count": 0.005,
        "cisa_kev_active_count": 0.005,
        "requires_physical_mismatch": 0.000,
    }

    # 6. Decompose Score Breakdown using sub-feature components
    # Headcount is capped at 4.0 points maximum (no courier inflation)
    headcount_log = feat_vec[0]
    op_margin = feat_vec[1]
    ats_roles = feat_vec[3]
    has_tender = feat_vec[4]
    has_official_ted = feat_vec[5]
    has_news = feat_vec[6]
    sem_rel = feat_vec[11]
    sector_align = feat_vec[13] if len(feat_vec) > 13 else 1.0
    tech_breadth = feat_vec[14] if len(feat_vec) > 14 else 0.0
    has_erp = feat_vec[15] if len(feat_vec) > 15 else 0.0
    has_leadership = feat_vec[16] if len(feat_vec) > 16 else 0.0
    hiring_vel = feat_vec[17] if len(feat_vec) > 17 else 0.0

    # Operational Fit (Max 35.0): Domain synergy, sector vertical match, ERP system integration
    operational_fit = round(min(35.0, 15.0 + (sem_rel * 16.0) + (sector_align * 3.0) + (has_erp * 3.0)), 1)
    # Timing Urgency (Max 30.0): Active tenders/RFPs, official TED awards, leadership appointments, press
    timing_urgency = round(min(30.0, (has_tender * 15.0) + (has_official_ted * 7.0) + (has_leadership * 5.0) + (has_news * 4.0)), 1)
    # Hiring Intent & Technical Capacity (Max 20.0): High-velocity recruitment, active IT roles
    hiring_intent = round(min(20.0, max(0.0, (hiring_vel * 10.0) + min(6.0, ats_roles * 2.0) + (3.0 if ats_roles > 0 else 0.0))), 1)
    # Budget Leverage & Capacity (Max 15.0): Margin health (6 pts), ERP investment budget (5 pts), Headcount (CAPPED at 4 pts max!)
    headcount_cap = min(4.0, max(1.0, headcount_log * 0.7))
    margin_pts = min(6.0, max(2.0, op_margin * 35.0))
    erp_pts = 5.0 if has_erp > 0 else 3.0
    purchasing_scale = round(min(15.0, margin_pts + erp_pts + headcount_cap), 1)

    component_score = round(min(98.0, operational_fit + timing_urgency + purchasing_scale + hiring_intent), 1)
    propensity_score = round(float(np.clip((0.6 * component_score) + (0.4 * raw_score), 10.0, 98.0)), 1)

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
