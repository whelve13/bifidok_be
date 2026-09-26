"""
Comprehensive Unit & Integration Test Suite for the 3-Layer Hybrid Scoring Pipeline.
Tests:
1. Gemini Signal Extractor & Anti-Hallucination Verbatim Guardrail
2. Annex Section 4.2 Deterministic Scoring Formula & Disqualification Checks
3. HT-GNN Graph Readiness Integration & 70/30 Composite Scoring
4. Sales Feedback Recording for Model Calibration
"""
import os
import sys
import json
import pytest

# Ensure bifidok_be package is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from engine.gemini_extractor import (
    verify_verbatim_quote,
    extract_signal_evidence,
    get_genai_client,
    DEFAULT_MODEL,
)
from engine.scoring_service import (
    calculate_deterministic_score,
    compute_composite_3layer_score,
    record_lead_feedback,
    get_lead_feedback,
    clear_lead_feedback,
)


# ==============================================================================
# LAYER 1: GEMINI EXTRACTOR & ANTI-HALLUCINATION GUARDRAIL TESTS
# ==============================================================================

def test_verify_verbatim_quote():
    passage = "DHL Group announced Strategy 2030 deploying agentic AI squads to automate logistics."
    
    # 1. Exact verbatim match
    assert verify_verbatim_quote("Strategy 2030 deploying agentic AI squads", passage) is True
    
    # 2. Match with surrounding quotation marks
    assert verify_verbatim_quote('"Strategy 2030 deploying agentic AI squads"', passage) is True
    
    # 3. Match with whitespace variations
    assert verify_verbatim_quote("Strategy 2030\n deploying agentic AI  squads", passage) is True
    
    # 4. Hallucinated or non-verbatim quote
    assert verify_verbatim_quote("DHL Group announced plans to buy 500 commercial e-vans", passage) is False
    assert verify_verbatim_quote("", passage) is False
    assert verify_verbatim_quote(None, passage) is False
    assert verify_verbatim_quote("Strategy 2030", None) is False


def test_gemini_extractor_clean_heuristic_fallback():
    passage = (
        "Lufthansa Group announced a major restructuring initiative to cut operational costs "
        "and reduce headcount by 4,000 employees across back-office operations."
    )
    question = "Is the company implementing operational cost cuts and headcount reduction?"
    guidance = "Look for announcements regarding layoffs, restructuring, or workforce reduction."

    # Force client=None to test the heuristic fallback
    result = extract_signal_evidence(raw_passage=passage, question=question, guidance=guidance, client=None)

    assert result["detected"] is True
    assert result["confidence"] > 0.5
    assert len(result["evidence_quote"]) > 0
    # Must be verified verbatim in passage
    assert verify_verbatim_quote(result["evidence_quote"], passage) is True
    assert "reasoning" in result


def test_gemini_extractor_negative_heuristic_fallback():
    passage = "Knorr-Bremse manufactures brake systems for rail and commercial vehicles."
    question = "Is the company facing immediate insolvency or bankruptcy proceedings?"
    guidance = "Check for Chapter 11, insolvency filings, or debt defaults."

    result = extract_signal_evidence(raw_passage=passage, question=question, guidance=guidance, client=None)
    assert result["detected"] is False
    assert result["confidence"] == 0.0
    assert result["evidence_quote"] == ""


def test_gemini_extractor_anti_hallucination_rejection():
    """
    Verifies that if an LLM returns a detected signal but hallucinates the evidence quote,
    the extraction is strictly rejected.
    """
    class MockHallucinatingModels:
        def generate_content(self, model, contents, config):
            class Response:
                text = json.dumps({
                    "detected": True,
                    "confidence": 0.95,
                    "evidence_quote": "We will spend 50 billion euros on AI by tomorrow morning.",
                    "reasoning": "Executive stated massive spending."
                })
            return Response()

    class MockHallucinatingClient:
        models = MockHallucinatingModels()

    passage = "Siemens AG reported third-quarter revenue of 18.9 billion euros with solid factory automation."
    question = "Is Siemens spending 50 billion euros on AI?"

    result = extract_signal_evidence(
        raw_passage=passage,
        question=question,
        client=MockHallucinatingClient()
    )

    assert result["detected"] is False
    assert result["confidence"] == 0.0
    assert result["evidence_quote"] == ""
    assert "REJECTED" in result["reasoning"]
    assert "Quote not verbatim" in result.get("rejection_reason", "")


def test_gemini_extractor_valid_client_response():
    """
    Verifies that when Gemini returns a valid, verbatim quote, it is accepted.
    """
    class MockAccurateModels:
        def generate_content(self, model, contents, config):
            class Response:
                text = json.dumps({
                    "detected": True,
                    "confidence": 0.88,
                    "evidence_quote": "Siemens AG reported third-quarter revenue of 18.9 billion euros",
                    "reasoning": "Revenue confirmed from official report."
                })
            return Response()

    class MockAccurateClient:
        models = MockAccurateModels()

    passage = "Siemens AG reported third-quarter revenue of 18.9 billion euros with solid factory automation."
    question = "Did Siemens report revenue?"

    result = extract_signal_evidence(
        raw_passage=passage,
        question=question,
        client=MockAccurateClient()
    )

    assert result["detected"] is True
    assert result["confidence"] == 0.88
    assert result["evidence_quote"] == "Siemens AG reported third-quarter revenue of 18.9 billion euros"
    assert verify_verbatim_quote(result["evidence_quote"], passage) is True


# ==============================================================================
# LAYER 2: DETERMINISTIC SCORING FORMULA (ANNEX SECTION 4.2) TESTS
# ==============================================================================

def test_calculate_deterministic_score_positive_weights():
    """
    Annex 4.2 Formula:
    Weights: HIGH=35, MEDIUM=20, LOW=10.
    Score = sum(W_i * C_i) bounded in [0, 100].
    """
    evaluations = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0}, # HIGH: 35 * 1.0 = 35
        {"rule_id": "r2", "detected": True, "confidence": 0.8}, # MEDIUM: 20 * 0.8 = 16
        {"rule_id": "r3", "detected": True, "confidence": 0.5}, # LOW: 10 * 0.5 = 5
        {"rule_id": "r4", "detected": False, "confidence": 1.0}, # Not detected -> 0
    ]
    rules = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r2", "weight": "MEDIUM", "is_negative": False},
        {"id": "r3", "weight": "LOW", "is_negative": False},
        {"id": "r4", "weight": "HIGH", "is_negative": False},
    ]

    # Expected: 35 + 16 + 5 = 56
    score, is_disq, disq_reason = calculate_deterministic_score(evaluations, rules)
    assert score == 56
    assert is_disq is False
    assert disq_reason is None


def test_calculate_deterministic_score_negative_penalty():
    """
    Annex 4.2: Negative penalty = 25 * confidence.
    Positive HIGH (35 * 1.0 = 35) minus Negative (25 * 0.8 = 20) = 15.
    """
    evaluations = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0},
        {"rule_id": "r_neg", "detected": True, "confidence": 0.8},
    ]
    rules = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r_neg", "weight": "MEDIUM", "is_negative": True},
    ]

    score, is_disq, disq_reason = calculate_deterministic_score(evaluations, rules)
    assert score == 15
    assert is_disq is False


def test_calculate_deterministic_score_disqualification_threshold():
    """
    Annex 4.2: If any rule labeled DISQUALIFY is confirmed with C >= 0.80,
    the account score immediately drops to 0 and is_disqualified is True.
    """
    # Case A: C = 0.85 (>= 0.80 -> Disqualified)
    evaluations_disq = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0}, # HIGH positive: 35
        {
            "rule_id": "r_disq",
            "detected": True,
            "confidence": 0.85,
            "reasoning": "Company filed for preliminary insolvency."
        },
    ]
    rules_disq = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r_disq", "weight": "DISQUALIFY", "is_negative": True},
    ]

    score, is_disq, disq_reason = calculate_deterministic_score(evaluations_disq, rules_disq)
    assert score == 0
    assert is_disq is True
    assert "insolvency" in disq_reason.lower()

    # Case B: C = 0.75 (< 0.80 -> NOT Disqualified)
    evaluations_not_disq = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0},
        {"rule_id": "r_disq", "detected": True, "confidence": 0.75, "reasoning": "Rumor of distress."},
    ]
    score, is_disq, disq_reason = calculate_deterministic_score(evaluations_not_disq, rules_disq)
    assert score == 35
    assert is_disq is False
    assert disq_reason is None


def test_calculate_deterministic_score_bounding():
    """Score must be bounded strictly in [0, 100]."""
    # Over 100
    evals_high = [
        {"detected": True, "confidence": 1.0, "weight": "HIGH"},
        {"detected": True, "confidence": 1.0, "weight": "HIGH"},
        {"detected": True, "confidence": 1.0, "weight": "HIGH"},
        {"detected": True, "confidence": 1.0, "weight": "HIGH"},
    ]
    score, _, _ = calculate_deterministic_score(evals_high, [])
    assert score == 100

    # Below 0
    evals_low = [
        {"detected": True, "confidence": 1.0, "weight": "LOW"}, # +10
        {"detected": True, "confidence": 1.0, "is_negative": True}, # -25
    ]
    score, _, _ = calculate_deterministic_score(evals_low, [])
    assert score == 0


# ==============================================================================
# LAYER 3 & COMPOSITE 3-LAYER SCORING TESTS
# ==============================================================================

def test_compute_composite_3layer_score_synthesis():
    """
    Validates:
    1. s_det calculation
    2. s_graph calculation via HT-GNN
    3. Composite formula: round(0.70 * s_det + 0.30 * s_graph)
    4. Inclusion of ecosystem_attribution
    """
    class MockHTGNNInferenceEngine:
        def predict_account(self, company_name: str):
            return {
                "company_name": company_name,
                "overall_readiness_score": 80.0,
                "tier": "Tier 1 - Hot",
                "best_solution": "Agentic Process Automation",
                "ecosystem_attribution": {
                    "competitors": [{"name": "Kuehne+Nagel", "buyer_label": True}],
                    "technologies": ["UiPath", "SAP S/4HANA"],
                    "regulations": ["NIS2 Directive"],
                    "suppliers": []
                },
                "grounded_pitch": "Sample pitch"
            }

    evaluations = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0}, # HIGH = 35
        {"rule_id": "r2", "detected": True, "confidence": 1.0}, # MEDIUM = 20
    ]
    rules = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r2", "weight": "MEDIUM", "is_negative": False},
    ]

    # s_det = 35 + 20 = 55
    # s_graph = 80.0
    # s_final = round(0.70 * 55 + 0.30 * 80.0) = round(38.5 + 24.0) = round(62.5) = 62 or 63
    mock_gnn = MockHTGNNInferenceEngine()
    result = compute_composite_3layer_score(
        company_name="DHL Group",
        domain="dhl.com",
        evaluations=evaluations,
        rules=rules,
        gnn_engine=mock_gnn
    )

    assert result["deterministic_score"] == 55
    assert result["graph_readiness_score"] == 80.0
    assert result["composite_score"] in (62, 63)
    assert result["is_disqualified"] is False
    assert result["disqualification_reason"] is None
    assert "competitors" in result["ecosystem_attribution"]
    assert "technologies" in result["ecosystem_attribution"]
    assert "regulations" in result["ecosystem_attribution"]
    assert result["evaluations"] == evaluations


def test_compute_composite_3layer_score_disqualification():
    """
    If account is disqualified in Layer 2, composite_score MUST be 0
    even if graph readiness score is high.
    """
    class MockHTGNNInferenceEngine:
        def predict_account(self, company_name: str):
            return {
                "overall_readiness_score": 95.0,
                "ecosystem_attribution": {"competitors": [], "technologies": []}
            }

    evaluations = [
        {"rule_id": "r1", "detected": True, "confidence": 1.0},
        {
            "rule_id": "r_disq",
            "detected": True,
            "confidence": 0.90,
            "reasoning": "Severe insolvency liquidation proceeding opened."
        }
    ]
    rules = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r_disq", "weight": "DISQUALIFY", "is_negative": True}
    ]

    result = compute_composite_3layer_score(
        company_name="Insolvent Co",
        domain="insolvent.com",
        evaluations=evaluations,
        rules=rules,
        gnn_engine=MockHTGNNInferenceEngine()
    )

    assert result["is_disqualified"] is True
    assert result["composite_score"] == 0
    assert "insolvency" in result["disqualification_reason"].lower()


# ==============================================================================
# SALES FEEDBACK RECORDING TESTS
# ==============================================================================

def test_record_lead_feedback():
    clear_lead_feedback()

    rec1 = record_lead_feedback(
        lead_id="lead-123",
        is_accurate=True,
        notes="Prospect confirmed they have active budget for NIS2 compliance."
    )
    assert rec1["lead_id"] == "lead-123"
    assert rec1["is_accurate"] is True
    assert rec1["status"] == "RECORDED"
    assert "feedback_id" in rec1
    assert "timestamp" in rec1

    rec2 = record_lead_feedback(
        lead_id="lead-456",
        is_accurate=False,
        notes="Company already contracted an automation vendor last quarter."
    )
    assert rec2["is_accurate"] is False

    all_feedback = get_lead_feedback()
    assert len(all_feedback) == 2

    lead_123_feedback = get_lead_feedback("lead-123")
    assert len(lead_123_feedback) == 1
    assert lead_123_feedback[0]["notes"] == rec1["notes"]


# ==============================================================================
# END-TO-END 3-LAYER PIPELINE INTEGRATION TESTS
# ==============================================================================

def test_compute_composite_3layer_score_live_ht_gnn():
    """
    Tests live PyTorch Geometric HT-GNN inference integration.
    """
    evaluations = [
        {"rule_id": "r1", "detected": True, "confidence": 0.90},
        {"rule_id": "r2", "detected": True, "confidence": 0.70},
    ]
    rules = [
        {"id": "r1", "weight": "HIGH", "is_negative": False},
        {"id": "r2", "weight": "MEDIUM", "is_negative": False},
    ]

    result = compute_composite_3layer_score(
        company_name="DHL Group",
        domain="dhl.com",
        evaluations=evaluations,
        rules=rules,
    )

    assert result["company_name"] == "DHL Group"
    assert result["domain"] == "dhl.com"
    assert 0 <= result["deterministic_score"] <= 100
    assert 0 <= result["graph_readiness_score"] <= 100
    assert 0 <= result["composite_score"] <= 100
    assert result["is_disqualified"] is False
    assert "competitors" in result["ecosystem_attribution"]
    assert "technologies" in result["ecosystem_attribution"]
    assert "regulations" in result["ecosystem_attribution"]


def test_end_to_end_3layer_pipeline():
    """
    Unites all 3 layers:
    Layer 1: Gemini extraction with anti-hallucination verification
    Layer 2: Annex 4.2 deterministic score calculation
    Layer 3: HT-GNN graph readiness & ecosystem attribution
    """
    passage = (
        "BASF is actively accelerating its cloud migration and legacy modernization "
        "across European facilities, deploying AWS Cloud and Kubernetes clusters."
    )
    question = "Is the company executing cloud migration and modernizing legacy applications?"
    guidance = "Look for AWS, Azure, Kubernetes, cloud transformation."

    # Layer 1: Extract signal evidence
    l1_result = extract_signal_evidence(passage, question, guidance, client=None)
    assert l1_result["detected"] is True
    assert verify_verbatim_quote(l1_result["evidence_quote"], passage) is True

    # Layer 2 & 3: Score composite lead
    evaluations = [
        {
            "rule_id": "r_cloud",
            "detected": l1_result["detected"],
            "confidence": l1_result["confidence"],
            "evidence_quote": l1_result["evidence_quote"],
            "reasoning": l1_result["reasoning"],
        }
    ]
    rules = [
        {
            "id": "r_cloud",
            "question": question,
            "weight": "HIGH",
            "is_negative": False,
        }
    ]

    composite = compute_composite_3layer_score(
        company_name="BASF",
        domain="basf.com",
        evaluations=evaluations,
        rules=rules,
    )

    assert composite["composite_score"] > 0
    assert composite["deterministic_score"] > 0
    assert composite["graph_readiness_score"] > 0
    assert composite["is_disqualified"] is False
    assert len(composite["ecosystem_attribution"].get("technologies", [])) > 0

    # Calibration feedback
    fb = record_lead_feedback(lead_id="basf-lead-001", is_accurate=True, notes="Confirmed high fit")
    assert fb["lead_id"] == "basf-lead-001"
