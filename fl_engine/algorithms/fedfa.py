"""
FedFA — Federated Fast Aggregation
Async FL with a fixed-size buffer deque for batched weighted aggregation.
"""
from __future__ import annotations
import copy
import heapq
import itertools
from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np

from fl_engine.algorithms.base import BaseAlgorithm, MetricsCallback
from fl_engine.algorithms.fedasync import staleness_weight, FedAsync


def fedfa_merge(
    client_state: Dict,
    buffer: List[Dict],
    weights: List[float],
) -> Dict:

    all_updates = list(buffer) + [client_state]
    if len(weights) != len(all_updates):
        raise ValueError(
            f"fedfa_merge: {len(weights)} weights for {len(all_updates)} updates"
        )

    total_weight = sum(weights)
    merged = {k: v.cpu().float() * 0.0 for k, v in copy.deepcopy(client_state).items()}

    for state_dict, w in zip(all_updates, weights):
        for key in merged:
            merged[key] += (w / total_weight) * state_dict[key].float().cpu()

    return merged


def fedfa_merge_deltas(
    current_global_state: Dict,
    deltas: List[Dict],
    weights: List[float],
) -> Dict:
    if len(weights) != len(deltas):
        raise ValueError(
            f"fedfa_merge_deltas: {len(weights)} weights for {len(deltas)} deltas"
        )

    total_weight = sum(weights)
    merged = {k: v.cpu().float() * 0.0 for k, v in copy.deepcopy(current_global_state).items()}

    for delta, w in zip(deltas, weights):
        for key in merged:
            merged[key] += (w / total_weight) * delta[key].float().cpu()

    return {
        k: current_global_state[k].float().cpu() + merged[k]
        for k in current_global_state
    }


class FedFA(BaseAlgorithm):

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
        num_clients = len(client_loaders)
        concurrency = min(cfg.get("async_concurrency", 3), num_clients)
        buffer_size = cfg.get("fedfa_buffer_size", 4)
        total_updates = cfg.get("rounds", 5) * cfg.get("async_updates_per_log", 10)
        log_every = cfg.get("async_updates_per_log", 10)
        staleness_mode = cfg.get("staleness_weighting", "inverse")

        from fl_engine.client import FLClient  # local import avoids circular at module level

        global_model = self._build_global_model()
        clients = [
            FLClient(i, loader, size, cfg, self._dp)
            for i, (loader, size) in enumerate(zip(client_loaders, client_sizes))
        ]
        self._speed_probs = FedAsync._build_speed_probs(num_clients, cfg)

        buffer: deque = deque(maxlen=buffer_size)
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
            current_global_state = global_model.state_dict()

            if self._dp is not None:
                reference_state = clients[client_idx].get_reference_state()
                current_delta = {
                    k: updated_weights[k].float().cpu() - reference_state[k].float().cpu()
                    for k in updated_weights
                }

                buffered_deltas = [d for d, _ in buffer]
                buffered_weights = [
                    staleness_weight(global_version - sv, staleness_mode)
                    for _, sv in buffer
                ]
                current_weight = staleness_weight(staleness, staleness_mode)
                all_weights = buffered_weights + [current_weight]
                all_deltas = buffered_deltas + [current_delta]

                if self._secure_agg.enabled and len(all_deltas) > 1:
                    self._secure_agg.setup(len(all_deltas))
                    secure_result = self._secure_agg.aggregate_secure(
                        list(zip(all_deltas, all_weights))
                    )
                    merged_weights = {
                        k: current_global_state[k].float().cpu() + secure_result[k].float().cpu()
                        for k in current_global_state
                    }
                else:
                    merged_weights = fedfa_merge_deltas(
                        current_global_state, all_deltas, all_weights,
                    )

                merged_weights = self._maybe_dp_noise(merged_weights)
                global_model.load_state_dict(merged_weights)
                global_version += 1
                buffer.append((current_delta, start_version))
            else:
                buffered_states = [sd for sd, _ in buffer]
                buffered_weights = [
                    staleness_weight(global_version - sv, staleness_mode)
                    for _, sv in buffer
                ]
                current_weight = staleness_weight(staleness, staleness_mode)
                all_weights = buffered_weights + [current_weight]

                all_states = buffered_states + [updated_weights]

                updated_weights_for_merge = all_states[-1]
                buffered_states_for_merge = all_states[:-1]

                if self._secure_agg.enabled and len(all_states) > 1:
                    self._secure_agg.setup(len(all_states))
                    merged_weights = self._secure_agg.aggregate_secure(
                        list(zip(all_states, all_weights))
                    )
                else:
                    merged_weights = fedfa_merge(
                        updated_weights_for_merge,
                        buffered_states_for_merge,
                        all_weights,
                    )
                global_model.load_state_dict(merged_weights)
                global_version += 1
                buffer.append((updated_weights, start_version))

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
                    algorithm="fedfa",
                    staleness=staleness,
                    buffer_len=len(buffer),
                    updates_done=updates_done,
                    client_idx=client_idx,
                    selection_prob=float(self._speed_probs[client_idx]),
                )
            elif self._dp is not None:
                self._emit(
                    round_num=log_count,
                    accuracy=0.0,
                    loss=0.0,
                    algorithm="fedfa",
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

        cfg = self.cfg
        weights = cfg.get("client_speed_weights")
        speed = weights[client_idx] if weights else 1.0
        mean_dur = cfg.get("duration_scale", 1.0) / max(speed, 1e-9)
        duration = float(np.random.exponential(mean_dur))

        finish_time = current_time + duration
        payload = (client_idx, updated_weights, local_loss, start_version)
        return (finish_time, next(seq), payload)
