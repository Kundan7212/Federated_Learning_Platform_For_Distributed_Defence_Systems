"""
Byzantine-Robust Aggregation Strategies.
I implemented Krum, Multi-Krum, Trimmed Mean, and Coordinate Median for defence against corrupt model updates.
"""
from __future__ import annotations
import copy
from enum import Enum
from typing import Dict, List, Tuple
import torch


class DefenseStrategy(str, Enum):
    FEDAVG       = "fedavg"
    KRUM         = "krum"
    MULTI_KRUM   = "multi_krum"
    TRIMMED_MEAN = "trimmed_mean"
    MEDIAN       = "median"


def _flatten(weights: Dict[str, torch.Tensor]) -> torch.Tensor:
    return torch.cat([v.float().cpu().reshape(-1) for v in weights.values()])


def _unflatten(
    flat: torch.Tensor,
    reference: Dict[str, torch.Tensor],
) -> Dict[str, torch.Tensor]:
    result = {}
    idx = 0
    for k, v in reference.items():
        size = v.numel()
        result[k] = flat[idx: idx + size].reshape(v.shape).to(v.dtype)
        idx += size
    return result


def fedavg_aggregate(
    client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
) -> Dict[str, torch.Tensor]:
    total = sum(n for _, n in client_updates)
    keys  = list(client_updates[0][0].keys())
    agg   = {k: client_updates[0][0][k].float() * 0.0 for k in keys}
    for w, n in client_updates:
        for k in keys:
            agg[k] += (n / total) * w[k].float().cpu()
    return agg


def krum_aggregate(
    client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    num_adversaries: int = 1,
    multi: bool = False,
    multi_k: int = None,
) -> Dict[str, torch.Tensor]:
    
    n = len(client_updates)
    f = min(num_adversaries, n - 2)  
    m = n - f - 2                    

    if m <= 0:
        return fedavg_aggregate(client_updates)

    vectors = [_flatten(w) for w, _ in client_updates]

    scores = []
    for i in range(n):
        dists = sorted(
            (torch.norm(vectors[i] - vectors[j]) ** 2).item()
            for j in range(n) if j != i
        )
        scores.append(sum(dists[:m]))

    if not multi:
        best_idx = int(min(range(n), key=lambda i: scores[i]))
        return copy.deepcopy(client_updates[best_idx][0])

    k = multi_k if multi_k else max(1, n - f)
    selected_indices = sorted(range(n), key=lambda i: scores[i])[:k]
    selected = [(client_updates[i][0], client_updates[i][1]) for i in selected_indices]
    return fedavg_aggregate(selected)


def trimmed_mean_aggregate(
    client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    trim_fraction: float = 0.1,
) -> Dict[str, torch.Tensor]:
    
    n = len(client_updates)
    trim_count = max(1, int(n * trim_fraction))

    keys    = list(client_updates[0][0].keys())
    vectors = [_flatten(w) for w, _ in client_updates]
    stacked = torch.stack(vectors, dim=0)  # (n, d)

    sorted_vals, _ = stacked.sort(dim=0)
    trimmed = sorted_vals[trim_count: n - trim_count]
    if trimmed.shape[0] == 0:
        trimmed = sorted_vals  # fallback: no trimming if too few clients
    mean_vec = trimmed.mean(dim=0)

    return _unflatten(mean_vec, client_updates[0][0])


def coordinate_median_aggregate(
    client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
) -> Dict[str, torch.Tensor]:
    
    vectors = [_flatten(w) for w, _ in client_updates]
    stacked = torch.stack(vectors, dim=0)
    median_vec = stacked.median(dim=0).values
    return _unflatten(median_vec, client_updates[0][0])


class RobustAggregator:
    
    def __init__(
        self,
        strategy: DefenseStrategy = DefenseStrategy.FEDAVG,
        num_adversaries: int = 1,
        trim_fraction: float = 0.1,
        multi_krum_k: int = None,
    ):
        self.strategy        = DefenseStrategy(strategy)
        self.num_adversaries = num_adversaries
        self.trim_fraction   = trim_fraction
        self.multi_krum_k    = multi_krum_k

    def aggregate(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> Dict[str, torch.Tensor]:
        if len(client_updates) == 0:
            raise ValueError("No client updates to aggregate")

        s = self.strategy
        if s == DefenseStrategy.FEDAVG:
            return fedavg_aggregate(client_updates)
        elif s == DefenseStrategy.KRUM:
            return krum_aggregate(client_updates, self.num_adversaries, multi=False)
        elif s == DefenseStrategy.MULTI_KRUM:
            return krum_aggregate(
                client_updates, self.num_adversaries,
                multi=True, multi_k=self.multi_krum_k
            )
        elif s == DefenseStrategy.TRIMMED_MEAN:
            return trimmed_mean_aggregate(client_updates, self.trim_fraction)
        elif s == DefenseStrategy.MEDIAN:
            return coordinate_median_aggregate(client_updates)
        raise ValueError(f"Unknown defense strategy: {self.strategy}")
