import os
import sys
import pytest

# Ensure bifidok_be root package is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from fastapi.testclient import TestClient
from api.app import app
from engine.commercial_verifier import verify_commercial_fit, CommercialVerificationResult


def test_domain_mismatch_detection_traditional_dairy():
    """Confirms non-digital primary commodity business is disqualified from enterprise AI/Cyber offering."""
    verdict = verify_commercial_fit(
        offering_title="Agentic Workflow Automation & SOC Defense",
        offering_description="Enterprise LLM process automation and Managed SOC security operations.",
        company_name="Bavarian Alps Dairy & Livestock Cooperative",
        company_sector="Dairy & Livestock Farming",
        company_description="Regional collective producing raw organic milk and butter.",
        evidence_snippets=["Bavarian Alps Dairy reports stable milk yield for spring season."],
    )

    assert verdict.is_approved is False
    assert verdict.domain_mismatch is True
    assert verdict.relevance_score <= 0.3
    assert verdict.rejection_reason is not None


def test_domain_mismatch_physical_cargo_bikes_to_fintech():
    """Confirms pure digital financial entity is disqualified from urban cargo bike offering."""
    verdict = verify_commercial_fit(
        offering_title="Urban Commercial Cargo E-Bikes",
        offering_description="Heavy-duty electric cargo bikes for last-mile inner-city courier operations.",
        company_name="Apex Hedge Fund Quantitative Trading",
        company_sector="Financial Services & Quantitative Trading",
        company_description="Cloud-native algorithmic hedge fund trading derivatives.",
        evidence_snippets=["Apex Hedge Fund expands latency co-location in Frankfurt datacenter."],
    )

    assert verdict.is_approved is False
    assert verdict.domain_mismatch is True
    assert verdict.rejection_reason is not None


def test_positive_commercial_alignment_and_executive_angle():
    """Confirms legitimate enterprise IT prospect receives approved verdict and high-conviction executive angle."""
    verdict = verify_commercial_fit(
        offering_title="Managed SOC Defense & NIS2 Compliance",
        offering_description="24/7 Security Operations Center monitoring and NIS2 compliance auditing.",
        company_name="Deutsche Telekom AG",
        company_sector="Telecommunications & Network Operations",
        company_description="Global telecommunications provider managing critical European network infrastructure.",
        evidence_snippets=["Deutsche Telekom announces infrastructure expansion and cyber resilience audit."],
    )

    assert verdict.is_approved is True
    assert verdict.domain_mismatch is False
    assert verdict.relevance_score >= 0.8
    assert "Deutsche Telekom" in verdict.executive_angle
    assert "NIS2" in verdict.executive_angle or "compliance" in verdict.executive_angle.lower()


def test_simulated_outreach_dispatch_safe_sandbox():
    """Confirms outreach approval sets simulated dispatch headers without external transmission."""
    client = TestClient(app)

    # 1. Stage a draft
    stage_res = client.post(
        "/api/outreach/stage",
        json={
            "recipient_email": "executive@siemens.com",
            "subject": "Grounded Value Proposition: PipStream",
            "email_body": "Demonstrating verified buying signals in sandbox mode.",
            "dry_run": True,
        },
    )
    assert stage_res.status_code == 200
    staged = stage_res.json()
    draft_id = staged["draft_id"]
    assert staged["status"] == "AWAITING_HUMAN_APPROVAL"

    # 2. Approve draft in simulated mode
    approve_res = client.post(f"/api/outreach/{draft_id}/approve")
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["status"] == "DISPATCHED"
    assert "Sandbox Simulation Mode" in data["message"]
    draft = data["draft"]
    assert draft["simulated_dispatch"] is True
    assert draft["message_id"].startswith("sim-")
    assert draft["delivery_transport"] == "SIMULATED_SECURE_SANDBOX"


def test_mcp_api_keys_endpoint_and_prefix():
    """Confirms provisioning and listing of pip_sk_ prefixed keys."""
    client = TestClient(app)

    # Provision key
    prov_res = client.post(
        "/api/auth/keys",
        json={"tenant_name": "PipStreamEnterpriseAgent", "key_prefix": "pip_sk"},
    )
    assert prov_res.status_code == 200
    prov_data = prov_res.json()
    assert prov_data["raw_key"].startswith("pip_sk_")
    assert len(prov_data["raw_key"]) > 20

    # List keys
    list_res = client.get("/api/auth/keys")
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)
