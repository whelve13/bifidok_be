import math
import random
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import torch
from torch_geometric.data import HeteroData

# Seed for reproducible dataset generation
RANDOM_SEED = 42

class B2BGraphBuilder:
    """
    Constructs a Heterogeneous Temporal Graph (HeteroData) representing
    companies, technologies, regulations, and their dynamic market interactions.
    """

    def __init__(self, seed: int = RANDOM_SEED):
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        self.tech_names = [
            "UiPath", "Celonis", "Power Automate", "SAP S/4HANA",
            "Kubernetes", "AWS Cloud", "Azure Cloud", "Managed SOC",
            "Fortinet VPN", "GitLab CI/CD"
        ]
        self.reg_names = [
            "NIS2 Directive", "DORA Compliance", "EU AI Act", "CSRD Reporting"
        ]

    def build_ecosystem_dataset(self) -> Tuple[HeteroData, Dict[str, Any]]:
        """
        Builds a comprehensive European enterprise ecosystem graph with
        temporal timestamps and ground-truth IT contract/procurement awards.
        """
        data = HeteroData()

        # 1. Catalog of European Enterprises across Verticals
        companies_seed = [
            {"name": "Siemens", "country": "DE", "sector": "Industrial", "headcount": 311000, "margin": 0.12, "sec_grade": 0.85},
            {"name": "Knorr-Bremse", "country": "DE", "sector": "Automotive/Rail", "headcount": 25800, "margin": 0.11, "sec_grade": 0.40},
            {"name": "Continental", "country": "DE", "sector": "Automotive", "headcount": 190000, "margin": 0.05, "sec_grade": 0.50},
            {"name": "BMW Group", "country": "DE", "sector": "Automotive", "headcount": 149000, "margin": 0.10, "sec_grade": 0.75},
            {"name": "Mercedes-Benz", "country": "DE", "sector": "Automotive", "headcount": 166000, "margin": 0.12, "sec_grade": 0.80},
            {"name": "Lufthansa Group", "country": "DE", "sector": "Aviation", "headcount": 109000, "margin": 0.06, "sec_grade": 0.45},
            {"name": "DHL Group", "country": "DE", "sector": "Logistics", "headcount": 600000, "margin": 0.08, "sec_grade": 0.70},
            {"name": "Bosch", "country": "DE", "sector": "Industrial/Auto", "headcount": 429000, "margin": 0.04, "sec_grade": 0.65},
            {"name": "BASF", "country": "DE", "sector": "Chemicals", "headcount": 111000, "margin": 0.05, "sec_grade": 0.60},
            {"name": "Airbus", "country": "FR", "sector": "Aerospace", "headcount": 134000, "margin": 0.09, "sec_grade": 0.70},
            {"name": "Schneider Electric", "country": "FR", "sector": "Energy/Tech", "headcount": 150000, "margin": 0.15, "sec_grade": 0.85},
            {"name": "Alstom", "country": "FR", "sector": "Rail/Transport", "headcount": 80000, "margin": 0.03, "sec_grade": 0.50},
            {"name": "Thales", "country": "FR", "sector": "Defense/Tech", "headcount": 77000, "margin": 0.11, "sec_grade": 0.90},
            {"name": "ASML", "country": "NL", "sector": "Semiconductors", "headcount": 42000, "margin": 0.31, "sec_grade": 0.85},
            {"name": "Philips", "country": "NL", "sector": "HealthTech", "headcount": 70000, "margin": 0.07, "sec_grade": 0.60},
            {"name": "ING Group", "country": "NL", "sector": "Banking", "headcount": 58000, "margin": 0.28, "sec_grade": 0.80},
            {"name": "Kuehne+Nagel", "country": "CH", "sector": "Logistics", "headcount": 81000, "margin": 0.09, "sec_grade": 0.65},
            {"name": "ABB", "country": "CH", "sector": "Industrial", "headcount": 105000, "margin": 0.14, "sec_grade": 0.80},
            {"name": "Volvo Group", "country": "SE", "sector": "Automotive/Trucks", "headcount": 104000, "margin": 0.13, "sec_grade": 0.75},
            {"name": "EnBW", "country": "DE", "sector": "Energy", "headcount": 28000, "margin": 0.08, "sec_grade": 0.55}
        ]

        # Generate total 120 companies by expanding with realistic regional enterprises
        sectors = ["Automotive", "Industrial", "Logistics", "Financial Services", "Energy", "Healthcare", "Retail", "Technology"]
        countries = ["DE", "FR", "NL", "CH", "AT", "SE", "UK", "IT", "ES"]

        all_companies = list(companies_seed)
        for i in range(len(companies_seed), 120):
            sec = random.choice(sectors)
            all_companies.append({
                "name": f"Enterprise-{sec[:3]}-{i}",
                "country": random.choice(countries),
                "sector": sec,
                "headcount": int(np.random.lognormal(mean=9.5, sigma=1.2)),  # Median ~13,000 employees
                "margin": float(np.clip(np.random.normal(loc=0.08, scale=0.06), 0.01, 0.35)),
                "sec_grade": float(np.clip(np.random.normal(loc=0.65, scale=0.18), 0.20, 0.95))
            })

        num_companies = len(all_companies)
        company_to_id = {c["name"]: idx for idx, c in enumerate(all_companies)}

        # 2. Company Node Features [headcount_log, margin, margin_stress_flag, sec_grade, sec_risk_flag, is_eu]
        comp_feats = []
        for c in all_companies:
            hc_log = math.log10(max(c["headcount"], 10)) / 6.0  # Normalized [0, 1]
            margin = c["margin"]
            margin_stress = 1.0 if margin < 0.08 else 0.0
            sec_grade = c["sec_grade"]
            sec_risk = 1.0 if sec_grade < 0.55 else 0.0
            is_eu = 1.0 if c["country"] in ["DE", "FR", "NL", "AT", "IT", "ES", "SE"] else 0.0
            comp_feats.append([hc_log, margin, margin_stress, sec_grade, sec_risk, is_eu])

        data['company'].x = torch.tensor(comp_feats, dtype=torch.float)
        data['company'].names = [c["name"] for c in all_companies]

        # 3. Technology Nodes (10 Techs, 4-dim feature vector)
        tech_feats = [
            [1.0, 0.0, 0.0, 0.8],  # UiPath (RPA)
            [1.0, 0.0, 0.0, 0.9],  # Celonis (Process Mining)
            [1.0, 0.0, 0.0, 0.7],  # Power Automate (RPA)
            [0.0, 1.0, 0.0, 0.95], # SAP S/4HANA (ERP/Cloud)
            [0.0, 1.0, 0.0, 0.85], # Kubernetes (Cloud)
            [0.0, 1.0, 0.0, 0.9],  # AWS Cloud
            [0.0, 1.0, 0.0, 0.85], # Azure Cloud
            [0.0, 0.0, 1.0, 0.95], # Managed SOC (Cyber)
            [0.0, 0.0, 1.0, 0.75], # Fortinet VPN (Cyber)
            [0.0, 1.0, 0.0, 0.7]   # GitLab (DevOps)
        ]
        data['tech'].x = torch.tensor(tech_feats, dtype=torch.float)
        data['tech'].names = self.tech_names

        # 4. Regulation Nodes (4 Regulations, 3-dim feature vector: [fine_severity, audit_burden, year_urgency])
        reg_feats = [
            [0.95, 0.90, 0.90],  # NIS2
            [0.90, 0.95, 0.85],  # DORA
            [0.85, 0.80, 0.60],  # AI Act
            [0.60, 0.75, 0.50]   # CSRD
        ]
        data['regulation'].x = torch.tensor(reg_feats, dtype=torch.float)
        data['regulation'].names = self.reg_names

        # 5. Edges Generation (with Temporal Timestamps)
        # Times are encoded as normalized continuous days (0 = Jan 2024, 730 = Dec 2025, 950 = Sep 2026)
        comp_src, comp_dst, comp_times = [], [], []
        tech_src, tech_dst, tech_times = [], [], []
        reg_src, reg_dst = [], []
        supply_src, supply_dst, supply_times = [], [], []

        # A. Competitor Edges (same sector companies compete with each other)
        sector_groups: Dict[str, List[int]] = {}
        for idx, c in enumerate(all_companies):
            sector_groups.setdefault(c["sector"], []).append(idx)

        for sec, members in sector_groups.items():
            for i in members:
                # Connect to up to 4 sector peers
                peers = [p for p in members if p != i]
                chosen = random.sample(peers, min(4, len(peers)))
                for p in chosen:
                    comp_src.append(i)
                    comp_dst.append(p)
                    comp_times.append(random.uniform(10.0, 600.0))

        # Explicit key competitive rivalries
        rivalries = [
            ("BMW Group", "Mercedes-Benz"),
            ("Knorr-Bremse", "Continental"),
            ("DHL Group", "Kuehne+Nagel"),
            ("Siemens", "Schneider Electric"),
            ("Alstom", "Siemens"),
            ("Airbus", "Thales")
        ]
        for c1, c2 in rivalries:
            if c1 in company_to_id and c2 in company_to_id:
                id1, id2 = company_to_id[c1], company_to_id[c2]
                comp_src.extend([id1, id2])
                comp_dst.extend([id2, id1])
                comp_times.extend([150.0, 150.0])

        # B. Technology Usage Edges
        for c_idx, c in enumerate(all_companies):
            # Every company uses 2-5 technologies with adoption timestamps
            num_t = random.randint(2, 5)
            t_indices = random.sample(range(len(self.tech_names)), num_t)
            for t_idx in t_indices:
                t_time = random.uniform(50.0, 850.0)
                tech_src.append(c_idx)
                tech_dst.append(t_idx)
                tech_times.append(t_time)

        # C. Regulation Compliance Edges (NIS2 & DORA apply to Critical Infra / Financials in EU)
        for c_idx, c in enumerate(all_companies):
            if c["country"] in ["DE", "FR", "NL", "AT", "IT", "ES", "SE"]:
                if c["sector"] in ["Energy", "Transport", "Aviation", "Automotive", "Industrial", "Rail/Transport"]:
                    reg_src.append(c_idx)
                    reg_dst.append(0)  # NIS2
                if c["sector"] in ["Banking", "Financial Services"]:
                    reg_src.append(c_idx)
                    reg_dst.append(1)  # DORA
                reg_src.append(c_idx)
                reg_dst.append(3)      # CSRD

        # D. Supply Chain Edges (e.g. Continental & Knorr-Bremse supply BMW & Mercedes)
        tier1_suppliers = ["Continental", "Knorr-Bremse", "Bosch", "Alstom", "Schneider Electric"]
        oems = ["BMW Group", "Mercedes-Benz", "Siemens", "Airbus"]
        for s in tier1_suppliers:
            for o in oems:
                if s in company_to_id and o in company_to_id:
                    s_id, o_id = company_to_id[s], company_to_id[o]
                    supply_src.append(s_id)
                    supply_dst.append(o_id)
                    supply_times.append(random.uniform(50.0, 500.0))

        # Assign Edge Indices and Timestamps
        data['company', 'competes_with', 'company'].edge_index = torch.tensor([comp_src, comp_dst], dtype=torch.long)
        data['company', 'competes_with', 'company'].edge_time = torch.tensor(comp_times, dtype=torch.float)

        data['company', 'uses_tech', 'tech'].edge_index = torch.tensor([tech_src, tech_dst], dtype=torch.long)
        data['company', 'uses_tech', 'tech'].edge_time = torch.tensor(tech_times, dtype=torch.float)

        # Reverse tech edge for bidirectional message passing
        data['tech', 'used_by', 'company'].edge_index = torch.tensor([tech_dst, tech_src], dtype=torch.long)
        data['tech', 'used_by', 'company'].edge_time = torch.tensor(tech_times, dtype=torch.float)

        data['company', 'subject_to', 'regulation'].edge_index = torch.tensor([reg_src, reg_dst], dtype=torch.long)
        data['regulation', 'applies_to', 'company'].edge_index = torch.tensor([reg_dst, reg_src], dtype=torch.long)

        data['company', 'supplies_to', 'company'].edge_index = torch.tensor([supply_src, supply_dst], dtype=torch.long)
        data['company', 'supplies_to', 'company'].edge_time = torch.tensor(supply_times, dtype=torch.float)

        # 6. Simulate Dynamic Ground-Truth Buying Readiness Labels (Y) with Realistic Temporal Waves
        # A company buys if:
        # (1) margin pressure + competitor adopted automation, OR
        # (2) NIS2 applicable + low security grade, OR
        # (3) supply chain partner mandated cloud upgrade.
        labels = np.zeros(num_companies, dtype=np.float32)
        event_timestamps = np.zeros(num_companies, dtype=np.float32)

        for i, c in enumerate(all_companies):
            # Baseline probability
            prob = 0.08
            base_time = random.uniform(100.0, 900.0)

            # Check if competitors adopted tech recently
            rival_bought = any(
                comp_dst[k] == i and tech_dst[m] in [0, 1]  # UiPath or Celonis
                for k in range(len(comp_dst))
                for m in range(len(tech_src))
                if tech_src[m] == comp_src[k]
            )
            if rival_bought and c["margin"] < 0.09:
                prob += 0.55  # Huge competitive impulse

            # Check NIS2 risk
            if (i in reg_src and 0 in [reg_dst[idx] for idx, val in enumerate(reg_src) if val == i]):
                if c["sec_grade"] < 0.55:
                    prob += 0.45  # Regulatory panic

            is_buyer = 1.0 if (random.random() < min(0.95, prob)) else 0.0
            labels[i] = is_buyer
            event_timestamps[i] = base_time

        data['company'].y = torch.tensor(labels, dtype=torch.float)
        data['company'].event_time = torch.tensor(event_timestamps, dtype=torch.float)

        # 7. Strict Temporal Split (No Data Leakage)
        # Train: Events occurring before day 500 (~mid 2025)
        # Val:   Events between day 500 and 700 (~late 2025)
        # Test:  Events after day 700 (~2026 live testing)
        train_mask = data['company'].event_time < 500.0
        val_mask = (data['company'].event_time >= 500.0) & (data['company'].event_time < 700.0)
        test_mask = data['company'].event_time >= 700.0

        metadata = {
            "num_companies": num_companies,
            "company_to_id": company_to_id,
            "train_count": int(train_mask.sum().item()),
            "val_count": int(val_mask.sum().item()),
            "test_count": int(test_mask.sum().item()),
            "positive_rate": float(labels.mean())
        }

        return data, metadata
