"""
CodeGNN: a 2-layer Graph Convolutional Network for code understanding.

Takes:
  - Initial node features  (N, input_dim)   — text embeddings from sentence-transformers
  - Adjacency matrix       (N, N)            — from the code knowledge graph

Produces:
  - Structure-aware node embeddings  (N, output_dim)

These refined embeddings encode not just what a function *says* in its
docstring, but also *who calls it* and *what it calls* — making similarity
search and dead-code detection more accurate.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from backend.ml.gnn.layers import GCNLayer, normalise_adjacency


class CodeGNN(nn.Module):
    """
    Two-layer GCN with residual projection.

    Architecture:
      input_dim  → hidden_dim  (GCNLayer + ReLU + dropout)
      hidden_dim → output_dim  (GCNLayer + ReLU)
      output_dim → output_dim  (L2 normalise)
    """

    def __init__(
        self,
        input_dim:  int   = 384,
        hidden_dim: int   = 256,
        output_dim: int   = 128,
        dropout:    float = 0.1,
    ) -> None:
        super().__init__()
        self.layer1 = GCNLayer(input_dim,  hidden_dim, dropout=dropout)
        self.layer2 = GCNLayer(hidden_dim, output_dim, dropout=0.0)

    def forward(
        self,
        features:  torch.Tensor,
        adjacency: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            features:  (N, input_dim)  — raw node embeddings.
            adjacency: (N, N)          — raw (unnormalised) adjacency matrix.

        Returns:
            L2-normalised node embeddings  (N, output_dim).
        """
        norm_adj = normalise_adjacency(adjacency)
        h = self.layer1(features,  norm_adj)
        h = self.layer2(h,         norm_adj)
        return F.normalize(h, dim=-1)

    @torch.no_grad()
    def embed(
        self,
        features:  torch.Tensor,
        adjacency: torch.Tensor,
    ) -> torch.Tensor:
        """Inference-mode forward pass (no gradient tracking, eval mode)."""
        self.eval()
        return self.forward(features, adjacency)
