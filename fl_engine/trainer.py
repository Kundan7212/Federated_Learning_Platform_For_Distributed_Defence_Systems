from __future__ import annotations
import time
from typing import Tuple
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from fl_engine.model import get_device
from fl_engine.exceptions import TrainingCancelledError


def train(
    model: nn.Module,
    data_loader: DataLoader,
    cfg: dict,
) -> float:
    
    device  = get_device(cfg.get("device", "auto"))
    epochs  = cfg.get("local_epochs", 2)
    lr      = cfg.get("lr", 0.01)
    stop_event = cfg.get("_stop_event")

    model = model.to(device)
    model.train()

    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    final_loss  = 0.0
    final_count = 0

    for _ in range(epochs):
        epoch_loss  = 0.0
        epoch_count = 0
        for images, labels in data_loader:
            if stop_event is not None and stop_event.is_set():
                raise TrainingCancelledError("Training cancelled by user")
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss    = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            epoch_loss  += loss.item()
            epoch_count += 1
            time.sleep(0)
        final_loss  = epoch_loss
        final_count = epoch_count

    return final_loss / max(final_count, 1)


def evaluate(
    model: nn.Module,
    data_loader: DataLoader,
) -> Tuple[float, float]:
    
    try:
        device = next(model.parameters()).device
    except StopIteration:
        device = torch.device("cpu")

    model.eval()
    criterion     = nn.CrossEntropyLoss()
    total_loss    = 0.0
    correct       = 0
    total_samples = 0

    with torch.no_grad():
        for images, labels in data_loader:
            images = images.to(device)
            labels = labels.to(device)
            outputs = model(images)
            loss    = criterion(outputs, labels)
            total_loss    += loss.item() * images.size(0)
            total_samples += images.size(0)
            correct       += (outputs.argmax(dim=1) == labels).sum().item()
            time.sleep(0)

    avg_loss = total_loss / max(total_samples, 1)
    accuracy = correct   / max(total_samples, 1)
    return avg_loss, accuracy
