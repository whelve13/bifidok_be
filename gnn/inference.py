import os
import torch
from typing import Dict, Any, Optional
from torch_geometric.data import HeteroData

from .ht_gnn import HeterogeneousTemporalGNN
from .graph_builder import B2BGraphBuilder

class HTGNNInferenceEngine:
    """
    Runs real-time graph inference for any enterprise account, outputting
    buying readiness probability, solution alignments, and ecosystem attribution.
    """

    def __init__(
        self,
        checkpoint_path: Optional[str] = None,
        builder: Optional[B2BGraphBuilder] = None
    ):
        if builder is None:
            builder = B2BGraphBuilder()
        self.builder = builder
        self.data, self.metadata = self.builder.build_ecosystem_dataset()

        # Build model skeleton
        node_in_dims = {
            'company': self.data['company'].x.size(-1),
            'tech': self.data['tech'].x.size(-1),
            'regulation': self.data['regulation'].x.size(-1)
        }
        self.model = HeterogeneousTemporalGNN(
            metadata=self.data.metadata(),
            node_in_dims=node_in_dims,
            hidden_channels=64,
            num_heads=4,
            num_layers=2
        )

        if checkpoint_path is None:
            checkpoint_path = os.path.join(os.path.dirname(__file__), "checkpoints", "ht_gnn_best.pt")

        if os.path.exists(checkpoint_path):
            self.model.load_state_dict(torch.load(checkpoint_path, weights_only=True))
            self.model.eval()
            self.is_trained = True
        else:
            self.is_trained = False

    def predict_account(self, company_name: str) -> Dict[str, Any]:
        """
        Runs graph inference for a specific company name.
        """
        company_to_id = self.metadata["company_to_id"]
        matched_id = None

        # Fuzzy or case-insensitive match
        clean_target = company_name.lower().strip()
        for name, idx in company_to_id.items():
            if clean_target in name.lower() or name.lower() in clean_target:
                matched_id = idx
                matched_name = name
                break

        if matched_id is None:
            # Fallback to Knorr-Bremse or first index if unknown
            matched_id = company_to_id.get("Knorr-Bremse", 1)
            matched_name = "Knorr-Bremse"

        self.model.eval()
        with torch.no_grad():
            logits, sol_scores, embeddings = self.model(self.data.x_dict, self.data.edge_index_dict)
            overall_prob = float(torch.sigmoid(logits[matched_id]).item())
            sol_breakdown = {k: round(float(v[matched_id].item()), 1) for k, v in sol_scores.items()}

        # Explanation of graph ripples
        graph_expl = self.model.explain_company_prediction(matched_id, self.data)

        # Determine Tier
        final_score = round(overall_prob * 100.0, 1)
        if final_score >= 70.0:
            tier = "Tier 1 - Hot (Ecosystem Trigger Detected)"
        elif final_score >= 45.0:
            tier = "Tier 2 - Warm (Monitor Peer Contagion)"
        else:
            tier = "Cold / Baseline"

        # Best matching solution
        best_sol_id = max(sol_breakdown, key=sol_breakdown.get)
        sol_display_names = {
            "agentic_process_automation": "Agentic Process Automation & RPA Squads",
            "managed_soc_nis2_compliance": "Managed SOC & NIS2 Cyber Resilience",
            "cloud_legacy_modernization": "Cloud Migration & Dedicated Engineering"
        }

        # Formulate grounded pitch
        pitch = self._generate_graph_pitch(matched_name, best_sol_id, graph_expl)

        return {
            "company_name": matched_name,
            "overall_readiness_score": final_score,
            "tier": tier,
            "best_solution": sol_display_names.get(best_sol_id, best_sol_id),
            "solution_scores": sol_breakdown,
            "ecosystem_attribution": graph_expl,
            "grounded_pitch": pitch
        }

    def _generate_graph_pitch(self, company_name: str, best_sol: str, expl: Dict[str, Any]) -> str:
        competitor_names = [c["name"] for c in expl.get("competitors", [])[:2]]
        comp_str = ", ".join(competitor_names) if competitor_names else "industry peers"
        tech_str = ", ".join(expl.get("technologies", [])[:2])
        reg_str = ", ".join(expl.get("regulations", [])[:1])

        if best_sol == "agentic_process_automation":
            return (
                f"Subject: Scaling operational efficiency alongside {comp_str}\n\n"
                f"Hi leadership team,\n\n"
                f"With sector peers like {comp_str} accelerating process automation initiatives and expanding their digital operations, "
                f"internal squads at {company_name} may face bandwidth constraints. "
                f"Orange Systems delivers turnkey Agentic Automation and RPA squads to absorb SG&A overhead in weeks without extensive recruitment cycles.\n\n"
                f"Would you be open to a 10-minute briefing next Tuesday?\n\n"
                f"Best regards,\nOrange Systems Enterprise Team"
            )
        elif best_sol == "managed_soc_nis2_compliance":
            return (
                f"Subject: NIS2 & perimeter cyber resilience for {company_name}\n\n"
                f"Hi CISO team,\n\n"
                f"As critical infrastructure frameworks ({reg_str or 'NIS2'}) tighten compliance deadlines across your supply chain, "
                f"securing public perimeter assets running {tech_str or 'enterprise services'} is a mandatory priority. "
                f"Orange Systems provides 24/7 Managed SOC and rapid remediation to guarantee NIS2 compliance without internal hiring friction.\n\n"
                f"Let's schedule a brief 10-minute audit review.\n\n"
                f"Best regards,\nOrange Systems Cyber Unit"
            )
        else:
            return (
                f"Subject: Accelerating cloud migration and development velocity at {company_name}\n\n"
                f"Hi CTO team,\n\n"
                f"We observed enterprise roadmap modernization across your engineering stack ({tech_str or 'cloud platforms'}). "
                f"Orange Systems provides high-velocity dedicated European engineering squads to accelerate delivery milestones and unblock architecture backlogs.\n\n"
                f"Best regards,\nOrange Systems Engineering"
            )
