"""
Local Machine Learning Module.
Exposes trained LightGBM, LogisticRegression, and RandomForest models
for local propensity scoring, disqualification gating, and feature extraction.
"""
from .feature_extractor import extract_feature_vector, FEATURE_NAMES


def get_local_models():
    from .inference import get_local_models as _get
    return _get()


def predict_lead_evaluation(*args, **kwargs):
    from .inference import predict_lead_evaluation as _pred
    return _pred(*args, **kwargs)


def train_and_save_models(*args, **kwargs):
    from .trainer import train_and_save_models as _train
    return _train(*args, **kwargs)


__all__ = [
    "extract_feature_vector",
    "FEATURE_NAMES",
    "train_and_save_models",
    "get_local_models",
    "predict_lead_evaluation",
]
