from __future__ import annotations
import copy
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple
import torch

from fl_engine.model import build_model, get_device
from fl_engine.trainer import evaluate
from privacy.differential_privacy import DPMechanism
from privacy.secure_aggregation import SecureAggregationProtocol


MetricsCallback = Callable[..., None]


class BaseAlgorithm(ABC):

    def __init__(self, cfg: dict, callback: Optional[MetricsCallback] = None):
        self.cfg = cfg
        self.callback = callback
        self.device = get_device(cfg.get("device", "auto"))
        self._secure_agg = SecureAggregationProtocol(cfg)
        self._dp = self._build_dp_mechanism(cfg)

    @staticmethod
    def _build_dp_mechanism(cfg: dict) -> Optional[DPMechanism]:
        dp_cfg = cfg.get("differential_privacy", {})
        if not dp_cfg.get("enabled", False):
            return None
        return DPMechanism(
            noise_multiplier=dp_cfg.get("noise_multiplier", 1.0),
            max_grad_norm=dp_cfg.get("max_grad_norm", 1.0),
        )

    @abstractmethod
    def run(
        self,
        client_loaders: List,
        test_loader,
        client_sizes: List[int],
    ) -> Tuple[List[float], List[float]]:
        """Train the global model. Returns (round_accuracies, round_losses)."""
        ...


    def _build_global_model(self):
        return build_model(self.cfg).to(self.device)

    def _evaluate(self, model, test_loader) -> Tuple[float, float]:
        return evaluate(model, test_loader)

    def _emit(self, round_num: int, accuracy: float, loss: float, **kwargs) -> None:
        if self.callback is not None:
            self.callback(
                round_num=round_num,
                accuracy=accuracy,
                loss=loss,
                **kwargs,
            )

    @staticmethod
    def _deep_copy_state(model) -> Dict:
        return copy.deepcopy(model.state_dict())

    def _maybe_secure_aggregate(
        self,
        client_updates: List[Tuple[Dict, int]],
        plain_fallback: Callable[[], Dict],
    ) -> Dict:
        
        if self._secure_agg.enabled and len(client_updates) > 1:
            self._secure_agg.setup(len(client_updates))
            return self._secure_agg.aggregate_secure(client_updates)
        return plain_fallback()

    def _maybe_dp_clip_single(self, global_state: Dict, client_state: Dict) -> Dict:
        if self._dp is None:
            return client_state

        delta = {
            k: client_state[k].float().cpu() - global_state[k].float().cpu()
            for k in client_state
        }
        clipped_delta = self._dp.clip_weights(delta)
        return {
            k: global_state[k].float().cpu() + clipped_delta[k]
            for k in client_state
        }

    def _maybe_dp_noise(self, aggregated_state: Dict) -> Dict:
        if self._dp is None:
            return aggregated_state
        return self._dp.add_noise(aggregated_state)
