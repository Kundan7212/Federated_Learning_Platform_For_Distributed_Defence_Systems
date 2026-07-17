"""
Secure Aggregation via Additive Secret Sharing (masking scheme).
In this implementation, I simulated the protocol locally (no network),
which demonstrates correctness. In a real system, clients would exchange
masks via an authenticated key agreement (e.g., Diffie-Hellman).
"""
from __future__ import annotations
import copy
from typing import Dict, List, Tuple
import torch


def _generate_mask(ref_tensor: torch.Tensor, scale: float = 1e-3) -> torch.Tensor:
    return torch.randn_like(ref_tensor.float()) * scale


class SecureAggregator:

    def __init__(self, num_clients: int, mask_scale: float = 1e-3):
        self.num_clients = num_clients
        self.mask_scale  = mask_scale

    def mask_updates(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> List[Tuple[Dict[str, torch.Tensor], int]]:
        
        n = len(client_updates)
        if n == 0:
            return client_updates

        keys = list(client_updates[0][0].keys())

        total_weight = sum(w for _, w in client_updates)
        if total_weight <= 0:
            raise ValueError(
                "Secure aggregation requires a positive total aggregation weight"
            )
        for idx, (_, w) in enumerate(client_updates):
            if w <= 0:
                raise ValueError(
                    f"Secure aggregation requires a positive aggregation weight "
                    f"for every client (client {idx} has weight {w})"
                )

        masks: List[List[Dict[str, torch.Tensor]]] = []
        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append({})  
                else:
                    mask = {
                        k: _generate_mask(client_updates[i][0][k].float(), self.mask_scale)
                        for k in keys
                    }
                    row.append(mask)
            masks.append(row)

        masked_updates = []
        for i, (weights, agg_weight) in enumerate(client_updates):
            wi = agg_weight / total_weight

            net_mask = {k: torch.zeros_like(weights[k].float()) for k in keys}
            for j in range(n):
                if i == j:
                    continue
                for k in keys:
                    net_mask[k] = net_mask[k] + masks[i][j][k]  
                    net_mask[k] = net_mask[k] - masks[j][i][k]  

            masked = {}
            for k in keys:
                masked[k] = weights[k].float().cpu().clone() + net_mask[k] / wi
            masked_updates.append((masked, agg_weight))

        return masked_updates

    def aggregate(
        self,
        masked_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> Dict[str, torch.Tensor]:
        
        total_samples = sum(n for _, n in masked_updates)
        keys = list(masked_updates[0][0].keys())

        result = {k: masked_updates[0][0][k].float() * 0.0 for k in keys}

        for weights, num_samples in masked_updates:
            w = num_samples / total_samples
            for k in keys:
                result[k] += w * weights[k].float()

        return result


class SecureAggregationProtocol:

    def __init__(self, cfg: dict):
        sa_cfg = cfg.get("secure_aggregation", {})
        self.enabled    = sa_cfg.get("enabled", False)
        self.num_shares = sa_cfg.get("num_shares", 3)
        self._aggregator: SecureAggregator = None

    def setup(self, num_clients: int) -> None:
        self._aggregator = SecureAggregator(num_clients=num_clients)

    def process(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> Tuple[List[Tuple[Dict, int]], bool]:
        
        if not self.enabled or self._aggregator is None:
            return client_updates, False

        masked = self._aggregator.mask_updates(client_updates)
        return masked, True

    def aggregate_secure(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> Dict[str, torch.Tensor]:
        if self._aggregator is None:
            raise RuntimeError("Call setup() before aggregate_secure()")
        masked = self._aggregator.mask_updates(client_updates)
        return self._aggregator.aggregate(masked)
