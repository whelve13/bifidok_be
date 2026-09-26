import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score
from typing import Dict, Any, Tuple, Optional
from torch_geometric.data import HeteroData

from .ht_gnn import HeterogeneousTemporalGNN

class HTGNNTrainer:
    """
    Manages training, temporal validation, and test evaluation for the B2B HT-GNN.
    """

    def __init__(
        self,
        model: HeterogeneousTemporalGNN,
        data: HeteroData,
        lr: float = 0.003,
        weight_decay: float = 1e-4,
        checkpoint_dir: Optional[str] = None
    ):
        self.model = model
        self.data = data
        self.lr = lr
        self.weight_decay = weight_decay

        if checkpoint_dir is None:
            checkpoint_dir = os.path.join(os.path.dirname(__file__), "checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        self.checkpoint_path = os.path.join(checkpoint_dir, "ht_gnn_best.pt")

        # Class balance weighting for rare B2B conversion events
        y_train = self.data['company'].y[self.data['company'].event_time < 500.0]
        pos_count = (y_train == 1.0).sum().item()
        neg_count = (y_train == 0.0).sum().item()
        weight_val = neg_count / max(1.0, pos_count)
        self.pos_weight = torch.tensor([weight_val], dtype=torch.float)

        self.criterion = nn.BCEWithLogitsLoss(pos_weight=self.pos_weight)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=self.lr, weight_decay=self.weight_decay)
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=80)

    def train(self, epochs: int = 80, verbose: bool = True) -> Dict[str, Any]:
        """
        Executes training with temporal validation early monitoring.
        """
        train_mask = self.data['company'].event_time < 500.0
        val_mask = (self.data['company'].event_time >= 500.0) & (self.data['company'].event_time < 700.0)

        best_val_auc = 0.0
        history = {"train_loss": [], "val_auc": []}

        for epoch in range(1, epochs + 1):
            self.model.train()
            self.optimizer.zero_grad()

            logits, _, _ = self.model(self.data.x_dict, self.data.edge_index_dict)
            loss = self.criterion(logits[train_mask], self.data['company'].y[train_mask])
            loss.backward()
            self.optimizer.step()
            self.scheduler.step()

            history["train_loss"].append(float(loss.item()))

            # Validation step
            val_auc, _, _ = self._evaluate_split(val_mask)
            history["val_auc"].append(val_auc)

            if val_auc > best_val_auc:
                best_val_auc = val_auc
                torch.save(self.model.state_dict(), self.checkpoint_path)

            if verbose and (epoch % 10 == 0 or epoch == epochs):
                print(f"Epoch {epoch:03d} | Train Loss: {loss.item():.4f} | Val ROC-AUC: {val_auc:.3f} | Best Val: {best_val_auc:.3f}")

        # Load best checkpoint
        if os.path.exists(self.checkpoint_path):
            self.model.load_state_dict(torch.load(self.checkpoint_path, weights_only=True))

        return {"best_val_auc": best_val_auc, "history": history}

    def evaluate_test(self) -> Dict[str, Any]:
        """
        Strict evaluation on the held-out future test window (Events >= Day 700 / 2026).
        """
        test_mask = self.data['company'].event_time >= 700.0
        roc_auc, pr_auc, metrics = self._evaluate_split(test_mask)

        # Precision@K ranking metrics
        self.model.eval()
        with torch.no_grad():
            logits, _, _ = self.model(self.data.x_dict, self.data.edge_index_dict)
            probs = torch.sigmoid(logits[test_mask]).cpu().numpy()
            y_true = self.data['company'].y[test_mask].cpu().numpy()
            test_names = [self.data['company'].names[i] for i in range(len(test_mask)) if test_mask[i]]

        # Precision@5 and Precision@10
        sorted_indices = np.argsort(-probs)
        top5_idx = sorted_indices[:5]
        top10_idx = sorted_indices[:10]

        p_at_5 = float(y_true[top5_idx].mean()) if len(top5_idx) > 0 else 0.0
        p_at_10 = float(y_true[top10_idx].mean()) if len(top10_idx) > 0 else 0.0

        top_leads = []
        for rank, idx in enumerate(top10_idx, 1):
            top_leads.append({
                "rank": rank,
                "company": test_names[idx],
                "predicted_prob": round(float(probs[idx]), 3),
                "actual_ground_truth": bool(y_true[idx] > 0.5)
            })

        results = {
            "test_roc_auc": round(float(roc_auc), 3),
            "test_pr_auc": round(float(pr_auc), 3),
            "precision_at_5": round(p_at_5 * 100.0, 1),
            "precision_at_10": round(p_at_10 * 100.0, 1),
            "test_account_count": len(y_true),
            "test_actual_buyer_count": int(y_true.sum()),
            "top_prioritized_leads": top_leads
        }
        return results

    def _evaluate_split(self, mask: torch.Tensor) -> Tuple[float, float, Dict[str, Any]]:
        self.model.eval()
        with torch.no_grad():
            logits, _, _ = self.model(self.data.x_dict, self.data.edge_index_dict)
            probs = torch.sigmoid(logits[mask]).cpu().numpy()
            y_true = self.data['company'].y[mask].cpu().numpy()

        if len(np.unique(y_true)) < 2:
            return 0.5, 0.5, {}

        roc_auc = float(roc_auc_score(y_true, probs))
        pr_auc = float(average_precision_score(y_true, probs))
        return roc_auc, pr_auc, {"probs": probs, "y_true": y_true}
