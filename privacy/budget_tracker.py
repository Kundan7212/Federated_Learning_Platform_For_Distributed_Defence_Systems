from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import List, Optional

from config.hyperparams import DEFAULT_ALERT_THRESHOLD, DEFAULT_TARGET_DELTA, DEFAULT_TARGET_EPSILON


@dataclass
class BudgetEntry:
    round_num:   int
    epsilon:     float
    delta:       float
    noise_mult:  float
    clip_norm:   float
    num_samples: int
    lot_size:    int


class PrivacyBudgetTracker:
    """
    For each round with Gaussian mechanism (σ) and subsampling rate q:
      ε_round ≈ q * sqrt(2 * ln(1.25 / δ)) / σ

    q (sampling_rate) depends on how the FL algorithm participates:
      - Synchronous (FedAvg, FedProx): q = 1 — every client contributes
        every round, so there's no subsampling amplification to account for.
      - Asynchronous (FedAsync, FedFA): q = the probability that the one
        client behind this update was the one selected (its speed weight
        normalized across all clients).

    Cumulative ε via basic composition: ε_total = Σ ε_i
    """

    def __init__(
        self,
        max_epsilon: float = DEFAULT_TARGET_EPSILON,
        target_delta: float = DEFAULT_TARGET_DELTA,
        alert_threshold: float = DEFAULT_ALERT_THRESHOLD,
    ):
        self.max_epsilon     = max_epsilon
        self.target_delta    = target_delta
        self.alert_threshold = alert_threshold
        self._entries: List[BudgetEntry] = []

    @property
    def total_epsilon(self) -> float:
        return sum(e.epsilon for e in self._entries)

    @property
    def total_delta(self) -> float:
        return sum(e.delta for e in self._entries)

    @property
    def budget_used_fraction(self) -> float:
        if self.max_epsilon <= 0:
            return 1.0
        return min(self.total_epsilon / self.max_epsilon, 1.0)

    @property
    def remaining_epsilon(self) -> float:
        return max(0.0, self.max_epsilon - self.total_epsilon)

    @property
    def is_budget_exhausted(self) -> bool:
        return self.total_epsilon >= self.max_epsilon

    @property
    def is_alert(self) -> bool:
        return self.budget_used_fraction >= self.alert_threshold

    def account_round(
        self,
        round_num: int,
        noise_multiplier: float,
        max_grad_norm: float,
        num_samples: int,
        lot_size: int,
        delta: Optional[float] = None,
        sampling_rate: Optional[float] = None,
    ) -> float:
        
        delta = delta or self.target_delta
        lot_size = max(lot_size, 1)
        num_samples = max(num_samples, 1)

        if sampling_rate is None:
            sampling_rate = lot_size / num_samples
        sampling_rate = min(max(sampling_rate, 0.0), 1.0)

        epsilon = self._gaussian_epsilon(
            noise_multiplier=noise_multiplier,
            sampling_rate=sampling_rate,
            delta=delta,
        )

        entry = BudgetEntry(
            round_num=round_num,
            epsilon=epsilon,
            delta=delta,
            noise_mult=noise_multiplier,
            clip_norm=max_grad_norm,
            num_samples=num_samples,
            lot_size=lot_size,
        )
        self._entries.append(entry)
        return epsilon

    def get_history(self) -> List[dict]:
        cumulative = 0.0
        history = []
        for e in self._entries:
            cumulative += e.epsilon
            history.append({
                "round":            e.round_num,
                "epsilon_round":    round(e.epsilon, 6),
                "epsilon_total":    round(cumulative, 6),
                "delta":            e.delta,
                "noise_multiplier": e.noise_mult,
                "clip_norm":        e.clip_norm,
                "budget_used_pct":  round(cumulative / self.max_epsilon * 100, 2),
            })
        return history

    def summary(self) -> dict:
        return {
            "total_epsilon":     round(self.total_epsilon, 6),
            "total_delta":       self.total_delta,
            "max_epsilon":       self.max_epsilon,
            "remaining_epsilon": round(self.remaining_epsilon, 6),
            "budget_used_pct":   round(self.budget_used_fraction * 100, 2),
            "is_exhausted":      self.is_budget_exhausted,
            "is_alert":          self.is_alert,
            "num_rounds":        len(self._entries),
        }

    def reset(self) -> None:
        self._entries.clear()


    @staticmethod
    def _gaussian_epsilon(
        noise_multiplier: float,
        sampling_rate: float,
        delta: float,
    ) -> float:
        """
        Approximate per-round epsilon for Gaussian mechanism with subsampling.
        Uses the analytic formula for the Gaussian mechanism:
            ε ≈ q * sqrt(2 * ln(1.25/δ)) / σ
        where q = sampling_rate, σ = noise_multiplier.
        """
        if noise_multiplier <= 0 or delta <= 0 or delta >= 1:
            return float("inf")
        sigma = max(noise_multiplier, 1e-10)
        eps = sampling_rate * math.sqrt(2.0 * math.log(1.25 / delta)) / sigma
        return eps

    @staticmethod
    def estimate_sigma_for_epsilon(
        target_epsilon: float,
        sampling_rate: float,
        delta: float,
    ) -> float:
        """Estimate the noise multiplier σ needed to hit target ε."""
        if target_epsilon <= 0:
            return float("inf")
        return sampling_rate * math.sqrt(2.0 * math.log(1.25 / delta)) / target_epsilon
