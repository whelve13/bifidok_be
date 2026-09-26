"""
Unit and integration tests for FastAPI application core endpoints.
Tests health, auth, leads, evidence, HitL feedback, outreach queue & approval, and CORS.
"""
import hashlib
import json
import os
import sys
import unittest
from unittest.mock import patch

# Ensure bifidok_be root package is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.app import app
from api.auth import generate_api_key, get_authenticated_tenant
from db.schema import Base, MCPApiKey
from db.seed import seed_database
from db.session import get_db
from services.leads_service import (
    OUTREACH_QUEUE,
    queue_sales_outreach,
    clear_lead_feedback,
    get_lead_feedback,
)


class TestApiEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create an in-memory SQLite database with StaticPool for test execution
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.engine
        )

    def setUp(self):
        # Override get_db dependency to use the isolated in-memory test database
        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.session = self.TestingSessionLocal()
        seed_database(self.session)

        # Clear state
        clear_lead_feedback()
        OUTREACH_QUEUE.clear()

    def tearDown(self):
        self.session.close()
        app.dependency_overrides.clear()
        clear_lead_feedback()
        OUTREACH_QUEUE.clear()

    # =========================================================================
    # 1. HEALTH ENDPOINT TESTS
    # =========================================================================
    def test_health_endpoint(self):
        """GET /health should return 200, status UP, and an ISO timestamp."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "UP")
        self.assertIn("timestamp", data)
        self.assertTrue(len(data["timestamp"]) > 10)

    def test_healthz_endpoint(self):
        """GET /healthz should return 200 (or 503 if down) with preflight diagnostics component statuses."""
        response = self.client.get("/healthz")
        self.assertIn(response.status_code, (200, 503))
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("components", data)
        self.assertIn("database", data["components"])
        self.assertIn("redis", data["components"])
        self.assertIn("gemini", data["components"])

    # =========================================================================
    # 2. AUTHENTICATION & API KEY TESTS
    # =========================================================================
    def test_generate_api_key(self):
        """generate_api_key must create key with orange_sk_ prefix, store SHA-256 hash in DB."""
        raw_key, key_hash = generate_api_key("Orange Innovation Lab", self.session)
        self.assertTrue(raw_key.startswith("orange_sk_"))
        self.assertEqual(len(raw_key), len("orange_sk_") + 32)
        expected_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        self.assertEqual(key_hash, expected_hash)

        # Verify key exists and is active in database
        db_key = (
            self.session.query(MCPApiKey)
            .filter(MCPApiKey.key_hash == key_hash)
            .first()
        )
        self.assertIsNotNone(db_key)
        self.assertEqual(db_key.tenant_name, "Orange Innovation Lab")
        self.assertTrue(db_key.is_active)

    def test_generate_api_key_empty_tenant_raises_error(self):
        """generate_api_key should reject empty tenant names."""
        with self.assertRaises(ValueError):
            generate_api_key("", self.session)

    def test_auth_provision_endpoint(self):
        """POST /api/auth/keys should provision key via REST API."""
        response = self.client.post(
            "/api/auth/keys",
            json={"tenant_name": "Acme Corp"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["tenant_name"], "Acme Corp")
        self.assertTrue(data["raw_key"].startswith("orange_sk_"))
        self.assertEqual(
            data["key_hash"],
            hashlib.sha256(data["raw_key"].encode("utf-8")).hexdigest(),
        )

    def test_auth_verify_with_valid_key(self):
        """GET /api/auth/verify with valid Bearer token should authenticate successfully."""
        raw_key, _ = generate_api_key("Enterprise Sales Team", self.session)
        headers = {"Authorization": f"Bearer {raw_key}"}
        response = self.client.get("/api/auth/verify", headers=headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "AUTHENTICATED")
        self.assertEqual(data.get("tenant_name"), "Enterprise Sales Team")
        self.assertTrue(data.get("is_active"))

    def test_auth_verify_with_missing_token_returns_401(self):
        """GET /api/auth/verify without Authorization header should return 401."""
        response = self.client.get("/api/auth/verify")
        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())

    def test_auth_verify_with_invalid_token_returns_401(self):
        """GET /api/auth/verify with non-existent token should return 401."""
        headers = {"Authorization": "Bearer orange_sk_invalid_fake_key_123456"}
        response = self.client.get("/api/auth/verify", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid or inactive API key", response.json()["detail"])

    def test_auth_dev_bypass_when_strict_production_false(self):
        """When STRICT_PRODUCTION=False, orange_dev_token bypasses authentication."""
        with patch.dict(os.environ, {"STRICT_PRODUCTION": "False"}):
            headers = {"Authorization": "Bearer orange_dev_token"}
            response = self.client.get("/api/auth/verify", headers=headers)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data.get("status"), "AUTHENTICATED")
            self.assertEqual(data.get("tenant_name"), "dev_tenant")

    def test_auth_dev_bypass_rejected_when_strict_production_true(self):
        """When STRICT_PRODUCTION=True, orange_dev_token is rejected with 401."""
        with patch.dict(os.environ, {"STRICT_PRODUCTION": "True"}):
            headers = {"Authorization": "Bearer orange_dev_token"}
            response = self.client.get("/api/auth/verify", headers=headers)
            self.assertEqual(response.status_code, 401)

    # =========================================================================
    # 3. LEADS & EVIDENCE ROUTE TESTS
    # =========================================================================
    def test_get_leads_default(self):
        """GET /api/leads with default threshold (70) should return DHL (score 86)."""
        response = self.client.get("/api/leads")
        self.assertEqual(response.status_code, 200)
        leads = response.json()
        self.assertIsInstance(leads, list)
        self.assertTrue(any(l["company"] == "DHL Group" for l in leads))
        # Lufthansa has score 46, so should be filtered out at min_score=70
        self.assertFalse(any(l["company"] == "Lufthansa Group" for l in leads))

    def test_get_leads_with_lower_min_score(self):
        """GET /api/leads with min_score=40 should return both DHL and Lufthansa."""
        response = self.client.get("/api/leads?service_line=Agentic+Automation&min_score=40")
        self.assertEqual(response.status_code, 200)
        leads = response.json()
        self.assertTrue(any(l["company"] == "DHL Group" for l in leads))
        self.assertTrue(any(l["company"] == "Lufthansa Group" for l in leads))

    def test_get_leads_with_high_min_score(self):
        """GET /api/leads with min_score=95 should return an empty list."""
        response = self.client.get("/api/leads?min_score=95")
        self.assertEqual(response.status_code, 200)
        leads = response.json()
        self.assertEqual(leads, [])

    def test_get_lead_evidence_canonical_domain(self):
        """GET /api/leads/dhl.com/evidence should return verified evidence quotes."""
        response = self.client.get("/api/leads/dhl.com/evidence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("company"), "DHL Group")
        self.assertEqual(data.get("status"), "QUALIFIED")
        evals = data.get("evaluations", [])
        self.assertGreater(len(evals), 0)
        self.assertIn("Strategy 2030", evals[0]["evidence_quote"])

    def test_get_lead_evidence_unknown_domain(self):
        """GET /api/leads/{domain}/evidence for unknown domain returns NOT_FOUND status."""
        response = self.client.get("/api/leads/unknown-company-abc.org/evidence")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "NOT_FOUND")
        self.assertIn("message", data)

    def test_lead_feedback_thumbs_up(self):
        """POST /api/leads/{lead_id}/feedback records positive qualification feedback."""
        payload = {
            "is_accurate": True,
            "notes": "Verified C-level mandate on agentic systems",
        }
        response = self.client.post("/api/leads/lead-dhl-001/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("lead_id"), "lead-dhl-001")
        self.assertTrue(data.get("is_accurate"))
        self.assertEqual(data.get("status"), "RECORDED")
        self.assertIn("Verified C-level", data.get("notes"))

        # Verify persisted in scoring service store
        feedback_list = get_lead_feedback("lead-dhl-001")
        self.assertEqual(len(feedback_list), 1)
        self.assertTrue(feedback_list[0]["is_accurate"])

    def test_lead_feedback_thumbs_down_alternative_field(self):
        """POST /api/leads/{lead_id}/feedback with thumbs_up=False."""
        payload = {
            "thumbs_up": False,
            "notes": "Internal IT department handles all development",
        }
        response = self.client.post("/api/leads/lead-lh-002/feedback", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("lead_id"), "lead-lh-002")
        self.assertFalse(data.get("is_accurate"))
        self.assertEqual(data.get("status"), "RECORDED")

    # =========================================================================
    # 4. OUTREACH QUEUE & APPROVAL TESTS
    # =========================================================================
    def test_outreach_stage_and_queue(self):
        """Staging a draft puts it in the human approval queue."""
        stage_resp = self.client.post(
            "/api/outreach/stage",
            json={
                "recipient_email": "vp_engineering@dhl.com",
                "subject": "Agentic RFQ Co-delivery",
                "email_body": "Proposed co-delivery architecture...",
                "dry_run": True,
            },
        )
        self.assertEqual(stage_resp.status_code, 200)
        staged_data = stage_resp.json()
        draft_id = staged_data["draft_id"]
        self.assertEqual(staged_data["status"], "AWAITING_HUMAN_APPROVAL")

        # Query GET /api/outreach/queue
        queue_resp = self.client.get("/api/outreach/queue")
        self.assertEqual(queue_resp.status_code, 200)
        queue_items = queue_resp.json()
        self.assertIsInstance(queue_items, list)
        self.assertTrue(any(it["draft_id"] == draft_id for it in queue_items))

    def test_outreach_approve_and_dispatch(self):
        """Approving a staged draft transitions status to DISPATCHED."""
        staged = queue_sales_outreach(
            recipient_email="cto@siemens.com",
            subject="Automation Briefing",
            email_body="Briefing details...",
            dry_run=True,
        )
        draft_id = staged["draft_id"]

        # Call approve endpoint
        approve_resp = self.client.post(f"/api/outreach/{draft_id}/approve")
        self.assertEqual(approve_resp.status_code, 200)
        data = approve_resp.json()
        self.assertEqual(data.get("status"), "DISPATCHED")
        self.assertEqual(data["draft"]["status"], "DISPATCHED")
        self.assertTrue(data["draft"]["simulated_dispatch"])

        # Queue should now be empty of AWAITING_HUMAN_APPROVAL drafts
        queue_resp = self.client.get("/api/outreach/queue")
        self.assertEqual(queue_resp.status_code, 200)
        queue_items = queue_resp.json()
        self.assertFalse(any(it["draft_id"] == draft_id for it in queue_items))

    def test_outreach_approve_nonexistent_returns_404(self):
        """Approving a nonexistent draft returns 404 Not Found."""
        response = self.client.post("/api/outreach/draft_nonexistent_999/approve")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    # =========================================================================
    # 5. INTEGRATION WITH OFFERINGS ROUTE & CORS
    # =========================================================================
    def test_offerings_compile_route_included(self):
        """The app should have /api/offerings/compile route registered."""
        response = self.client.post(
            "/api/offerings/compile",
            json={"user_input": "Commercial Cargo E-Bikes for Last-Mile Courier Fleets"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("offering_name", data)
        self.assertIn("signal_rules", data)

    def test_cors_middleware_headers(self):
        """App must allow cross-origin requests for dev and web dashboard."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }
        response = self.client.options("/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            response.headers.get("access-control-allow-origin"),
            ["*", "http://localhost:3000"],
        )


if __name__ == "__main__":
    unittest.main()
