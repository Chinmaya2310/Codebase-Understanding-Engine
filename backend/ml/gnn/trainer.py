"""
Self-supervised GNN trainer using contrastive link-prediction loss.

The model learns embeddings such that:
  - connected node pairs (positive) have high dot-product similarity
  - random unconnected pairs (negative) have low similarity

This requires NO labelled data — the graph structure itself provides
the training signal.  Works on any repository out of the box.
"""
from __future__ import annotations

import logging
import random

import torch
import torch.nn.functional as F

from backend.ml.gnn.dataset import CodeGraphDataset
from backend.ml.gnn.model import CodeGNN

logger = logging.getLogger(__name__)


class GNNTrainer:
    """Trains `CodeGNN` via contrastive link-prediction."""

    def __init__(
        self,
        model: CodeGNN,
        learning_rate: float = 1e-3,
        weight_decay:  float = 1e-5,
    ) -> None:
        self.model     = model
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train_epoch(
        self,
        dataset:       CodeGraphDataset,
        embedding_dim: int = 384,
        neg_ratio:     int = 2,
    ) -> float:
        """
        One training epoch.

        Returns
        -------
        float
            Mean binary cross-entropy loss for this epoch.
        """
        features, adjacency = dataset.to_tensors(embedding_dim)
        edges = list(dataset.graph.edges())
        if not edges:
            return 0.0

        n = features.shape[0]
        self.model.train()
        self.optimizer.zero_grad()

        embeddings = self.model(features, adjacency)  # (N, output_dim)

        # Positive pairs
        pos_u, pos_v = [], []
        for u, v in edges:
            ui = dataset.id_to_index.get(u)
            vi = dataset.id_to_index.get(v)
            if ui is not None and vi is not None:
                pos_u.append(ui)
                pos_v.append(vi)

        if not pos_u:
            return 0.0

        pos_u_t = torch.tensor(pos_u, dtype=torch.long)
        pos_v_t = torch.tensor(pos_v, dtype=torch.long)
        pos_scores = (embeddings[pos_u_t] * embeddings[pos_v_t]).sum(dim=-1)

        # Negative pairs (random sampling)
        neg_u = [random.randrange(n) for _ in range(len(pos_u) * neg_ratio)]
        neg_v = [random.randrange(n) for _ in range(len(pos_u) * neg_ratio)]
        neg_u_t = torch.tensor(neg_u, dtype=torch.long)
        neg_v_t = torch.tensor(neg_v, dtype=torch.long)
        neg_scores = (embeddings[neg_u_t] * embeddings[neg_v_t]).sum(dim=-1)

        scores = torch.cat([pos_scores, neg_scores])
        labels = torch.cat([
            torch.ones_like(pos_scores),
            torch.zeros_like(neg_scores),
        ])
        loss = F.binary_cross_entropy_with_logits(scores, labels)

        loss.backward()
        self.optimizer.step()
        return float(loss.item())

    def train(
        self,
        dataset:       CodeGraphDataset,
        epochs:        int = 20,
        embedding_dim: int = 384,
    ) -> list[float]:
        """
        Train for *epochs* epochs.

        Returns
        -------
        list[float]
            Per-epoch loss history.
        """
        history: list[float] = []
        for epoch in range(1, epochs + 1):
            loss = self.train_epoch(dataset, embedding_dim=embedding_dim)
            history.append(loss)
            if epoch == 1 or epoch % 5 == 0:
                logger.info(
                    "GNN epoch %d/%d  loss=%.4f", epoch, epochs, loss
                )
        return history

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------

    @torch.no_grad()
    def get_refined_embeddings(
        self,
        dataset:       CodeGraphDataset,
        embedding_dim: int = 384,
    ) -> dict[str, list[float]]:
        """
        Return structure-aware embeddings for all nodes as a plain dict
        (node_id → list[float]).  Safe to serialise / store.
        """
        self.model.eval()
        features, adjacency = dataset.to_tensors(embedding_dim)
        refined = self.model.embed(features, adjacency)   # (N, output_dim)
        return {
            node_id: refined[idx].tolist()
            for node_id, idx in dataset.id_to_index.items()
        }
