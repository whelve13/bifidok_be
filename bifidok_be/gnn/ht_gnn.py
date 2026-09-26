import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import HGTConv, Linear
from typing import Dict, List, Any, Tuple, Optional

class HeterogeneousTemporalGNN(nn.Module):
    """
    Heterogeneous Temporal Graph Neural Network (HT-GNN) for B2B Buying Intent Prediction.
    
    Processes multi-relational enterprise graphs (competitors, technologies, regulations, supply chain)
    with attention-weighted message passing across time.
    """

    def __init__(
        self,
        metadata: Tuple[List[str], List[Tuple[str, str, str]]],
        node_in_dims: Dict[str, int],
        hidden_channels: int = 64,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.2
    ):
        super().__init__()
        self.hidden_channels = hidden_channels
        self.dropout = dropout

        # 1. Heterogeneous Node Feature Projectors
        # Projects each node type's distinct feature size into uniform hidden_channels
        self.proj_dict = nn.ModuleDict()
        for node_type, in_dim in node_in_dims.items():
            self.proj_dict[node_type] = nn.Sequential(
                Linear(in_dim, hidden_channels),
                nn.LayerNorm(hidden_channels),
                nn.ReLU()
            )

        # 2. HGT Layers (Heterogeneous Graph Transformer)
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(
                in_channels=hidden_channels,
                out_channels=hidden_channels,
                metadata=metadata,
                heads=num_heads
            )
            self.convs.append(conv)
            self.norms.append(nn.LayerNorm(hidden_channels))

        # 3. Overall Buying Readiness Prediction Head (Company Level)
        self.readiness_head = nn.Sequential(
            Linear(hidden_channels, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            Linear(32, 1)
        )

        # 4. Solution-Specific Affinity Projections
        # Projects company representation into alignment scores for 3 core Orange Systems solutions
        self.solution_heads = nn.ModuleDict({
            "agentic_process_automation": Linear(hidden_channels, 1),
            "managed_soc_nis2_compliance": Linear(hidden_channels, 1),
            "cloud_legacy_modernization": Linear(hidden_channels, 1)
        })

    def forward(
        self,
        x_dict: Dict[str, torch.Tensor],
        edge_index_dict: Dict[Tuple[str, str, str], torch.Tensor]
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor], torch.Tensor]:
        """
        Forward pass.
        Returns:
            - logits: raw logits for binary buying readiness [num_companies]
            - solution_scores: dictionary of solution alignment probabilities [0.0 - 100.0]
            - embeddings: latent node representations for companies [num_companies, hidden_channels]
        """
        # Step 1: Project heterogeneous features
        h_dict = {}
        for node_type, x in x_dict.items():
            h_dict[node_type] = self.proj_dict[node_type](x)

        # Step 2: Message Passing across Heterogeneous Graph
        for conv, norm in zip(self.convs, self.norms):
            h_next = conv(h_dict, edge_index_dict)
            # Residual connection and layer norm
            h_dict = {
                node_type: norm(F.relu(h_next[node_type]) + h_dict[node_type])
                for node_type in h_dict.keys()
            }

        company_emb = h_dict['company']

        # Step 3: Compute Overall Readiness Logits
        logits = self.readiness_head(company_emb).squeeze(-1)

        # Step 4: Compute Solution-Specific Alignments (0 to 100 scale)
        solution_scores = {}
        for sol_id, head in self.solution_heads.items():
            sol_logit = head(company_emb).squeeze(-1)
            solution_scores[sol_id] = torch.sigmoid(sol_logit) * 100.0

        return logits, solution_scores, company_emb

    def explain_company_prediction(
        self,
        company_idx: int,
        data: Any,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Extracts multi-relational graph neighbors (competitors, tech, regulations)
        that influenced this company's embedding.
        """
        explanations = {
            "target_company": data['company'].names[company_idx],
            "competitors": [],
            "technologies": [],
            "regulations": [],
            "suppliers": []
        }

        # Check competitors
        comp_edges = data['company', 'competes_with', 'company'].edge_index
        src, dst = comp_edges[0], comp_edges[1]
        mask = (dst == company_idx)
        neighbor_comp_indices = src[mask].tolist()
        for n_idx in neighbor_comp_indices[:top_k]:
            explanations["competitors"].append({
                "name": data['company'].names[n_idx],
                "buyer_label": bool(data['company'].y[n_idx].item() > 0.5)
            })

        # Check technologies
        tech_edges = data['company', 'uses_tech', 'tech'].edge_index
        t_src, t_dst = tech_edges[0], tech_edges[1]
        t_mask = (t_src == company_idx)
        neighbor_tech_indices = t_dst[t_mask].tolist()
        for t_idx in neighbor_tech_indices:
            explanations["technologies"].append(data['tech'].names[t_idx])

        # Check regulations
        reg_edges = data['company', 'subject_to', 'regulation'].edge_index
        r_src, r_dst = reg_edges[0], reg_edges[1]
        r_mask = (r_src == company_idx)
        neighbor_reg_indices = r_dst[r_mask].tolist()
        for r_idx in neighbor_reg_indices:
            explanations["regulations"].append(data['regulation'].names[r_idx])

        return explanations
