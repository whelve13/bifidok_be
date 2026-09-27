"""
Test Suite for Local Machine Learning Models & Autonomous Scout.
Validates:
1. Multi-modal 14D feature extraction.
2. Local ML model inference (LightGBM, LogisticRegression, RandomForest).
3. Dynamic learned feature importances (no hardcoded weights).
4. Hard-gate disqualification for insolvency and physical footprint mismatch.
5. Autonomous entity discovery via Wikipedia category and registry scout.
"""
import os
import sys
import unittest
import numpy as np

# Ensure bifidok_be is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.abspath(os.path.join(current_dir, ".."))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from engine.local_ml.feature_extractor import extract_feature_vector, FEATURE_NAMES
from engine.local_ml.inference import get_local_models, predict_lead_evaluation
from engine.autonomous_scout import derive_discovery_queries, discover_candidate_universe
from engine.offering_catalog import FLAGSHIP_OFFERINGS


class TestLocalMLAndScout(unittest.TestCase):
    def setUp(self):
        self.models = get_local_models()

    def test_feature_vector_shape_and_types(self):
        """Test that feature extraction produces 14D float32 vectors."""
        company = {
            "name": "Test Logistics AG",
            "headcount": 5000,
            "operating_margin": 0.08,
            "is_solvent": True,
            "sector": "Logistics & Transport",
            "operational_attributes": {"urban_delivery_fleets": True},
        }
        signals = {
            "matched_roles": ["Fleet Manager", "Logistics Lead"],
            "has_tenders": True,
            "has_official_award": True,
            "has_news": True,
            "security_grade": "A",
            "missing_headers": [],
            "cisa_kev_count": 0,
            "github_repo_count": 12,
            "semantic_relevance": 0.92,
        }
        offering = FLAGSHIP_OFFERINGS["commercial_bikes"]

        vec = extract_feature_vector(company, signals, offering)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (len(FEATURE_NAMES),))
        self.assertEqual(len(FEATURE_NAMES), 18)
        self.assertGreater(vec[0], 3.0)  # log10(5000) ~ 3.69
        self.assertEqual(vec[2], 1.0)    # is_solvent

    def test_local_ml_qualified_lead_scoring(self):
        """Test local ML prediction for a prime qualified enterprise."""
        company = {
            "name": "DHL Group",
            "headcount": 590000,
            "operating_margin": 0.07,
            "is_solvent": True,
            "sector": "Logistics",
            "operational_attributes": {"urban_delivery_fleets": True},
        }
        signals = {
            "matched_roles": ["Fleet Operations", "Cargo Lead"],
            "has_tenders": True,
            "has_official_award": True,
            "has_news": True,
            "security_grade": "B",
            "missing_headers": ["CSP"],
            "semantic_relevance": 0.95,
        }
        offering = FLAGSHIP_OFFERINGS["commercial_bikes"]

        res = predict_lead_evaluation(company, signals, offering)
        self.assertFalse(res["is_disqualified"])
        self.assertIsNone(res["disqualification_reason"])
        self.assertGreaterEqual(res["propensity_score"], 80.0)
        self.assertIn("Tier 1", res["tier"])

        # Validate learned dynamic weights
        weights = res["dynamic_weights"]
        self.assertIsInstance(weights, dict)
        self.assertGreater(len(weights), 5)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=1)

    def test_local_ml_hard_disqualification_insolvency(self):
        """Test that local ML hard-disqualifies insolvent enterprises."""
        company = {
            "name": "Signa Holding",
            "headcount": 1500,
            "operating_margin": -0.25,
            "is_solvent": False,
            "sector": "Real Estate",
            "operational_attributes": {"physical_footprint_level": "Insolvent"},
        }
        signals = {"has_news": True}
        offering = FLAGSHIP_OFFERINGS["commercial_bikes"]

        res = predict_lead_evaluation(company, signals, offering)
        self.assertTrue(res["is_disqualified"])
        self.assertEqual(res["propensity_score"], 0.0)
        self.assertEqual(res["tier"], "Disqualified")
        self.assertIn("insolvency", res["disqualification_reason"].lower())

    def test_local_ml_hard_disqualification_remote_mismatch(self):
        """Test that local ML hard-disqualifies 100% remote companies for physical offerings."""
        company = {
            "name": "GitLab",
            "headcount": 2100,
            "is_solvent": True,
            "sector": "Software",
            "operational_attributes": {"remote_only": True},
        }
        signals = {"semantic_relevance": 0.8}
        offering = FLAGSHIP_OFFERINGS["commercial_bikes"]  # requires_physical_presence = True

        res = predict_lead_evaluation(company, signals, offering)
        self.assertTrue(res["is_disqualified"])
        self.assertEqual(res["propensity_score"], 0.0)
        self.assertIn("remote", res["disqualification_reason"].lower())

    def test_autonomous_scout_discovery(self):
        """Test autonomous scout discovers real candidates matching mandate."""
        mandate = "Commercial Cargo Bikes for Last-Mile Urban Delivery Fleets"
        queries = derive_discovery_queries(mandate)
        self.assertIn("categories", queries)
        self.assertGreater(len(queries["categories"]), 0)

        universe = discover_candidate_universe(mandate, target_count=5)
        self.assertIsInstance(universe, list)
        self.assertGreaterEqual(len(universe), 1)

        first = universe[0]
        self.assertIn("name", first)
        self.assertIn("domain", first)
        self.assertIn("sector", first)


if __name__ == "__main__":
    unittest.main()
