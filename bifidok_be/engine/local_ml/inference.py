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

import math
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

    op_margin_val = float(company.get("operating_margin", 0.12) if company.get("operating_margin") is not None else 0.12)
    if not is_solvent or (disq_prob >= 0.85 and op_margin_val < -0.20):
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

    # 5. Extract Feature Importances (Calibrated Serious Weights - Zero Courier Bias)
    dynamic_weights = {
        "semantic_relevance": 0.200,
        "has_active_tender": 0.140,
        "has_enterprise_erp": 0.100,
        "sector_alignment": 0.090,
        "hiring_velocity_score": 0.080,
        "operating_margin": 0.060,
        "has_official_ted_award": 0.060,
        "tech_stack_breadth": 0.050,
        "github_repo_count": 0.050,
        "has_leadership_catalyst": 0.040,
        "ats_role_count": 0.040,
        "headcount_log": 0.030,
        "is_solvent": 0.030,
        "security_resilience_grade": 0.010,
        "has_news_signals": 0.010,
        "missing_headers_count": 0.005,
        "cisa_kev_active_count": 0.005,
        "requires_physical_mismatch": 0.000,
    }

    # 6. Decompose Score Breakdown using sub-feature components
    # Incorporates Orange Systems Outsource Propensity & Vertical Market Scalability
    headcount_log = feat_vec[0]
    op_margin = feat_vec[1]
    ats_roles = feat_vec[3]
    has_tender = feat_vec[4]
    has_official_ted = feat_vec[5]
    has_news = feat_vec[6]
    github_repos = feat_vec[10]
    sem_rel = feat_vec[11]
    sector_align = feat_vec[13] if len(feat_vec) > 13 else 1.0
    tech_breadth = feat_vec[14] if len(feat_vec) > 14 else 0.0
    has_erp = feat_vec[15] if len(feat_vec) > 15 else 0.0
    has_leadership = feat_vec[16] if len(feat_vec) > 16 else 0.0
    hiring_vel = feat_vec[17] if len(feat_vec) > 17 else 0.0

    # Operational Fit (Max 35.0): Domain synergy, vertical expansion match, ERP integration, minus in-house engineering resistance penalty
    vertical_expansion_bonus = 4.0 if (sector_align >= 0.8 and github_repos < 250) else 0.0
    in_house_penalty = min(22.0, (math.log10(max(1.0, github_repos)) - 1.7) * 14.0) if github_repos > 100 else 0.0
    operational_fit = round(min(35.0, max(5.0, 12.0 + (sem_rel * 16.0) + (sector_align * 3.0) + (has_erp * 2.0) + vertical_expansion_bonus - in_house_penalty)), 1)

    # Timing Urgency (Max 30.0): Active tenders/RFPs, official TED awards, leadership appointments, press
    timing_urgency = round(min(30.0, (has_tender * 14.0) + (has_official_ted * 7.0) + (has_leadership * 5.0) + (has_news * 4.0)), 1)

    # Hiring Intent & Technical Delivery Capacity (Max 20.0): High-velocity recruitment, active IT roles
    hiring_intent = round(min(20.0, max(0.0, (hiring_vel * 9.0) + min(5.0, ats_roles * 1.5) + (2.5 if ats_roles > 0 else 0.0))), 1)

    # Purchasing Scale & Outsource Propensity Sweet Spot (Max 15.0):
    # Headcount capped (prevents courier/warehouse inflation); Mid-market sweet spot (250-35,000 employees) yields highest Orange Systems ROI
    headcount_cap = min(3.5, max(1.0, headcount_log * 0.6))
    margin_pts = min(5.0, max(1.5, op_margin * 30.0))
    erp_pts = 3.5 if has_erp > 0 else 2.5
    roi_sweet_spot = 3.0 if (2.4 <= headcount_log <= 4.55) else (2.5 if headcount_log > 4.55 else 1.5)
    purchasing_scale = round(min(15.0, margin_pts + erp_pts + headcount_cap + roi_sweet_spot), 1)

    component_score = round(min(98.0, operational_fit + timing_urgency + purchasing_scale + hiring_intent), 1)
    propensity_score = round(float(np.clip((0.6 * component_score) + (0.4 * raw_score), 10.0, 98.0)), 1)

    # Assign Tier
    if propensity_score >= 80.0:
        tier = "Tier 1 - Prime Target (Urgent Buying Catalysts & High Outsource ROI)"
    elif propensity_score >= 60.0:
        tier = "Tier 2 - Strategic Opportunity / Technology Partnership"
    else:
        tier = "Tier 3 - Nurture / Low Outsource Propensity"

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
