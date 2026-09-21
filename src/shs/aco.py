"""ACO-based undersampling of a synthetic oversampling pool (Sequential Hybrid Sampling).

Refactored from the thesis implementation (`Thesis/For Thesis/oversampling_aco.py`).
Differences from the thesis code, each controllable via a flag so the original
behavior can be reproduced exactly:

- `legacy_pheromone=False` uses the standard evaporation rule
  tau_new = (1 - rho) * tau_old + delta, as written in the manuscript (Eq. 3).
  The thesis code implemented tau_new = (1 - rho * tau_old) + delta instead;
  pass `legacy_pheromone=True` to reproduce it.
- `stratified=True` uses StratifiedKFold for the fitness cross-validation.
  The thesis code used plain KFold, which with ~6% positives can produce
  folds without a single positive test sample.
- `replacement=False` selects synthetic instances without replacement.
  The thesis code sampled with replacement (`random.choices`), so an ant's
  solution could contain duplicated synthetic rows.
"""

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import KFold, StratifiedKFold

from .metrics import fitness_score


class ACOUndersampler:
    """Select the most informative synthetic instances from an oversampling pool.

    The pool (`pool_X`, `pool_y`) holds only the synthetic minority rows produced
    by an oversampler. The selector picks `n_majority - n_minority` of them so the
    training set (original + selected synthetic) becomes balanced, guided by
    pheromone values updated from a cross-validated fitness on the original data.
    """

    def __init__(self, init_pheromone=0.3, rho=0.8, n_ants=20, max_iter=10,
                 max_idle=5, cv=5, fitness="f1", stratified=True,
                 replacement=True, legacy_pheromone=False,
                 random_state=None, verbose=False):
        self.init_pheromone = init_pheromone
        self.rho = rho
        self.n_ants = n_ants
        self.max_iter = max_iter
        self.max_idle = max_idle
        self.cv = cv
        self.fitness = fitness
        self.stratified = stratified
        self.replacement = replacement
        self.legacy_pheromone = legacy_pheromone
        self.random_state = random_state
        self.verbose = verbose

    # ------------------------------------------------------------------ #

    def _cv_fitness(self, model, X_train, y_train, extra_X=None, extra_y=None):
        """Mean fitness over CV folds of the ORIGINAL training data.

        The candidate synthetic rows (`extra_*`) are added to each fold's
        training part only; validation is always on original samples.
        """
        splitter_cls = StratifiedKFold if self.stratified else KFold
        kf = splitter_cls(n_splits=self.cv, shuffle=True, random_state=self.random_state)
        scores = []
        for tr_idx, te_idx in kf.split(X_train, y_train if self.stratified else None):
            X_tr, y_tr = X_train.iloc[tr_idx], y_train.iloc[tr_idx]
            if extra_X is not None:
                X_tr = pd.concat([X_tr, extra_X], ignore_index=True)
                y_tr = pd.concat([y_tr, extra_y], ignore_index=True)
            est = clone(model)
            est.fit(X_tr, y_tr)
            y_pred = est.predict(X_train.iloc[te_idx])
            scores.append(fitness_score(self.fitness, y_train.iloc[te_idx], y_pred))
        return float(np.mean(scores))

    # ------------------------------------------------------------------ #

    def fit_resample(self, X_train, y_train, pool_X, pool_y, model,
                     minority_label=1):
        """Return a balanced (X, y) built from X_train plus selected pool rows."""
        X_train = X_train.reset_index(drop=True)
        y_train = y_train.reset_index(drop=True)
        pool_X = pool_X.reset_index(drop=True)
        pool_y = pool_y.reset_index(drop=True)

        rng = np.random.default_rng(self.random_state)
        counts = y_train.value_counts()
        n_minority = int(counts.get(minority_label, 0))
        n_majority = int(counts.drop(index=minority_label).sum())
        n_select = n_majority - n_minority
        n_pool = len(pool_X)
        if n_select <= 0:
            raise ValueError("Training data is already balanced; nothing to select.")
        if not self.replacement and n_select > n_pool:
            raise ValueError(f"Pool too small: need {n_select}, have {n_pool}.")

        pheromone = np.full(n_pool, self.init_pheromone, dtype=float)

        # Baseline: original data only.
        best_fitness = self._cv_fitness(model, X_train, y_train)
        best_ids = None
        self.history_ = [best_fitness]

        idle = 0
        for it in range(self.max_iter):
            prob = pheromone / pheromone.sum()
            delta = np.zeros(n_pool)
            iter_best_fitness, iter_best_ids = 0.0, None

            for _ in range(self.n_ants):
                chosen = rng.choice(n_pool, size=n_select,
                                    replace=self.replacement, p=prob)
                fit = self._cv_fitness(model, X_train, y_train,
                                       pool_X.iloc[chosen], pool_y.iloc[chosen])
                np.add.at(delta, chosen, fit)
                if fit > iter_best_fitness:
                    iter_best_fitness, iter_best_ids = fit, chosen

            if self.legacy_pheromone:
                pheromone = (1.0 - self.rho * pheromone) + delta
            else:
                pheromone = (1.0 - self.rho) * pheromone + delta
            pheromone = np.clip(pheromone, 1e-12, None)

            self.history_.append(iter_best_fitness)
            if self.verbose:
                print(f"[ACO] iter {it + 1}/{self.max_iter}: "
                      f"best_found={iter_best_fitness:.4f} best={best_fitness:.4f}")

            if iter_best_fitness > best_fitness:
                best_fitness, best_ids, idle = iter_best_fitness, iter_best_ids, 0
            else:
                idle += 1
                if idle > self.max_idle:
                    break

        self.best_fitness_ = best_fitness
        self.selected_ids_ = best_ids
        if best_ids is None:  # no ant beat the plain-data baseline
            return X_train, y_train
        X_res = pd.concat([X_train, pool_X.iloc[best_ids]], ignore_index=True)
        y_res = pd.concat([y_train, pool_y.iloc[best_ids]], ignore_index=True)
        return X_res, y_res
