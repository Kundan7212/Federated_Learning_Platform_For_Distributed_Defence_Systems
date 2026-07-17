"""
FedAsync — Xie et al. 2019 [Paper]
Asynchronous FL with staleness-aware weighting.
Discrete-event simulation via heapq.
"""
from __future__ import annotations
import copy
import heapq
import itertools
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from fl_engine.algorithms.base import BaseAlgorithm, MetricsCallback
from fl_engine.client import FLClient

logger = logging.getLogger(__name__)


def staleness_weight(staleness: int, mode: str = "inverse") -> float:
    staleness = max(staleness, 0)
    if mode == "none":
        return 1.0
    if mode == "inverse":
        return 1.0 / (1.0 + staleness)
    raise ValueError(f"Unknown staleness mode: '{mode}'")


def fedasync_update(
    global_state: Dict,
    client_state: Dict,
    alpha: float,
) -> Dict:
    """Convex combination: (1-α)·global + α·client."""
    updated = copy.deepcopy(global_state)
    for key in updated:
        g = updated[key].float().cpu()
        c = client_state[key].float().cpu()
        updated[key] = (1.0 - alpha) * g + alpha * c
    return updated


class FedAsync(BaseAlgorithm):

    def __init__(self, cfg: dict, callback: Optional[MetricsCallback] = None):
        super().__init__(cfg, callback)
        self._speed_probs: Optional[np.ndarray] = None

    def run(
        self,
        client_loaders: List,
        test_loader,
        client_sizes: List[int],
    ) -> Tuple[List[float], List[float]]:
        cfg = self.cfg
        if self._secure_agg.enabled:
            logger.warning(
                "Secure Aggregation was requested but is not applied for "
                "FedAsync (incompatible with per-update async aggregation)."
            )
        num_clients = len(client_loaders)
        concurrency = min(cfg.get("async_concurrency", 3), num_clients)
        total_updates = cfg.get("rounds", 5) * cfg.get("async_updates_per_log", 10)
        log_every = cfg.get("async_updates_per_log", 10)
        alpha = cfg.get("async_alpha", 0.1)
        staleness_mode = cfg.get("staleness_weighting", "inverse")

        global_model = self._build_global_model()
        clients = [
            FLClient(i, loader, size, cfg, self._dp)
            for i, (loader, size) in enumerate(zip(client_loaders, client_sizes))
        ]
        self._speed_probs = self._build_speed_probs(num_clients, cfg)

        seq = itertools.count()
        heap: List = []
        global_version = 0

        for _ in range(concurrency):
            heap_item = self._dispatch(clients, global_model, global_version, 0.0, seq)
            heapq.heappush(heap, heap_item)

        round_accuracies: List[float] = []
        round_losses: List[float] = []
        updates_done = 0
        log_count = 0

        while updates_done < total_updates:
            finish_time, _, (client_idx, updated_weights, _local_loss, start_version) = heapq.heappop(heap)

            staleness = global_version - start_version
            eff_alpha = alpha * staleness_weight(staleness, staleness_mode)

            current_global_state = global_model.state_dict()

            if self._dp is not None:
                reference_state = clients[client_idx].get_reference_state()
                clipped_delta = {
                    k: updated_weights[k].float().cpu() - reference_state[k].float().cpu()
                    for k in updated_weights
                }
                new_weights = {
                    k: current_global_state[k].float().cpu() + eff_alpha * clipped_delta[k]
                    for k in current_global_state
                }
            else:
                new_weights = fedasync_update(current_global_state, updated_weights, eff_alpha)

            new_weights = self._maybe_dp_noise(new_weights)
            global_model.load_state_dict(new_weights)
            global_version += 1

            heap_item = self._dispatch(clients, global_model, global_version, finish_time, seq)
            heapq.heappush(heap, heap_item)

            updates_done += 1

            if updates_done % log_every == 0:
                log_count += 1
                test_loss, test_acc = self._evaluate(global_model, test_loader)
                round_accuracies.append(test_acc)
                round_losses.append(test_loss)
                self._emit(
                    round_num=log_count,
                    accuracy=test_acc,
                    loss=test_loss,
                    algorithm="fedasync",
                    staleness=staleness,
                    effective_alpha=eff_alpha,
                    updates_done=updates_done,
                    client_idx=client_idx,
                    selection_prob=float(self._speed_probs[client_idx]),
                )
            elif self._dp is not None:
                self._emit(
                    round_num=log_count,
                    accuracy=0.0,
                    loss=0.0,
                    algorithm="fedasync",
                    dp_only=True,
                    selection_prob=float(self._speed_probs[client_idx]),
                )

        return round_accuracies, round_losses

    def _dispatch(self, clients, global_model, global_version, current_time, seq):
        client_idx = int(np.random.choice(len(clients), p=self._speed_probs))
        client = clients[client_idx]

        start_version = global_version
        client.load_global_weights(self._deep_copy_state(global_model))
        updated_weights, _, local_loss = client.local_train()

        duration = self._sample_duration(client_idx)
        finish_time = current_time + duration
        payload = (client_idx, updated_weights, local_loss, start_version)
        return (finish_time, next(seq), payload)

    def _sample_duration(self, client_idx: int) -> float:
        weights = self.cfg.get("client_speed_weights")
        speed = weights[client_idx] if weights else 1.0
        mean_duration = self.cfg.get("duration_scale", 1.0) / max(speed, 1e-9)
        return float(np.random.exponential(mean_duration))

    @staticmethod
    def _build_speed_probs(num_clients: int, cfg: dict) -> np.ndarray:
        weights = cfg.get("client_speed_weights")
        if weights is not None:
            arr = np.array(weights, dtype=float)
            if len(arr) != num_clients:
                raise ValueError(
                    f"client_speed_weights length {len(arr)} != num_clients {num_clients}"
                )
            if np.any(arr <= 0):
                raise ValueError("All client_speed_weights must be positive")
        else:
            arr = np.ones(num_clients, dtype=float)
        return arr / arr.sum()
