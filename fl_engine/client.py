from __future__ import annotations
import copy
from typing import Dict, Optional, Tuple

from fl_engine.model import build_model
from fl_engine.trainer import train
from privacy.differential_privacy import DPMechanism


class FLClient:

    def __init__(self, client_id: int, data_loader, num_samples: int, cfg: dict, dp_mechanism: Optional[DPMechanism] = None):
        self.client_id    = client_id
        self.data_loader  = data_loader
        self.num_samples  = num_samples
        self.cfg          = cfg
        self.model        = build_model(cfg)
        self._dp          = dp_mechanism
        self._global_state = None

    def load_global_weights(self, global_state_dict: Dict) -> None:
        self._global_state = copy.deepcopy(global_state_dict)
        self.model.load_state_dict(copy.deepcopy(global_state_dict))

    def get_reference_state(self) -> Dict:
        return self._global_state

    def local_train(self) -> Tuple[Dict, int, float]:
        local_loss = train(self.model, self.data_loader, self.cfg)
        updated_weights = {
            key: val.cpu().clone()
            for key, val in self.model.state_dict().items()
        }
        if self._dp is not None:
            delta = {
                k: updated_weights[k].float().cpu() - self._global_state[k].float().cpu()
                for k in updated_weights
            }
            clipped_delta = self._dp.clip_weights(delta)
            updated_weights = {
                k: self._global_state[k].float().cpu() + clipped_delta[k]
                for k in updated_weights
            }
        return updated_weights, self.num_samples, local_loss
