"""
Data Harvesting and Local ML Model Training API routes.
Conforms to CLI Options 4 & 5 and Section 2 of Enterprise Sales Intelligence Platform.
"""
import json
import logging
import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])


class HarvestDataRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=1000, description="Data amount in days to harvest")


class TrainModelsRequest(BaseModel):
    samples: int = Field(default=450, ge=50, le=2000, description="Target training episodes count")


@router.post("/harvest", response_model=Dict[str, Any])
@router.post("/fetch", response_model=Dict[str, Any], include_in_schema=False)
def harvest_market_data(request: HarvestDataRequest):
    """
    Option 4: Harvests and compiles historical enterprise market dataset across specified days.
    """
    try:
        from data.historical_harvester import (
            build_and_save_historical_market_dataset,
            HISTORICAL_DATASET_PATH,
        )
    except ImportError:
        from bifidok_be.data.historical_harvester import (
            build_and_save_historical_market_dataset,
            HISTORICAL_DATASET_PATH,
        )

    try:
        records = build_and_save_historical_market_dataset(days=request.days)
    except Exception as exc:
        logger.error("Data harvest failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Historical data harvesting failed: {str(exc)}",
        )

    total = len(records)
    insolvent = sum(1 for r in records if r.get("ground_truth_disqualified") == 1)
    solvent = total - insolvent

    wedge_counts = {0: 0, 1: 0, 2: 0}
    for r in records:
        w = r.get("primary_wedge", 0)
        wedge_counts[w] = wedge_counts.get(w, 0) + 1

    return {
        "status": "COMPLETED",
        "days": request.days,
        "total_records": total,
        "solvent_count": solvent,
        "insolvent_count": insolvent,
        "solvent_percentage": round((solvent / total * 100), 1) if total > 0 else 0,
        "wedge_distribution": {
            "Agentic Automation": wedge_counts.get(0, 0),
            "Managed SOC": wedge_counts.get(1, 0),
            "Cloud Modernization": wedge_counts.get(2, 0),
        },
        "dataset_path": HISTORICAL_DATASET_PATH,
    }


@router.post("/train", response_model=Dict[str, Any])
def train_local_models_endpoint(request: TrainModelsRequest):
    """
    Option 5: Trains and serializes local ML models (Hard-Gate Disqualification Classifier,
    LightGBM Propensity Regressor, and RandomForest Commercial Wedge Classifier).
    """
    try:
        from engine.local_ml.trainer import train_and_save_models, WEIGHTS_DIR
    except ImportError:
        from bifidok_be.engine.local_ml.trainer import train_and_save_models, WEIGHTS_DIR

    try:
        result = train_and_save_models(target_samples=request.samples)
    except Exception as exc:
        logger.error("Model training failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Local ML model training failed: {str(exc)}",
        )

    # Reload model weights in memory
    try:
        from engine.local_ml.inference import reload_local_models
        reload_local_models()
    except Exception as reload_err:
        logger.warning("Could not hot-reload models: %s", reload_err)

    meta = result.get("metadata", {})
    metrics = meta.get("metrics", {})
    importances = meta.get("feature_importances", {})

    descriptions = {
        "semantic_relevance": "Core service / domain capability alignment",
        "has_active_tender": "Active RFP / public procurement demand",
        "has_enterprise_erp": "Core ERP footprint (SAP, Oracle, Salesforce)",
        "hiring_velocity_score": "High-velocity technical & specialist recruitment",
        "sector_alignment": "Target vertical industry fit",
        "operating_margin": "Financial health & investment budget capacity",
        "has_official_ted_award": "Official European contract award history",
        "tech_stack_breadth": "Enterprise tech stack maturity & cloud breadth",
        "has_leadership_catalyst": "Executive leadership catalyst (new CIO/CISO/CTO)",
        "ats_role_count": "Active hiring in target engineering roles",
        "headcount_log": "Baseline organizational scale (capped capacity check)",
        "github_repo_count": "Internal software engineering capability",
        "is_solvent": "Hard solvency / liquidation gate",
        "security_resilience_grade": "Perimeter security posture (A to F)",
        "has_news_signals": "Press coverage on transformation / restructuring",
        "missing_headers_count": "Security vulnerability configuration gap",
        "cisa_kev_active_count": "Active weaponized CISA vulnerabilities",
        "requires_physical_mismatch": "Physical footprint alignment",
    }

    feature_ranking = [
        {
            "rank": i,
            "feature": k,
            "weight": round(v * 100, 2),
            "description": descriptions.get(k, "Engine feature signal"),
        }
        for i, (k, v) in enumerate(sorted(importances.items(), key=lambda x: x[1], reverse=True), 1)
    ]

    return {
        "status": "COMPLETED",
        "target_samples": request.samples,
        "metrics": {
            "disqualification_accuracy": round(metrics.get("disqualification_accuracy", 1.0) * 100, 2),
            "propensity_regressor_mae": round(metrics.get("propensity_regressor_mae", 0.0), 4),
            "propensity_regressor_r2": round(metrics.get("propensity_regressor_r2", 0.0), 4),
            "wedge_classifier_macro_f1": round(metrics.get("wedge_classifier_macro_f1", 1.0), 4),
        },
        "feature_ranking": feature_ranking,
        "weights_dir": WEIGHTS_DIR,
    }


@router.get("/status", response_model=Dict[str, Any])
def get_data_engine_status():
    """
    Returns the current status of the historical market dataset and trained local ML models.
    """
    try:
        from data.historical_harvester import HISTORICAL_DATASET_PATH, load_historical_market_dataset
        from engine.local_ml.trainer import WEIGHTS_DIR
    except ImportError:
        from bifidok_be.data.historical_harvester import HISTORICAL_DATASET_PATH, load_historical_market_dataset
        from bifidok_be.engine.local_ml.trainer import WEIGHTS_DIR

    dataset_exists = os.path.exists(HISTORICAL_DATASET_PATH)
    record_count = 0
    if dataset_exists:
        try:
            records = load_historical_market_dataset()
            record_count = len(records)
        except Exception:
            pass

    meta_path = os.path.join(WEIGHTS_DIR, "model_metadata.json")
    models_trained = os.path.exists(meta_path)
    metadata = {}
    if models_trained:
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            pass

    return {
        "dataset": {
            "exists": dataset_exists,
            "path": HISTORICAL_DATASET_PATH,
            "records": record_count,
        },
        "models": {
            "trained": models_trained,
            "weights_dir": WEIGHTS_DIR,
            "trained_at": metadata.get("trained_at"),
            "metrics": metadata.get("metrics", {}),
            "episodes_count": metadata.get("dataset_episodes_count", 0),
        },
    }
