from __future__ import annotations
import torch
import torch.nn as nn


class MLP(nn.Module):
    def __init__(self, input_size: int, hidden_size: int, num_classes: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Flatten(),
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class SimpleCNN(nn.Module):
    def __init__(self, ch1: int, ch2: int, hidden: int, num_classes: int):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, ch1, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(ch1, ch2, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(ch2 * 7 * 7, hidden),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def build_model(cfg: dict) -> nn.Module:
    model_type  = cfg.get("model_type", "cnn").lower().strip()
    num_classes = cfg.get("num_classes", 10)
    hidden      = cfg.get("hidden_size", 128)

    if model_type == "mlp":
        return MLP(
            input_size=cfg.get("input_size", 784),
            hidden_size=hidden,
            num_classes=num_classes,
        )
    elif model_type == "cnn":
        return SimpleCNN(
            ch1=cfg.get("cnn_channels_1", 32),
            ch2=cfg.get("cnn_channels_2", 64),
            hidden=hidden,
            num_classes=num_classes,
        )
    else:
        raise ValueError(
            f"Unknown model_type '{model_type}'. Choose 'mlp' or 'cnn'."
        )


def get_device(device_str: str = "auto") -> torch.device:
    if device_str == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device_str)
