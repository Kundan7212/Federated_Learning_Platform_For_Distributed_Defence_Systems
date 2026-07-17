"""
FedAvg — McMahan et al. 2017 [Paper]
Synchronous weighted averaging of client updates.
"""
from __future__ import annotations
import copy
from typing import Dict, List, Optional, Tuple
from fl_engine.algorithms.base import BaseAlgorithm, MetricsCallback
from fl_engine.client import FLClient


def fedavg_aggregate(
    global_state: Dict,
    client_updates: List[Tuple[Dict, int]],
) -> Dict:
    
    total_samples = sum(n for _, n in client_updates)
    aggregated = {k: v.cpu().float() * 0.0 for k, v in copy.deepcopy(global_state).items()}

    for client_state, num_samples in client_updates:
        weight = num_samples / total_samples
        for key in aggregated:
            aggregated[key] += weight * client_state[key].float().cpu()

    return aggregated


class FedAvg(BaseAlgorithm):

    def __init__(self, cfg: dict, callback: Optional[MetricsCallback] = None):
        super().__init__(cfg, callback)

    def run(
        self,
        client_loaders: List,
        test_loader,
        client_sizes: List[int],
    ) -> Tuple[List[float], List[float]]:
        global_model = self._build_global_model()
        clients = [
            FLClient(i, loader, size, self.cfg, self._dp)
            for i, (loader, size) in enumerate(zip(client_loaders, client_sizes))
        ]

        round_accuracies: List[float] = []
        round_losses: List[float] = []
        rounds = self.cfg.get("rounds", 5)

        for round_num in range(1, rounds + 1):
            global_weights = self._deep_copy_state(global_model)
            client_updates: List[Tuple[Dict, int]] = []

            for client in clients:
                client.load_global_weights(global_weights)
                updated_weights, num_samples, _ = client.local_train()
                client_updates.append((updated_weights, num_samples))

            new_weights = self._maybe_secure_aggregate(
                client_updates,
                lambda: fedavg_aggregate(global_weights, client_updates),
            )
            new_weights = self._maybe_dp_noise(new_weights)
            global_model.load_state_dict(new_weights)

            test_loss, test_acc = self._evaluate(global_model, test_loader)
            round_accuracies.append(test_acc)
            round_losses.append(test_loss)

            self._emit(
                round_num=round_num,
                accuracy=test_acc,
                loss=test_loss,
                algorithm="fedavg",
            )

        return round_accuracies, round_losses
