"""Evaluation metrics for imbalanced binary classification."""

import numpy as np
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             f1_score)


def evaluate(y_true, y_pred, y_score=None):
    """Return the full metric dict used in the paper's result tables."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    out = {
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "accuracy": (tp + tn) / (tp + tn + fp + fn),
        "f1": f1_score(y_true, y_pred, pos_label=1, zero_division=0),
        "gmean": float(np.sqrt(sens * spec)),
        "bas": (sens + spec) / 2.0,
    }
    if y_score is not None:
        out["auprc"] = average_precision_score(y_true, y_score)
    return out


def fitness_score(name, y_true, y_pred):
    """Scalar fitness used inside the ACO loop (prediction-label based)."""
    m = evaluate(y_true, y_pred)
    if name not in ("f1", "gmean", "bas"):
        raise ValueError(f"Unknown fitness '{name}' (use f1, gmean, or bas)")
    return m[name]
