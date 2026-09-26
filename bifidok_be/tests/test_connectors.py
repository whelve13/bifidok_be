import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from connectors import fetch_gdelt_signals, fetch_public_procurement_tenders, is_official_contract_award


class TestGDELTConnector(unittest.TestCase):
    @patch("requests.get")
    def test_fetch_gdelt_signals_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"articles": [{"title": "DHL expands autonomous fleet", "url": "https://example.com/dhl-fleet", "seendate": "20260920T100000Z", "domain": "example.com"}]}'
        mock_response.json.return_value = {
            "articles": [
                {
                    "title": "DHL expands autonomous fleet",
                    "url": "https://example.com/dhl-fleet",
                    "seendate": "20260920T100000Z",
                    "domain": "example.com"
                }
            ]
        }
        mock_get.return_value = mock_response

        signals = fetch_gdelt_signals("DHL Group", keywords=["autonomous", "fleet"])
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["title"], "DHL expands autonomous fleet")
        self.assertEqual(signals[0]["url"], "https://example.com/dhl-fleet")
        self.assertEqual(signals[0]["seendate"], "20260920T100000Z")
        self.assertEqual(signals[0]["domain"], "example.com")
        self.assertEqual(signals[0]["raw_text"], "DHL expands autonomous fleet")

    @patch("requests.get")
    def test_fetch_gdelt_signals_empty_or_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = ""
        mock_get.return_value = mock_response

        signals = fetch_gdelt_signals("Test Company")
        self.assertEqual(signals, [])

    def test_fetch_gdelt_signals_empty_company(self):
        signals = fetch_gdelt_signals("")
        self.assertEqual(signals, [])


class TestPublicProcurementTenders(unittest.TestCase):
    def test_is_official_contract_award(self):
        # TED domain link
        self.assertTrue(is_official_contract_award("https://ted.europa.eu/en/notice/-/detail/123456-2024", "IT Services RFP"))
        # TED award notice format
        self.assertTrue(is_official_contract_award("https://news.example.com", "Award of contract: 2024/S 123-456789 Cloud Hosting"))
        # Contract Award ID phrase
        self.assertTrue(is_official_contract_award("https://example.com", "Tender result - Contract Award ID: TED-98765"))
        # Standard unconfirmed news mention
        self.assertFalse(is_official_contract_award("https://news.google.com/rss/articles/CBMi...", "Knorr-Bremse bids for digital rail tender"))

    @patch("requests.get")
    def test_tender_rss_unconfirmed_capped_at_40(self, mock_get):
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>Knorr-Bremse evaluates railway automation procurement tender</title>
                    <link>https://news.google.com/rss/articles/abc123</link>
                </item>
            </channel>
        </rss>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = rss_xml.encode("utf-8")
        mock_get.return_value = mock_resp

        results = fetch_public_procurement_tenders("Knorr-Bremse")
        self.assertTrue(results["active_tender_rfp"])
        self.assertEqual(results["tender_count"], 1)
        self.assertEqual(results["source"], "Public Procurement News Feed")
        self.assertEqual(results["confidence"], 0.40)
        self.assertFalse(results["has_official_award"])
        self.assertIn("Public Procurement News Mention (Unconfirmed)", results["evidence"][0])

    @patch("requests.get")
    def test_tender_official_ted_detected(self, mock_get):
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <item>
                    <title>European Railway Agency - Contract award 2024/S 050-123456</title>
                    <link>https://ted.europa.eu/udl?uri=TED:NOTICE:123456-2024:TEXT:EN:HTML</link>
                </item>
            </channel>
        </rss>"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = rss_xml.encode("utf-8")
        mock_get.return_value = mock_resp

        results = fetch_public_procurement_tenders("Knorr-Bremse")
        self.assertTrue(results["active_tender_rfp"])
        self.assertTrue(results["has_official_award"])
        self.assertEqual(results["source"], "TED (Tenders Electronic Daily)")
        self.assertGreaterEqual(results["confidence"], 0.85)
        self.assertIn("Official Public Procurement Notice", results["evidence"][0])


if __name__ == "__main__":
    unittest.main()
