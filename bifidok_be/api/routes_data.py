"""
Data Engine and Machine Learning training routes.
Connects CLI Options 4 and 5 to the web dashboard.
"""
import os
import json
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from data.historical_harvester import (
        build_and_save_historical_market_dataset,
        HISTORICAL_DATASET_PATH,
    )
    from engine.local_ml.trainer import (
        train_and_save_models,
        WEIGHTS_DIR,
    )
    from engine.local_ml.inference import reload_local_models
except ImportError:
    from bifidok_be.data.historical_harvester import (
        build_and_save_historical_market_dataset,
        HISTORICAL_DATASET_PATH,
    )
    from bifidok_be.engine.local_ml.trainer import (
        train_and_save_models,
        WEIGHTS_DIR,
    )
    from bifidok_be.engine.local_ml.inference import reload_local_models

router = APIRouter(prefix="/api/data", tags=["data-engine"])

class HarvestRequest(BaseModel):
    days: int = Field(default=90, ge=7, le=730)

class TrainRequest(BaseModel):
    samples: int = Field(default=450, ge=50, le=5000)

@router.post("/harvest", response_model=Dict[str, Any])
def harvest_market_data(req: HarvestRequest):
    try:
        records = build_and_save_historical_market_dataset(days=req.days)
        total = len(records)
        disqualified = sum(1 for r in records if r.get("ground_truth_disqualified") == 1)
        solvent = total - disqualified
        
        wedges = {0: 0, 1: 0, 2: 0}
        for r in records:
            w = r.get("primary_wedge", 0)
            wedges[w] = wedges.get(w, 0) + 1
            
        return {
            "status": "DATASET_COMPILED",
            "days": req.days,
            "records_count": total,
            "solvent_count": solvent,
            "disqualified_count": disqualified,
            "wedge_distribution": {
                "agentic_automation": wedges.get(0, 0),
                "managed_soc": wedges.get(1, 0),
                "cloud_modernization": wedges.get(2, 0),
            },
            "dataset_path": HISTORICAL_DATASET_PATH,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/train", response_model=Dict[str, Any])
def train_models(req: TrainRequest):
    try:
        result = train_and_save_models(target_samples=req.samples)
        reload_local_models()
        
        meta = result.get("metadata", {})
        metrics = meta.get("metrics", {})
        importances = meta.get("feature_importances", {})
        
        sorted_imp = [
            {"feature": k, "weight": f"{v * 100:.1f}%"}
            for k, v in sorted(importances.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "status": "TRAINED_AND_SERIALIZED",
            "episodes": req.samples,
            "metrics": {
                "disqualification_accuracy": round(metrics.get("disqualification_accuracy", 1.0), 3),
                "propensity_regressor_mae": round(metrics.get("propensity_regressor_mae", 0.0), 2),
                "propensity_regressor_r2": round(metrics.get("propensity_regressor_r2", 0.0), 3),
                "wedge_classifier_macro_f1": round(metrics.get("wedge_classifier_macro_f1", 1.0), 3),
            },
            "feature_importances": sorted_imp,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/status", response_model=Dict[str, Any])
def get_data_engine_status():
    meta_path = os.path.join(WEIGHTS_DIR, "model_metadata.json")
    has_meta = os.path.exists(meta_path)
    has_data = os.path.exists(HISTORICAL_DATASET_PATH)
    
    meta = {}
    if has_meta:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            
    return {
        "dataset_ready": has_data,
        "dataset_path": HISTORICAL_DATASET_PATH,
        "models_trained": has_meta,
        "trained_at": meta.get("trained_at", None),
        "episodes_count": meta.get("dataset_episodes_count", 0),
        "metrics": meta.get("metrics", {}),
        "feature_importances": meta.get("feature_importances", {}),
    }
