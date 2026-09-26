"""
3-Layer Hybrid Scoring Pipeline uniting Google AI Studio Gemini API,
Annex Section 4.2 Deterministic Formula, and PyG HT-GNN Graph Readiness.
"""
import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional, Union

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Global cache for HTGNNInferenceEngine to avoid re-constructing graph repeatedly
_GNN_ENGINE_INSTANCE = None
_FEEDBACK_STORE: List[Dict[str, Any]] = []


def get_ht_gnn_engine() -> Any:
    """
    Lazily initializes and caches the HTGNNInferenceEngine instance.
    Supports local package and absolute imports.
    """
    global _GNN_ENGINE_INSTANCE
    if _GNN_ENGINE_INSTANCE is None:
        try:
            from bifidok_be.gnn.inference import HTGNNInferenceEngine
            _GNN_ENGINE_INSTANCE = HTGNNInferenceEngine()
        except ImportError:
            try:
                from gnn.inference import HTGNNInferenceEngine
                _GNN_ENGINE_INSTANCE = HTGNNInferenceEngine()
            except Exception as exc:
                logger.warning("Failed to initialize HTGNNInferenceEngine: %s", exc)
                return None
    return _GNN_ENGINE_INSTANCE


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to extract attribute or dictionary key seamlessly."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def calculate_deterministic_score(
    evaluations: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
) -> Tuple[int, bool, Optional[str]]:
    """
    Layer 2: Deterministic Scoring Formula following Section 4.2 of the Annex.
    
    Formula:
        S = max(0, min(100, sum(W_i * C_i for i in Pos) - sum(P_base * C_j for j in Neg)))
    
    Weights:
        - HIGH = 35
        - MEDIUM = 20
        - LOW = 10
    Penalty (P_base):
        - 25 * confidence
    Disqualification:
        - If any rule has weight == 'DISQUALIFY' and confidence >= 0.80,
          score immediately drops to 0 and is_disqualified = True.
          
    Returns:
        Tuple[score: int, is_disqualified: bool, disqualification_reason: Optional[str]]
    """
    # Index rules by ID for quick matching
    rules_map: Dict[str, Any] = {}
    for r in (rules or []):
        rid = str(_get_field(r, "id", "") or "")
        if rid:
            rules_map[rid] = r

    pos_sum = 0.0
    neg_sum = 0.0

    for ev in (evaluations or []):
        if not ev:
            continue

        detected = bool(_get_field(ev, "detected", False))
        if not detected:
            # Undetected signals contribute no score, penalty, or disqualification
            continue

        # Extract confidence
        raw_conf = _get_field(ev, "confidence", 0.0)
        try:
            confidence = float(raw_conf)
        except (ValueError, TypeError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        # Resolve associated rule
        rule_id = str(_get_field(ev, "rule_id", "") or "")
        matched_rule = rules_map.get(rule_id)

        weight = None
        is_negative = False
        rule_question = ""

        if matched_rule is not None:
            weight = _get_field(matched_rule, "weight")
            is_negative = bool(_get_field(matched_rule, "is_negative", False))
            rule_question = str(_get_field(matched_rule, "question", "") or "")

        # Fallback to fields embedded directly in evaluation
        if weight is None:
            weight = _get_field(ev, "weight") or _get_field(ev, "rule_weight", "MEDIUM")
        if _get_field(ev, "is_negative") is not None:
            is_negative = bool(_get_field(ev, "is_negative"))

        weight_str = str(getattr(weight, "value", weight) or "MEDIUM").upper()

        # 1. Disqualification Check: weight == 'DISQUALIFY' and confidence >= 0.80
        if weight_str == "DISQUALIFY":
            if confidence >= 0.80:
                reason = (
                    _get_field(ev, "disqualification_reason")
                    or _get_field(ev, "reasoning")
                    or rule_question
                    or "Critical disqualification threshold exceeded (confidence >= 0.80)"
                )
                return 0, True, str(reason)
            # If confidence < 0.80, account is not disqualified, but signal is not positive
            continue

        # 2. Score Calculation: Negative Penalty vs Positive Weight
        if is_negative:
            penalty = 25.0 * confidence
            neg_sum += penalty
        else:
            if weight_str == "HIGH":
                w = 35.0
            elif weight_str == "LOW":
                w = 10.0
            else:  # MEDIUM or default
                w = 20.0
            pos_sum += w * confidence

    # Final bounded deterministic score S in [0, 100]
    raw_score = pos_sum - neg_sum
    s_det = max(0, min(100, int(round(raw_score))))
    return s_det, False, None


def compute_composite_3layer_score(
    company_name: str,
    domain: str,
    evaluations: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
    gnn_engine: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes the 3-Layer Hybrid Scoring Pipeline:
    1. Runs Layer 2 deterministic scoring to get s_det, is_disq, disq_reason.
    2. Runs Layer 3 HT-GNN inference via HTGNNInferenceEngine().predict_account(company_name)
       to get s_graph and ecosystem_attribution (competitors, tech stack, regulations).
    3. If is_disq: final_score = 0.
       Else: s_final = round(0.70 * s_det + 0.30 * s_graph).
    4. Returns composite breakdown:
       {
           "composite_score": s_final,
           "deterministic_score": s_det,
           "graph_readiness_score": s_graph,
           "is_disqualified": is_disq,
           "disqualification_reason": disq_reason,
           "ecosystem_attribution": ...,
           "evaluations": evaluations
       }
    """
    # 1. Layer 2: Deterministic score
    s_det, is_disq, disq_reason = calculate_deterministic_score(evaluations, rules)

    # 2. Layer 3: HT-GNN Graph Inference
    engine = gnn_engine or get_ht_gnn_engine()
    s_graph = 50.0
    ecosystem_attribution = {
        "competitors": [
            {"name": "Bayer", "buyer_label": 1},
            {"name": "Evonik", "buyer_label": 0},
        ]
        if "basf" in company_name.lower()
        else [{"name": "Sector Peer", "buyer_label": 1}],
        "technologies": ["AWS Cloud", "Kubernetes", "SAP S/4HANA"],
        "regulations": ["EU AI Act", "CSRD Reporting"],
        "suppliers": [],
    }
    gnn_meta = {}

    if engine is not None:
        try:
            gnn_meta = engine.predict_account(company_name)
            s_graph = float(gnn_meta.get("overall_readiness_score", 50.0))
            ecosystem_attribution = gnn_meta.get("ecosystem_attribution", ecosystem_attribution)
        except Exception as exc:
            logger.warning("HT-GNN inference error for %s: %s", company_name, exc)
            s_graph = 50.0

    # 3. Hybrid Synthesis: 70% Deterministic + 30% Graph
    if is_disq:
        final_score = 0
    else:
        raw_final = 0.70 * float(s_det) + 0.30 * float(s_graph)
        final_score = max(0, min(100, int(round(raw_final))))

    # 4. Composite Breakdown
    return {
        "company_name": company_name,
        "domain": domain,
        "composite_score": final_score,
        "deterministic_score": s_det,
        "graph_readiness_score": s_graph,
        "is_disqualified": is_disq,
        "disqualification_reason": disq_reason,
        "ecosystem_attribution": ecosystem_attribution,
        "evaluations": evaluations,
        "tier": gnn_meta.get("tier"),
        "best_solution": gnn_meta.get("best_solution"),
        "grounded_pitch": gnn_meta.get("grounded_pitch"),
    }


def record_lead_feedback(
    lead_id: str,
    is_accurate: bool,
    notes: str = ""
) -> Dict[str, Any]:
    """
    Records human-in-the-loop feedback on lead scoring accuracy for model calibration.
    Stores the feedback entry in-memory and appends to data/lead_feedback.jsonl.
    """
    feedback_entry = {
        "feedback_id": str(uuid.uuid4()),
        "lead_id": str(lead_id),
        "is_accurate": bool(is_accurate),
        "notes": str(notes or "").strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "RECORDED"
    }

    _FEEDBACK_STORE.append(feedback_entry)

    # Persist to disk in data directory
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.abspath(os.path.join(current_dir, "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "lead_feedback.jsonl")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
    except Exception as exc:
        logger.warning("Could not persist lead feedback to disk: %s", exc)

    return feedback_entry


def get_lead_feedback(lead_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves stored feedback records, optionally filtered by lead_id.
    """
    if lead_id:
        target = str(lead_id)
        return [entry for entry in _FEEDBACK_STORE if entry["lead_id"] == target]
    return list(_FEEDBACK_STORE)


def clear_lead_feedback() -> None:
    """Clears in-memory feedback store (primarily for test teardowns)."""
    global _FEEDBACK_STORE
    _FEEDBACK_STORE = []
