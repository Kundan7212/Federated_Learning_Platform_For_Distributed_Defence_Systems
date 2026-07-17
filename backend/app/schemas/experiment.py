from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from config.hyperparams import (
    ALGORITHM_CHOICES,
    CLIENT_SPEED_PROFILE_CHOICES,
    DATASET_CHOICES,
    MODEL_TYPE_CHOICES,
    PARTITION_METHOD_CHOICES,
    STALENESS_WEIGHTING_CHOICES,
)

class FLConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    algorithm:        str   = Field("fedavg")
    dataset:          str   = Field("mnist")
    model_type:       str   = Field("cnn")
    num_clients:      int   = Field(10, ge=2, le=100)
    rounds:           int   = Field(5,  ge=1, le=100)
    local_epochs:     int   = Field(2,  ge=1, le=20)
    batch_size:       int   = Field(32, ge=8, le=256)
    learning_rate:    float = Field(0.01, ge=1e-5, le=1.0)
    partition_method: str   = Field("dirichlet")
    dirichlet_alpha:  float = Field(0.5, ge=0.01, le=10.0)
    
    # async params
    async_alpha:       float = Field(0.1, ge=0.01, le=1.0)
    async_concurrency: int   = Field(3,   ge=1, le=50)
    async_updates_per_log: int = Field(10, ge=1, le=100)
    fedfa_buffer_size: int   = Field(4,   ge=1, le=20)
    fedprox_mu:        float = Field(0.01, ge=0.0, le=1.0)
    staleness_weighting: str = Field("inverse")
    client_speed_profile: str = Field("uniform")

    @field_validator("algorithm")
    @classmethod
    def _validate_algorithm(cls, v: str) -> str:
        if v not in ALGORITHM_CHOICES:
            raise ValueError(f"algorithm must be one of {ALGORITHM_CHOICES}")
        return v

    @field_validator("dataset")
    @classmethod
    def _validate_dataset(cls, v: str) -> str:
        if v not in DATASET_CHOICES:
            raise ValueError(f"dataset must be one of {DATASET_CHOICES}")
        return v

    @field_validator("model_type")
    @classmethod
    def _validate_model_type(cls, v: str) -> str:
        if v not in MODEL_TYPE_CHOICES:
            raise ValueError(f"model_type must be one of {MODEL_TYPE_CHOICES}")
        return v

    @field_validator("partition_method")
    @classmethod
    def _validate_partition_method(cls, v: str) -> str:
        if v not in PARTITION_METHOD_CHOICES:
            raise ValueError(f"partition_method must be one of {PARTITION_METHOD_CHOICES}")
        return v

    @field_validator("staleness_weighting")
    @classmethod
    def _validate_staleness_weighting(cls, v: str) -> str:
        if v not in STALENESS_WEIGHTING_CHOICES:
            raise ValueError(f"staleness_weighting must be one of {STALENESS_WEIGHTING_CHOICES}")
        return v

    @field_validator("client_speed_profile")
    @classmethod
    def _validate_client_speed_profile(cls, v: str) -> str:
        if v not in CLIENT_SPEED_PROFILE_CHOICES:
            raise ValueError(f"client_speed_profile must be one of {CLIENT_SPEED_PROFILE_CHOICES}")
        return v


class PrivacyOptions(BaseModel):
    dp_enabled:       bool  = False
    noise_multiplier: float = Field(1.0, ge=0.01, le=100.0)
    max_grad_norm:    float = Field(1.0, ge=0.01, le=100.0)
    sa_enabled:       bool  = False


class CreateExperimentRequest(BaseModel):
    name:        str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    fl_config:   FLConfig
    privacy:     PrivacyOptions = PrivacyOptions()


class ExperimentResponse(BaseModel):
    id:             str
    name:           str
    description:    Optional[str]
    algorithm:      str
    dataset:        str
    model_type:     str
    num_clients:    int
    rounds:         int
    local_epochs:   int
    batch_size:     int
    learning_rate:  float
    partition_method: str
    dp_enabled:     bool
    sa_enabled:     bool
    noise_mult:     Optional[float]
    max_grad_norm:  Optional[float]
    status:         str
    final_accuracy: Optional[float]
    best_accuracy:  Optional[float]
    final_loss:     Optional[float]
    total_epsilon:  Optional[float]
    error_message:  Optional[str]
    owner_id:       str
    created_at:     datetime
    started_at:     Optional[datetime]
    finished_at:    Optional[datetime]
    duration_seconds: Optional[float]
    model_config = {"from_attributes": True, "protected_namespaces": ()}


class RoundMetricResponse(BaseModel):
    round_num:   int
    accuracy:    float
    loss:        float
    extra:       Optional[Dict[str, Any]]
    recorded_at: datetime
    model_config = {"from_attributes": True}


class PrivacyLogResponse(BaseModel):
    round_num:     int
    epsilon_round: float
    epsilon_total: float
    delta:         float
    noise_mult:    float
    clip_norm:     float
    recorded_at:   datetime
    model_config = {"from_attributes": True}


class ExperimentDetailResponse(ExperimentResponse):
    round_metrics: List[RoundMetricResponse] = []
    privacy_logs:  List[PrivacyLogResponse]  = []


class TrainingStatusResponse(BaseModel):
    experiment_id:  str
    status:         str
    current_round:  int
    total_rounds:   int
    latest_accuracy: Optional[float]
    latest_loss:     Optional[float]
    total_epsilon:   Optional[float]
    progress_pct:    float


class WebSocketMessage(BaseModel):
    type:    str  # round_update | status_change | error | complete
    payload: Dict[str, Any]
