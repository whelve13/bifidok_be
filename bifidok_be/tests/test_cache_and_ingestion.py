import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from connectors.financials import fetch_financial_signals
from connectors.firmographics import resolve_company_entity
from db.schema import Base, Company, LeadScore, ServiceOffering, SignalEvaluation
from db.session import SessionLocal, engine
from services.cache import (
    InMemoryTTLCache,
    delete_cache,
    get_cache,
    get_job_status,
    reset_cache_state,
    set_cache,
    update_job_status,
)
from services.ingestion_coordinator import (
    compute_3_layer_composite_score,
    run_async_ingestion,
    tier1_filter_chunk,
    tier2_extract_signal,
)


class TestCacheService(unittest.TestCase):
    def setUp(self):
        reset_cache_state(force_redis=False)

    def test_in_memory_ttl_cache_basic(self):
        cache = InMemoryTTLCache()
        cache.set("key1", {"score": 95}, ttl=10)
        self.assertEqual(cache.get("key1"), {"score": 95})

        # Test mutation safety
        val = cache.get("key1")
        val["score"] = 50
        self.assertEqual(cache.get("key1"), {"score": 95})

    def test_in_memory_ttl_cache_expiry(self):
        cache = InMemoryTTLCache()
        cache.set("short_key", "temporary_value", ttl=0.1)
        self.assertEqual(cache.get("short_key"), "temporary_value")
        time.sleep(0.15)
        self.assertIsNone(cache.get("short_key"))

    def test_get_set_cache_fallback(self):
        set_cache("test_key", {"company": "Test Enterprise", "revenue": 1000}, ttl=3600)
        cached = get_cache("test_key")
        self.assertIsInstance(cached, dict)
        self.assertEqual(cached["company"], "Test Enterprise")

        delete_cache("test_key")
        self.assertIsNone(get_cache("test_key"))

    def test_job_status_lifecycle(self):
        job_id = "test_job_123"
        update_job_status(job_id, status="STARTED", progress=0.0, meta={"step": 1})
        status = get_job_status(job_id)

        self.assertIsNotNone(status)
        self.assertEqual(status["job_id"], job_id)
        self.assertEqual(status["status"], "STARTED")
        self.assertEqual(status["progress"], 0.0)
        self.assertEqual(status["meta"]["step"], 1)

        # Progress update with clamping
        update_job_status(job_id, status="PROCESSING", progress=0.5567)
        status2 = get_job_status(job_id)
        self.assertEqual(status2["status"], "PROCESSING")
        self.assertEqual(status2["progress"], 0.557)

        # Clamping check: > 1.0 clamped to 1.0
        update_job_status(job_id, status="COMPLETED", progress=1.5)
        status3 = get_job_status(job_id)
        self.assertEqual(status3["progress"], 1.0)
        self.assertEqual(status3["status"], "COMPLETED")

    @patch("redis.Redis.from_url")
    def test_redis_operations_when_connected(self, mock_from_url):
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = '{"redis": true, "val": 42}'
        mock_from_url.return_value = mock_client

        reset_cache_state()
        val = get_cache("redis_key")
        self.assertEqual(val, {"redis": True, "val": 42})
        mock_client.get.assert_called_with("redis_key")


class TestConnectorsCaching(unittest.TestCase):
    def setUp(self):
        reset_cache_state(force_redis=False)

    @patch("connectors.firmographics.requests.get")
    def test_firmographics_caching(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"name": "Acme Corp", "domain": "acme.com"}]
        mock_get.return_value = mock_resp

        # First call: executes HTTP query and caches response
        res1 = resolve_company_entity("Acme Corp")
        self.assertEqual(res1["domain"], "acme.com")
        initial_call_count = mock_get.call_count

        # Second call: served from cache, HTTP call count should not increase for Clearbit
        res2 = resolve_company_entity("Acme Corp")
        self.assertEqual(res2["domain"], "acme.com")
        # Ensure Clearbit was read from cache
        self.assertIsNotNone(get_cache("cache:clearbit:acme corp"))

    @patch("connectors.financials.requests.get")
    @patch("connectors.financials.yf.Ticker")
    def test_financials_caching(self, mock_ticker_cls, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"quotes": [{"symbol": "ACM.DE"}]}
        mock_get.return_value = mock_resp

        mock_ticker_obj = MagicMock()
        mock_ticker_obj.info = {
            "fullTimeEmployees": 12000,
            "sector": "Industrial",
            "country": "Germany",
            "operatingMargins": 0.18,
        }
        mock_ticker_cls.return_value = mock_ticker_obj

        # First call: hits search and ticker info
        res1 = fetch_financial_signals("Acme Corp")
        self.assertEqual(res1["ticker"], "ACM.DE")
        self.assertEqual(res1["headcount"], 12000)

        # Verify cached
        cached_search = get_cache("cache:yahoo_search:acme corp")
        self.assertIsNotNone(cached_search)
        cached_info = get_cache("cache:yahoo_info:ACM.DE")
        self.assertIsNotNone(cached_info)
        self.assertEqual(cached_info["fullTimeEmployees"], 12000)

        # Second call: uses cache
        res2 = fetch_financial_signals("Acme Corp")
        self.assertEqual(res2["ticker"], "ACM.DE")
        self.assertEqual(res2["headcount"], 12000)


class TestIngestionCoordinator(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        reset_cache_state(force_redis=False)

    def test_tier1_filter_chunk(self):
        noise = "Accept all cookies and click here to review our privacy policy. Copyright © 2026."
        self.assertFalse(tier1_filter_chunk(noise))

        signal_text = (
            "The corporate Strategy 2030 prioritizes agentic AI and workflow automation to modernise operations."
        )
        self.assertTrue(tier1_filter_chunk(signal_text))

        custom_kw_text = "The enterprise operates 500 cargo e-bikes for urban micro-mobility hubs."
        self.assertTrue(tier1_filter_chunk(custom_kw_text, trigger_keywords=["cargo", "e-bikes"]))

    def test_tier2_extract_signal_deterministic(self):
        source = (
            "General news overview. Lufthansa Group announced an official target to reduce 4,000 administrative jobs "
            "by 2030 using automated tools and workflow consolidation. Financial disclosures remain stable."
        )
        detected, conf, quote, reason = tier2_extract_signal(
            rule_question="Is the organization targeting headcount reduction or administrative job automation?",
            rule_guidance="Search for administrative job reduction targets.",
            source_text=source,
        )
        self.assertTrue(detected)
        self.assertGreaterEqual(conf, 0.60)
        self.assertIn("reduce 4,000 administrative jobs", quote)
        self.assertTrue(bool(reason))

    def test_compute_3_layer_composite_score(self):
        # Qualified lead test
        evals = [
            {
                "detected": True,
                "confidence": 0.90,
                "weight": "HIGH",
                "is_negative": False,
                "question": "Deploying agentic AI?",
            },
            {
                "detected": True,
                "confidence": 0.85,
                "weight": "MEDIUM",
                "is_negative": False,
                "question": "RFP for automation?",
            },
        ]
        firmographics = {"is_solvent": True, "headcount": 50000, "operating_margin": 0.16}
        catalysts = {"matched_roles": ["Automation Engineer", "AI Lead"], "has_tenders": True, "has_news": True}

        score, is_disq, disq_reason, summary = compute_3_layer_composite_score(evals, firmographics, catalysts)
        self.assertFalse(is_disq)
        self.assertIsNone(disq_reason)
        self.assertGreater(score, 60)
        self.assertIn("Layer 1 Signals", summary)

        # Disqualified lead test: insolvency
        inso_score, inso_disq, inso_reason, _ = compute_3_layer_composite_score(
            evals, {"is_solvent": False}, catalysts
        )
        self.assertEqual(inso_score, 0)
        self.assertTrue(inso_disq)
        self.assertIn("insolvency", inso_reason.lower())

        # Disqualified lead test: high-confidence DISQUALIFY rule
        disq_evals = [
            {
                "detected": True,
                "confidence": 0.95,
                "weight": "DISQUALIFY",
                "is_negative": True,
                "question": "Active bankruptcy proceeding?",
            }
        ]
        gate_score, gate_disq, gate_reason, _ = compute_3_layer_composite_score(
            disq_evals, {"is_solvent": True, "headcount": 1000}, catalysts
        )
        self.assertEqual(gate_score, 0)
        self.assertTrue(gate_disq)
        self.assertIn("disqualifying rule", gate_reason.lower())

    async def test_run_async_ingestion_end_to_end(self):
        job_id = "test_ingestion_job_001"
        service_id = "agentic_automation"
        domains = ["dhl.com"]

        await run_async_ingestion(job_id=job_id, service_id=service_id, domains=domains)

        # Verify job completed in cache
        status = get_job_status(job_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "COMPLETED")
        self.assertEqual(status["progress"], 1.0)
        self.assertEqual(status["meta"]["domains_completed"], 1)

        # Verify DB records
        session = SessionLocal()
        try:
            company = session.query(Company).filter(Company.domain == "dhl.com").first()
            self.assertIsNotNone(company)
            self.assertEqual(company.name, "DHL Group")

            lead_score = (
                session.query(LeadScore).filter(LeadScore.company_id == company.id).first()
            )
            self.assertIsNotNone(lead_score)
            self.assertGreater(lead_score.composite_score, 0)
            self.assertFalse(lead_score.is_disqualified)

            # Verify cached evidence for domain
            evidence_cache = get_cache("evidence:dhl.com")
            self.assertIsNotNone(evidence_cache)
            self.assertEqual(evidence_cache["domain"], "dhl.com")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
