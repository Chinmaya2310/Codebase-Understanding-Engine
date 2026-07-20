"""
Converts a NetworkX code graph + per-node text embeddings into dense
PyTorch tensors suitable for `CodeGNN`.

Usage
-----
>>> from backend.ml.gnn.dataset import CodeGraphDataset
>>> dataset = CodeGraphDataset(graph, node_embeddings)
>>> features, adjacency = dataset.to_tensors()
"""
from __future__ import annotations

import networkx as nx
import torch


class CodeGraphDataset:
    """
    Wraps a code knowledge graph and its node embeddings.

    Parameters
    ----------
    graph:
        The `networkx.MultiDiGraph` produced by `GraphService.build_graph`.
    node_embeddings:
        Mapping of node qualified-name → embedding vector (list of floats).
        Nodes without an entry receive a zero vector.
    """

    def __init__(
        self,
        graph: nx.MultiDiGraph,
        node_embeddings: dict[str, list[float]],
    ) -> None:
        self.graph           = graph
        self.node_ids        = list(graph.nodes())
        self.id_to_index     = {nid: i for i, nid in enumerate(self.node_ids)}
        self.node_embeddings = node_embeddings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_tensors(
        self,
        embedding_dim: int = 384,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Build the feature matrix and adjacency matrix.

        Returns
        -------
        features : torch.Tensor  shape (N, embedding_dim)
        adjacency: torch.Tensor  shape (N, N)
        """
        n        = len(self.node_ids)
        features = torch.zeros((n, embedding_dim), dtype=torch.float32)

        for node_id, idx in self.id_to_index.items():
            vec = self.node_embeddings.get(node_id)
            if vec:
                t = torch.tensor(vec[:embedding_dim], dtype=torch.float32)
                features[idx, : len(t)] = t

        adjacency = torch.zeros((n, n), dtype=torch.float32)
        for u, v in self.graph.edges():
            ui = self.id_to_index.get(u)
            vi = self.id_to_index.get(v)
            if ui is not None and vi is not None:
                adjacency[ui, vi] = 1.0
                adjacency[vi, ui] = 1.0  # symmetrise for undirected message passing

        return features, adjacency

    def num_nodes(self) -> int:
        return len(self.node_ids)

    def num_edges(self) -> int:
        return self.graph.number_of_edges()
