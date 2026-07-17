"""
FedProx — Li et al. 2020 [Paper]
Adds a proximal term μ/2 · ||w - w_global||² to the local objective.
This regularizes local training toward the global model,
improving convergence on heterogeneous (non-IID) data.
"""
from __future__ import annotations
import copy
from typing import Dict, List, Optional, Tuple
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from fl_engine.algorithms.base import BaseAlgorithm, MetricsCallback
from fl_engine.algorithms.fedavg import fedavg_aggregate
from fl_engine.model import build_model, get_device


def train_fedprox(
    model: nn.Module,
    global_state: Dict,
    data_loader: DataLoader,
    cfg: dict,
) -> float:
    
    device = get_device(cfg.get("device", "auto"))
    model = model.to(device)
    model.train()

    mu = cfg.get("fedprox_mu", 0.01)
    lr = cfg.get("lr", 0.01)
    epochs = cfg.get("local_epochs", 2)

    global_model = build_model(cfg).to(device)
    global_model.load_state_dict(copy.deepcopy(global_state))
    for p in global_model.parameters():
        p.requires_grad_(False)

    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9)
    criterion = nn.CrossEntropyLoss()

    total_loss = 0.0
    num_batches = 0

    for _ in range(epochs):
        for images, labels in data_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            ce_loss = criterion(outputs, labels)

            # Proximal term: μ/2 * sum_i ||w_i - w_global_i||²
            prox_term = torch.tensor(0.0, device=device)
            for w, w_global in zip(model.parameters(), global_model.parameters()):
                prox_term += ((w - w_global.detach()) ** 2).sum()
            prox_loss = (mu / 2.0) * prox_term

            loss = ce_loss + prox_loss
            loss.backward()
            optimizer.step()

            total_loss += ce_loss.item()  
            num_batches += 1

    return total_loss / max(num_batches, 1)


class FedProx(BaseAlgorithm):
    
    def __init__(self, cfg: dict, callback: Optional[MetricsCallback] = None):
        super().__init__(cfg, callback)

    def run(
        self,
        client_loaders: List,
        test_loader,
        client_sizes: List[int],
    ) -> Tuple[List[float], List[float]]:
        from fl_engine.model import build_model

        global_model = self._build_global_model()
        rounds = self.cfg.get("rounds", 5)

        round_accuracies: List[float] = []
        round_losses: List[float] = []

        for round_num in range(1, rounds + 1):
            global_weights = self._deep_copy_state(global_model)
            client_updates: List[Tuple[Dict, int]] = []

            for loader, num_samples in zip(client_loaders, client_sizes):
                local_model = build_model(self.cfg).to(self.device)
                local_model.load_state_dict(copy.deepcopy(global_weights))

                train_fedprox(local_model, global_weights, loader, self.cfg)

                updated_weights = {
                    k: v.cpu().clone()
                    for k, v in local_model.state_dict().items()
                }
                updated_weights = self._maybe_dp_clip_single(global_weights, updated_weights)
                client_updates.append((updated_weights, num_samples))

            new_weights = self._maybe_secure_aggregate(
                client_updates,
                lambda: fedavg_aggregate(global_weights, client_updates),
            )
            new_weights = self._maybe_dp_noise(new_weights)
            global_model.load_state_dict(new_weights)

            test_loss, test_acc = self._evaluate(global_model, test_loader)
            round_accuracies.append(test_acc)
            round_losses.append(test_loss)

            self._emit(
                round_num=round_num,
                accuracy=test_acc,
                loss=test_loss,
                algorithm="fedprox",
                mu=self.cfg.get("fedprox_mu", 0.01),
            )

        return round_accuracies, round_losses
