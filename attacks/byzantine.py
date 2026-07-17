"""
Byzantine Attack Simulations.
I simulated three attack types for testing robustness of aggregation strategies in case when models send curropt updates.
"""
from __future__ import annotations

import copy
import random
from enum import Enum
from typing import Dict, List, Tuple

import torch


class AttackType(str, Enum):
    GAUSSIAN_NOISE = "gaussian_noise"   
    SIGN_FLIP      = "sign_flip"        
    SCALING        = "scaling"          


class ByzantineAttacker:

    def __init__(
        self,
        attack_type: AttackType = AttackType.GAUSSIAN_NOISE,
        num_adversaries: int = 2,
        noise_scale: float = 10.0,
        scale_factor: float = 10.0,
    ):
        self.attack_type     = AttackType(attack_type)
        self.num_adversaries = num_adversaries
        self.noise_scale     = noise_scale
        self.scale_factor    = scale_factor

    def poison_updates(
        self,
        client_updates: List[Tuple[Dict[str, torch.Tensor], int]],
    ) -> List[Tuple[Dict[str, torch.Tensor], int]]:
        
        if self.num_adversaries <= 0:
            return client_updates

        n = len(client_updates)
        adv_count = min(self.num_adversaries, n)
        adv_indices = set(random.sample(range(n), adv_count))

        result = []
        for i, (weights, num_samples) in enumerate(client_updates):
            if i in adv_indices:
                poisoned = self._attack(weights)
                result.append((poisoned, num_samples))
            else:
                result.append((weights, num_samples))
        return result

    def _attack(self, weights: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        if self.attack_type == AttackType.GAUSSIAN_NOISE:
            return self._gaussian_noise_attack(weights)
        elif self.attack_type == AttackType.SIGN_FLIP:
            return self._sign_flip_attack(weights)
        elif self.attack_type == AttackType.SCALING:
            return self._scaling_attack(weights)
        raise ValueError(f"Unknown attack type: {self.attack_type}")

    def _gaussian_noise_attack(
        self, weights: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        return {
            k: torch.randn_like(v.float()) * self.noise_scale
            for k, v in weights.items()
        }

    def _sign_flip_attack(
        self, weights: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        return {k: -v.float().clone() for k, v in weights.items()}

    def _scaling_attack(
        self, weights: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        return {k: v.float().clone() * self.scale_factor for k, v in weights.items()}
