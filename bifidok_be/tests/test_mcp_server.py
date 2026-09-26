import json
import os
import sys
import unittest
from unittest.mock import patch

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from mcp_server import (
    mcp,
    get_prioritized_leads,
    get_signal_evidence,
    prepare_grounded_pitch,
    send_sales_outreach_email,
)
from services.leads_service import (
    query_prioritized_leads,
    query_signal_evidence,
    format_grounded_pitch,
    queue_sales_outreach,
    OUTREACH_QUEUE,
)
from db.schema import Base, Company, ServiceOffering, LeadScore
from db.session import SessionLocal, engine


class TestFastMCPServer(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        OUTREACH_QUEUE.clear()

    def test_registered_tools(self):
        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        expected_tools = [
            "get_prioritized_leads",
            "get_signal_evidence",
            "prepare_grounded_pitch",
            "send_sales_outreach_email",
        ]
        for expected in expected_tools:
            self.assertIn(expected, tool_names)

    def test_get_prioritized_leads_canonical_filter(self):
        # min_score=70 should only return DHL (86)
        res_70_str = get_prioritized_leads(service_line="Agentic Automation", min_score=70)
        leads_70 = json.loads(res_70_str)
        self.assertIsInstance(leads_70, list)
        self.assertTrue(any(l["company"] == "DHL Group" for l in leads_70))
        self.assertFalse(any(l["company"] == "Lufthansa Group" for l in leads_70))

        # min_score=40 should return both
        res_40_str = get_prioritized_leads(service_line="Agentic Automation", min_score=40)
        leads_40 = json.loads(res_40_str)
        self.assertTrue(any(l["company"] == "DHL Group" for l in leads_40))
        self.assertTrue(any(l["company"] == "Lufthansa Group" for l in leads_40))

    def test_get_signal_evidence(self):
        # Canonical existing domain
        ev_dhl_str = get_signal_evidence("dhl.com")
        dhl_data = json.loads(ev_dhl_str)
        self.assertEqual(dhl_data.get("company"), "DHL Group")
        self.assertEqual(dhl_data.get("status"), "QUALIFIED")
        self.assertGreater(len(dhl_data.get("evaluations", [])), 0)

        # Nonexistent domain
        ev_unknown_str = get_signal_evidence("unknown-corp-xyz.io")
        unknown_data = json.loads(ev_unknown_str)
        self.assertEqual(unknown_data.get("status"), "NOT_FOUND")

    def test_prepare_grounded_pitch(self):
        pitch = prepare_grounded_pitch(
            company_name="BMW Group",
            recipient_title="Head of Digitalization",
            evidence_quote="Accelerating production line automation by 40%",
            value_prop="custom RPA and high-velocity engineering squads",
        )
        self.assertIn("BMW Group", pitch)
        self.assertIn("Head of Digitalization", pitch)
        self.assertIn("Accelerating production line automation by 40%", pitch)
        self.assertIn("custom RPA and high-velocity engineering squads", pitch)
        self.assertIn("Orange Systems", pitch)

    def test_send_sales_outreach_email_dry_run_and_dispatched(self):
        # Dry run staging
        res_dry = send_sales_outreach_email(
            recipient_email="cto@dhl.com",
            subject="Automation briefing",
            email_body="Hello team...",
            dry_run=True,
        )
        self.assertIn("SUCCESS: Draft", res_dry)
        self.assertIn("staged in Orange Dashboard queue for human review", res_dry)

        # Verify entry in queue
        self.assertEqual(len(OUTREACH_QUEUE), 1)
        draft_id = list(OUTREACH_QUEUE.keys())[0]
        self.assertEqual(OUTREACH_QUEUE[draft_id]["status"], "AWAITING_HUMAN_APPROVAL")
        self.assertEqual(OUTREACH_QUEUE[draft_id]["recipient"], "cto@dhl.com")

        # Dispatched send
        res_dispatched = send_sales_outreach_email(
            recipient_email="ciso@dhl.com",
            subject="Security audit",
            email_body="Security details...",
            dry_run=False,
        )
        self.assertIn("SUCCESS: Email dispatched to ciso@dhl.com", res_dispatched)
        self.assertEqual(len(OUTREACH_QUEUE), 2)


if __name__ == "__main__":
    unittest.main()
