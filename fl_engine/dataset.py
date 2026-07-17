from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
from PIL import Image
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms


DATASET_CLASSES: Dict[str, int] = {
    "mnist":  10,
    "emnist": 47,
}


def _get_transforms(dataset_name: str):
    if dataset_name == "emnist":
        return transforms.Compose([
            transforms.Lambda(
                lambda img: img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
            ),
            transforms.ToTensor(),
            transforms.Normalize((0.1751,), (0.3332,)),
        ])
    return transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])


def download_dataset(cfg: dict):
    name = cfg.get("dataset", "mnist").lower().strip()
    data_dir = cfg.get("data_dir", "./data")
    transform = _get_transforms(name)

    if name not in DATASET_CLASSES:
        raise ValueError(f"Unknown dataset '{name}'. Choose from {list(DATASET_CLASSES)}")

    if name == "mnist":
        train = datasets.MNIST(data_dir, train=True,  download=True, transform=transform)
        test  = datasets.MNIST(data_dir, train=False, download=True, transform=transform)
    elif name == "emnist":
        train = datasets.EMNIST(data_dir, split="balanced", train=True,  download=True, transform=transform)
        test  = datasets.EMNIST(data_dir, split="balanced", train=False, download=True, transform=transform)
    else:
        raise ValueError(f"Unsupported dataset: {name}")

    return train, test, DATASET_CLASSES[name]


def iid_partition(dataset, num_clients: int) -> List[np.ndarray]:
    indices = np.random.permutation(len(dataset))
    return list(np.array_split(indices, num_clients))


def non_iid_partition(dataset, num_clients: int) -> List[np.ndarray]:
    labels = np.array(dataset.targets)
    sorted_idx = np.argsort(labels)
    num_shards = 2 * num_clients
    shards = np.array_split(sorted_idx, num_shards)
    shard_order = np.random.permutation(num_shards)
    client_indices = []
    for i in range(num_clients):
        combined = np.concatenate([shards[shard_order[2 * i]], shards[shard_order[2 * i + 1]]])
        client_indices.append(combined)
    return client_indices


def dirichlet_partition(dataset, num_clients: int, alpha: float) -> List[np.ndarray]:
    labels = np.array(dataset.targets)
    num_classes = int(labels.max()) + 1
    client_indices: List[List[int]] = [[] for _ in range(num_clients)]

    for c in range(num_classes):
        idx_c = np.where(labels == c)[0]
        np.random.shuffle(idx_c)
        proportions = np.random.dirichlet(np.repeat(alpha, num_clients))
        split_points = (np.cumsum(proportions)[:-1] * len(idx_c)).astype(int)
        class_splits = np.split(idx_c, split_points)
        for cid in range(num_clients):
            client_indices[cid].extend(class_splits[cid].tolist())

    result = [np.array(idx) for idx in client_indices]
    for idx in result:
        np.random.shuffle(idx)
    return result


def create_client_loaders(
    train_dataset,
    client_indices: List[np.ndarray],
    batch_size: int,
) -> List[DataLoader]:
    return [
        DataLoader(
            Subset(train_dataset, idx.tolist()),
            batch_size=batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=False,
        )
        for idx in client_indices
    ]


def get_test_loader(test_dataset, batch_size: int = 256) -> DataLoader:
    return DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)


def load_data(cfg: dict) -> Tuple[List[DataLoader], DataLoader, List[int]]:
    num_clients = cfg.get("num_clients", 10)
    partition   = cfg.get("partition_method", "dirichlet").lower()
    batch_size  = cfg.get("batch_size", 32)
    alpha       = cfg.get("dirichlet_alpha", 0.5)

    train_dataset, test_dataset, num_classes = download_dataset(cfg)

    cfg["num_classes"] = num_classes

    if partition == "iid":
        client_indices = iid_partition(train_dataset, num_clients)
    elif partition == "label_skew":
        client_indices = non_iid_partition(train_dataset, num_clients)
    elif partition == "dirichlet":
        client_indices = dirichlet_partition(train_dataset, num_clients, alpha)
    else:
        raise ValueError(f"Unknown partition_method '{partition}'")

    client_loaders = create_client_loaders(train_dataset, client_indices, batch_size)
    test_loader    = get_test_loader(test_dataset)
    client_sizes   = [len(idx) for idx in client_indices]

    return client_loaders, test_loader, client_sizes
