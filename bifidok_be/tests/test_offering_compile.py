import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from fastapi.testclient import TestClient
from api.routes_config import app
from engine.offering_catalog import (
    decompose_custom_offering,
    offering_dict_to_profile,
    OfferingProfile,
    CommercialWedge,
)
from engine.prospecting_engine import CustomerProspectingEngine


class TestOfferingCompile(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_decompose_custom_offering_archetype(self):
        """Test decomposition using an archetype keyword (e-bikes)."""
        compiled = decompose_custom_offering("Commercial Cargo E-Bikes for Last-Mile Courier Fleets")
        self.assertIsInstance(compiled, dict)
        expected_keys = {"offering_name", "description", "signal_rules", "connector_queries", "disqualifiers"}
        self.assertTrue(expected_keys.issubset(compiled.keys()))
        self.assertIn("Cargo", compiled["offering_name"])
        self.assertIsInstance(compiled["signal_rules"], list)
        self.assertGreater(len(compiled["signal_rules"]), 0)

        for rule in compiled["signal_rules"]:
            self.assertIn("question", rule)
            self.assertIn("guidance_notes", rule)
            self.assertIn("weight", rule)
            self.assertIn("is_negative", rule)
            self.assertIn(rule["weight"], ["HIGH", "MEDIUM", "LOW", "DISQUALIFY"])

        conn_queries = compiled["connector_queries"]
        for key in ["news", "tenders", "ats", "developer", "security"]:
            self.assertIn(key, conn_queries)
            self.assertIsInstance(conn_queries[key], list)

    def test_decompose_custom_offering_generic(self):
        """Test decomposition with arbitrary commercial product."""
        compiled = decompose_custom_offering("Commercial Solar Panels and Battery Storage for Factories")
        self.assertIsInstance(compiled, dict)
        self.assertIn("Solar", compiled["offering_name"])
        self.assertIsInstance(compiled["disqualifiers"], list)
        self.assertGreater(len(compiled["disqualifiers"]), 0)
        self.assertGreater(len(compiled["signal_rules"]), 0)

    @patch("google.generativeai.GenerativeModel")
    @patch("google.generativeai.configure")
    def test_decompose_custom_offering_gemini_success(self, mock_configure, mock_model_class):
        """Test decomposition when Gemini LLM returns valid structured JSON."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        gemini_payload = {
            "offering_name": "Autonomous Drone Fleet Inspection",
            "description": "Enterprise autonomous drone inspection for offshore wind turbines.",
            "signal_rules": [
                {
                    "question": "Does the enterprise operate offshore wind farm assets?",
                    "guidance_notes": "Look for offshore energy concessions.",
                    "weight": "HIGH",
                    "is_negative": False,
                },
                {
                    "question": "Is the enterprise under active bankruptcy proceedings?",
                    "guidance_notes": "Financial insolvency disqualifies vendor onboarding.",
                    "weight": "DISQUALIFY",
                    "is_negative": True,
                },
            ],
            "connector_queries": {
                "news": ["offshore wind", "turbine maintenance"],
                "tenders": ["drone inspection", "blade integrity"],
                "ats": ["Drone Pilot", "Turbine Inspection Lead"],
                "developer": ["PX4 autopilot", "computer vision"],
                "security": ["airspace compliance", "aviation authority"],
            },
            "disqualifiers": [
                "Enterprises with no wind power or physical energy generation assets",
                "Company under active bankruptcy or insolvency proceedings",
            ],
        }
        mock_response = MagicMock()
        mock_response.text = f"```json\n{json.dumps(gemini_payload)}\n```"
        mock_model.generate_content.return_value = mock_response

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_test_key"}):
            compiled = decompose_custom_offering("Autonomous Drone Fleet Inspection")

        self.assertEqual(compiled["offering_name"], "Autonomous Drone Fleet Inspection")
        self.assertEqual(len(compiled["signal_rules"]), 2)
        self.assertIn("PX4 autopilot", compiled["connector_queries"]["developer"])

    def test_offering_dict_to_profile(self):
        """Test converting compiled dict into OfferingProfile."""
        compiled = decompose_custom_offering("Commercial Cargo E-Bikes for Last-Mile Delivery")
        profile = offering_dict_to_profile(compiled)

        self.assertIsInstance(profile, OfferingProfile)
        self.assertTrue(profile.offering_id.startswith("custom_"))
        self.assertEqual(profile.title, compiled["offering_name"])
        self.assertGreater(len(profile.target_wedges), 0)
        self.assertTrue(profile.requires_physical_presence)
        self.assertIsInstance(profile.ats_roles, list)
        self.assertIsInstance(profile.tender_keywords, list)
        self.assertIsInstance(profile.signal_keywords, list)

        # Check wedge attributes
        first_wedge = profile.target_wedges[0]
        self.assertIsInstance(first_wedge, CommercialWedge)
        self.assertTrue(bool(first_wedge.name))
        self.assertTrue(bool(first_wedge.value_driver))

    def test_prospecting_engine_resolves_dict_profile(self):
        """Test CustomerProspectingEngine resolves a custom offering dictionary."""
        engine = CustomerProspectingEngine()
        compiled = decompose_custom_offering("Industrial Warehouse Robotics")
        profile = engine._resolve_offering(compiled)

        self.assertIsInstance(profile, OfferingProfile)
        self.assertEqual(profile.title, compiled["offering_name"])
        self.assertTrue(profile.requires_physical_presence)

    def test_api_compile_endpoint_success(self):
        """Test POST /api/offerings/compile with valid input."""
        response = self.client.post(
            "/api/offerings/compile",
            json={"user_input": "Commercial Solar Panels for Manufacturing Hubs"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("offering_name", data)
        self.assertIn("description", data)
        self.assertIn("signal_rules", data)
        self.assertIn("connector_queries", data)
        self.assertIn("disqualifiers", data)
        self.assertIsInstance(data["signal_rules"], list)
        self.assertGreater(len(data["signal_rules"]), 0)

    def test_api_compile_endpoint_alternative_field(self):
        """Test POST /api/offerings/compile with offering_text field."""
        response = self.client.post(
            "/api/offerings/compile",
            json={"offering_text": "Cyber SOC and NIS2 Compliance"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Cyber", data["offering_name"])

    def test_api_compile_endpoint_empty_input(self):
        """Test POST /api/offerings/compile with empty payload returns 400."""
        response = self.client.post(
            "/api/offerings/compile",
            json={"user_input": "   "},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
