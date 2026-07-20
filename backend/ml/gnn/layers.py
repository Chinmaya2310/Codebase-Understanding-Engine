"""
Graph Convolutional Network layer — pure PyTorch, no torch-geometric needed.

Implements H' = ReLU( D^{-1/2} (A + I) D^{-1/2}  H  W )
which is the standard GCN propagation rule from Kipf & Welling (2017).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class GCNLayer(nn.Module):
    """Single GCN message-passing layer with optional dropout."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        dropout: float = 0.1,
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.linear  = nn.Linear(in_features, out_features, bias=bias)
        self.dropout = nn.Dropout(p=dropout)

    def forward(self, x: torch.Tensor, norm_adj: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x:        Node features  (N, in_features).
            norm_adj: Normalised adjacency with self-loops  (N, N).

        Returns:
            Updated node features  (N, out_features).
        """
        x = self.dropout(x)
        x = norm_adj @ x          # neighbourhood aggregation
        x = self.linear(x)        # linear projection
        return F.relu(x)           # non-linearity


def normalise_adjacency(adj: torch.Tensor) -> torch.Tensor:
    """
    Compute  D^{-1/2} (A + I) D^{-1/2}.

    Args:
        adj: Raw (unnormalised) adjacency matrix  (N, N).

    Returns:
        Symmetrically-normalised adjacency with self-loops, same shape.
    """
    n   = adj.size(0)
    adj = adj + torch.eye(n, device=adj.device)
    deg = adj.sum(dim=1)
    d   = torch.pow(deg.clamp(min=1e-8), -0.5)
    D   = torch.diag(d)
    return D @ adj @ D
