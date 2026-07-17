from __future__ import annotations
import random
from typing import List, Optional

# ── Valid choice sets ────────────────────────────────────────────────────
ALGORITHM_CHOICES            = ("fedavg", "fedasync", "fedfa", "fedprox")
DATASET_CHOICES              = ("mnist", "emnist")
MODEL_TYPE_CHOICES           = ("mlp", "cnn")
PARTITION_METHOD_CHOICES     = ("iid", "label_skew", "dirichlet")
STALENESS_WEIGHTING_CHOICES  = ("none", "inverse")
CLIENT_SPEED_PROFILE_CHOICES = ("uniform", "mild", "high")
ASYNC_ALGORITHMS = ("fedasync", "fedfa")

def is_async_algorithm(algorithm: str) -> bool:
    return algorithm in ASYNC_ALGORITHMS

SECURE_AGG_COMPATIBLE_ALGORITHMS = ("fedavg", "fedprox", "fedfa")

def is_secure_agg_compatible(algorithm: str) -> bool:
    return algorithm in SECURE_AGG_COMPATIBLE_ALGORITHMS

def generate_client_speed_weights(profile: str, num_clients: int) -> Optional[List[float]]:
    """
    - "uniform" -> None (existing default behavior: every client has the same expected speed — unchanged).
    - "mild"    -> num_clients weights drawn from Uniform(0.7, 1.3).
    - "high"    -> num_clients weights drawn from Uniform(0.1, 2.0).
    """
    if profile == "uniform":
        return None
    if profile == "mild":
        return [random.uniform(0.7, 1.3) for _ in range(num_clients)]
    if profile == "high":
        return [random.uniform(0.1, 2.0) for _ in range(num_clients)]
    raise ValueError(f"client_speed_profile must be one of {CLIENT_SPEED_PROFILE_CHOICES}")

DEFAULT_TARGET_EPSILON  = 10.0
DEFAULT_TARGET_DELTA    = 1e-5
DEFAULT_ALERT_THRESHOLD = 0.8   
