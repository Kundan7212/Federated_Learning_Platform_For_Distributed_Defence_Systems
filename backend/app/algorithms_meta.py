from config.hyperparams import is_secure_agg_compatible

ALGORITHM_META = [
    {
        "value":       "fedavg",
        "label":       "FedAvg",
        "description": "Synchronous weighted averaging. Best convergence for IID data.",
        "type":        "synchronous",
        "paper":       "McMahan et al., 2017",
        "secure_agg_compatible": is_secure_agg_compatible("fedavg"),
    },
    {
        "value":       "fedasync",
        "label":       "FedAsync",
        "description": "Asynchronous FL with staleness-weighted updates via virtual clock simulation.",
        "type":        "asynchronous",
        "paper":       "Xie et al., 2019",
        "secure_agg_compatible": is_secure_agg_compatible("fedasync"),
    },
    {
        "value":       "fedfa",
        "label":       "FedFA",
        "description": "Federated Fast Aggregation — async FL with buffered deque for batched weighted merging.",
        "type":        "asynchronous",
        "paper":       "Custom implementation",
        "secure_agg_compatible": is_secure_agg_compatible("fedfa"),
    },
    {
        "value":       "fedprox",
        "label":       "FedProx",
        "description": "Proximal regularization term keeps local models close to the global model. Best for non-IID.",
        "type":        "synchronous",
        "paper":       "Li et al., 2020",
        "secure_agg_compatible": is_secure_agg_compatible("fedprox"),
    },
]
