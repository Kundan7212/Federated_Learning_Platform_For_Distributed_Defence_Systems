from __future__ import annotations
from typing import Callable, Dict, Optional, Type
from fl_engine.algorithms.base import BaseAlgorithm, MetricsCallback


class AlgorithmRegistry:

    def __init__(self):
        self._registry: Dict[str, Type[BaseAlgorithm]] = {}

    def register(self, name: str, cls: Type[BaseAlgorithm]) -> None:
        name = name.lower().strip()
        if not issubclass(cls, BaseAlgorithm):
            raise TypeError(f"{cls} must subclass BaseAlgorithm")
        self._registry[name] = cls

    def get(self, name: str) -> Type[BaseAlgorithm]:
        name = name.lower().strip()
        if name not in self._registry:
            available = list(self._registry.keys())
            raise KeyError(
                f"Unknown algorithm '{name}'. Available: {available}"
            )
        return self._registry[name]

    def create(
        self,
        name: str,
        cfg: dict,
        callback: Optional[MetricsCallback] = None,
    ) -> BaseAlgorithm:
        cls = self.get(name)
        return cls(cfg=cfg, callback=callback)

    def list_algorithms(self) -> list:
        return sorted(self._registry.keys())

    def is_registered(self, name: str) -> bool:
        return name.lower().strip() in self._registry


def _build_default_registry() -> AlgorithmRegistry:
    from fl_engine.algorithms.fedavg import FedAvg
    from fl_engine.algorithms.fedasync import FedAsync
    from fl_engine.algorithms.fedfa import FedFA
    from fl_engine.algorithms.fedprox import FedProx

    reg = AlgorithmRegistry()
    reg.register("fedavg",   FedAvg)
    reg.register("fedasync", FedAsync)
    reg.register("fedfa",    FedFA)
    reg.register("fedprox",  FedProx)
    return reg


registry: AlgorithmRegistry = _build_default_registry()
