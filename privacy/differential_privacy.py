"""
Differential Privacy for Federated Learning without any prebuilt framework.
Implements gradient clipping + Gaussian noise mechanism.
"""
from __future__ import annotations
import copy
from typing import Dict, List, Tuple
import torch
import torch.nn as nn

from privacy.budget_tracker import PrivacyBudgetTracker


class DPMechanism:
    
    def __init__(
        self,
        noise_multiplier: float = 1.0,
        max_grad_norm: float = 1.0,
        budget_tracker: PrivacyBudgetTracker = None,
    ):
        if noise_multiplier <= 0:
            raise ValueError("noise_multiplier must be positive")
        if max_grad_norm <= 0:
            raise ValueError("max_grad_norm must be positive")

        self.noise_multiplier = noise_multiplier
        self.max_grad_norm    = max_grad_norm
        self.budget_tracker   = budget_tracker

    def clip_weights(self, weights: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        clipped = {k: v.float().cpu().clone() for k, v in weights.items()}
        l2_norm = torch.sqrt(
            sum(t.norm() ** 2 for t in clipped.values())
        )
        clip_factor = min(1.0, self.max_grad_norm / (l2_norm.item() + 1e-10))
        return {k: v * clip_factor for k, v in clipped.items()}

    def add_noise(self, weights: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        sigma = self.noise_multiplier * self.max_grad_norm
        return {
            k: v + torch.normal(mean=0.0, std=sigma, size=v.shape)
            for k, v in weights.items()
        }

    def privatize_update(
        self, weights: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        clipped = self.clip_weights(weights)
        return self.add_noise(clipped)

    def privatize_batch(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
        num_total_samples: int,
        round_num: int = 0,
    ) -> List[Tuple[Dict[str, torch.Tensor], int]]:
        
        privatized = []
        for weights, num_samples in client_updates:
            dp_weights = self.privatize_update(weights)
            privatized.append((dp_weights, num_samples))

        if self.budget_tracker is not None:
            lot_size = min(32, num_total_samples)  # approximate batch size
            self.budget_tracker.account_round(
                round_num=round_num,
                noise_multiplier=self.noise_multiplier,
                max_grad_norm=self.max_grad_norm,
                num_samples=num_total_samples,
                lot_size=lot_size,
            )
        return privatized

    def apply_to_model(self, model: nn.Module) -> nn.Module:
        noised_model = copy.deepcopy(model)
        with torch.no_grad():
            for param in noised_model.parameters():
                noise = torch.normal(
                    mean=0.0,
                    std=self.noise_multiplier * self.max_grad_norm,
                    size=param.shape,
                    device=param.device,
                )
                param.add_(noise)
        return noised_model

    @property
    def sensitivity(self) -> float:
        return self.max_grad_norm

    @property
    def noise_scale(self) -> float:
        return self.noise_multiplier * self.max_grad_norm


def create_dp_mechanism(cfg: dict, tracker: PrivacyBudgetTracker = None) -> DPMechanism:
    dp_cfg = cfg.get("differential_privacy", {})
    return DPMechanism(
        noise_multiplier=dp_cfg.get("noise_multiplier", 1.0),
        max_grad_norm=dp_cfg.get("max_grad_norm", 1.0),
        budget_tracker=tracker,
    )
