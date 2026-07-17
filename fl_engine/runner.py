from __future__ import annotations
import os
import random
from typing import Callable, Dict, List, Optional, Tuple
import numpy as np
import torch

from fl_engine.algorithms.registry import registry
from fl_engine.dataset import load_data


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def run_experiment(
    cfg: dict,
    callback: Optional[Callable] = None,
    seed: int = 42,
) -> Tuple[List[float], List[float], Dict]:

    set_seed(seed)
    results_dir = cfg.get("results_dir", "./results")
    os.makedirs(results_dir, exist_ok=True)

    client_loaders, test_loader, client_sizes = load_data(cfg)

    algo_name = cfg.get("algorithm", "fedavg").lower()
    algorithm = registry.create(algo_name, cfg=cfg, callback=callback)

    round_accuracies, round_losses = algorithm.run(
        client_loaders=client_loaders,
        test_loader=test_loader,
        client_sizes=client_sizes,
    )

    summary = {
        "algorithm":      algo_name.upper(),
        "dataset":        cfg.get("dataset", "mnist").upper(),
        "model":          cfg.get("model_type", "cnn").upper(),
        "num_clients":    cfg.get("num_clients", 10),
        "rounds":         len(round_accuracies),
        "final_accuracy": round_accuracies[-1] if round_accuracies else 0.0,
        "best_accuracy":  max(round_accuracies) if round_accuracies else 0.0,
        "final_loss":     round_losses[-1] if round_losses else 0.0,
    }

    return round_accuracies, round_losses, summary
