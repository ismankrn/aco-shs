"""Oversampling / hybrid sampling builders.

All functions operate on (X: DataFrame, y: Series) and sample the TRAINING
split only. `n_target` is the desired number of minority instances after
oversampling (thesis used absolute targets 1000/1500/2000 on NR; for
cross-dataset comparability prefer `ratio_to_target()`).
"""

import pandas as pd
from imblearn.combine import SMOTEENN, SMOTETomek
from imblearn.over_sampling import ADASYN, SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler

SMOTE_K_NEIGHBORS = 11  # thesis setting


def ratio_to_target(y, ratio, minority_label=1):
    """Minority target count = ratio x majority count (e.g. 1.25 -> 25% surplus)."""
    n_majority = int((y != minority_label).sum())
    return int(round(ratio * n_majority))


def make_oversampler(name, n_target, minority_label=1, random_state=None):
    strategy = {minority_label: n_target}
    if name == "ros":
        return RandomOverSampler(sampling_strategy=strategy, random_state=random_state)
    if name == "smote":
        return SMOTE(sampling_strategy=strategy, random_state=random_state,
                     k_neighbors=SMOTE_K_NEIGHBORS)
    if name == "adasyn":
        return ADASYN(sampling_strategy=strategy, random_state=random_state)
    raise ValueError(f"Unknown oversampler '{name}'")


def oversample(X, y, name, n_target, minority_label=1, random_state=None):
    """Classic oversampling: returns the full resampled training set."""
    sampler = make_oversampler(name, n_target, minority_label, random_state)
    return sampler.fit_resample(X.reset_index(drop=True), y.reset_index(drop=True))


def synthetic_pool(X, y, name, n_target, minority_label=1, random_state=None):
    """Return ONLY the synthetic rows added by the oversampler (the ACO pool)."""
    X_res, y_res = oversample(X, y, name, n_target, minority_label, random_state)
    n_real = len(X)
    return (X_res.iloc[n_real:].reset_index(drop=True),
            y_res.iloc[n_real:].reset_index(drop=True))


def shs_rus(X, y, name, n_target, minority_label=1, random_state=None):
    """Sequential Hybrid Sampling with Random Undersampling: oversample the
    minority beyond the majority, then randomly reduce it back to balance."""
    X_over, y_over = oversample(X, y, name, n_target, minority_label, random_state)
    # After oversampling, the original minority EXCEEDS the majority, so the
    # default 'auto' strategy cuts that surplus back down to balance.
    rus = RandomUnderSampler(random_state=random_state)
    return rus.fit_resample(X_over, y_over)


def combined_hybrid(X, y, name, random_state=None):
    """Established one-shot hybrids used as comparison baselines."""
    if name == "smote-enn":
        sampler = SMOTEENN(random_state=random_state,
                           smote=SMOTE(random_state=random_state,
                                       k_neighbors=SMOTE_K_NEIGHBORS))
    elif name == "smote-tomek":
        sampler = SMOTETomek(random_state=random_state,
                             smote=SMOTE(random_state=random_state,
                                         k_neighbors=SMOTE_K_NEIGHBORS))
    else:
        raise ValueError(f"Unknown hybrid '{name}'")
    return sampler.fit_resample(X.reset_index(drop=True), y.reset_index(drop=True))
