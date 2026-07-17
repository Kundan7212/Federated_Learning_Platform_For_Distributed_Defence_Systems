from __future__ import annotations
import os
import re
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, field_validator

from config.hyperparams import (
    ALGORITHM_CHOICES,
    DEFAULT_ALERT_THRESHOLD,
    DEFAULT_TARGET_DELTA,
    DEFAULT_TARGET_EPSILON,
    PARTITION_METHOD_CHOICES,
)


class DifferentialPrivacyConfig(BaseModel):
    enabled: bool = False
    noise_multiplier: float = 1.0
    max_grad_norm: float = 1.0
    target_epsilon: float = DEFAULT_TARGET_EPSILON
    target_delta: float = DEFAULT_TARGET_DELTA


class SecureAggregationConfig(BaseModel):
    enabled: bool = False
    num_shares: int = 3


class BudgetTrackerConfig(BaseModel):
    alert_threshold: float = DEFAULT_ALERT_THRESHOLD


class PrivacyConfig(BaseModel):
    differential_privacy: DifferentialPrivacyConfig = DifferentialPrivacyConfig()
    secure_aggregation: SecureAggregationConfig = SecureAggregationConfig()
    budget_tracker: BudgetTrackerConfig = BudgetTrackerConfig()


class FLConfig(BaseModel):
    dataset: str = "mnist"
    num_clients: int = 10
    data_dir: str = "./data"
    partition_method: str = "dirichlet"
    dirichlet_alpha: float = 0.5
    model_type: str = "cnn"
    input_size: int = 784
    hidden_size: int = 128
    num_classes: int = 10
    cnn_channels_1: int = 32
    cnn_channels_2: int = 64
    rounds: int = 5
    local_epochs: int = 2
    batch_size: int = 32
    lr: float = 0.01
    device: str = "auto"
    algorithm: str = "fedavg"
    async_alpha: float = 0.1
    async_concurrency: int = 3
    duration_scale: float = 1.0
    staleness_weighting: str = "inverse"
    async_updates_per_log: int = 10
    fedfa_buffer_size: int = 4
    fedprox_mu: float = 0.01
    client_speed_weights: Optional[List[float]] = None
    results_dir: str = "./results"
    save_model: bool = True

    @field_validator("algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        if v.lower() not in ALGORITHM_CHOICES:
            raise ValueError(f"algorithm must be one of {ALGORITHM_CHOICES}, got '{v}'")
        return v.lower()

    @field_validator("partition_method")
    @classmethod
    def validate_partition(cls, v: str) -> str:
        if v.lower() not in PARTITION_METHOD_CHOICES:
            raise ValueError(f"partition_method must be one of {PARTITION_METHOD_CHOICES}")
        return v.lower()


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 1440
    database_url: str = "sqlite:///./fl_platform.db"
    cors_origins: List[str] = ["http://localhost:3000"]


class AppConfig(BaseModel):
    fl: FLConfig = FLConfig()
    privacy: PrivacyConfig = PrivacyConfig()
    server: ServerConfig = ServerConfig()


_ENV_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def _resolve_env_vars(value: str) -> str:
    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, match.group(0))
    return _ENV_VAR_PATTERN.sub(replacer, value)


def _resolve_recursive(obj):
    if isinstance(obj, dict):
        return {k: _resolve_recursive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_recursive(item) for item in obj]
    if isinstance(obj, str):
        return _resolve_env_vars(obj)
    return obj


def load_config(path: Optional[str] = None) -> AppConfig:
    if path is None:
        candidates = [
            Path(__file__).parent / "config.yaml",
            Path.cwd() / "config" / "config.yaml",
            Path.cwd() / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = str(candidate)
                break
        else:
            return AppConfig()

    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    resolved = _resolve_recursive(raw or {})
    return AppConfig(**resolved)


_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    global _config
    _config = None
