"""Simulated-annealing undersampling of a synthetic oversampling pool.

Budget-matched comparator for `ACOUndersampler` (cf. SAUS, Chennuru &
Timmappareddy 2022): same solution space (a length-`n_select` index multiset
over the pool), the same cross-validated fitness (`cv_fitness`), and a total
number of fitness evaluations equal to the ACO budget (K ants x N iterations,
200 by default), so any performance difference is attributable to the search
strategy alone.

Search: start from a random selection; a neighbor resamples a small fraction
of positions; accept improvements always and deteriorations with Boltzmann
probability exp(delta/T) under a geometric cooling schedule from `t0` to
`t_end` across the budget. The best solution ever seen is returned.
"""

import numpy as np
import pandas as pd

from .aco import cv_fitness


class SAUndersampler:
    def __init__(self, budget=200, t0=0.05, t_end=0.001, move_frac=0.05,
                 cv=5, fitness="f1", stratified=True, replacement=True,
                 random_state=None, verbose=False):
        self.budget = budget
        self.t0 = t0
        self.t_end = t_end
        self.move_frac = move_frac
        self.cv = cv
        self.fitness = fitness
        self.stratified = stratified
        self.replacement = replacement
        self.random_state = random_state
        self.verbose = verbose

    def _fitness(self, model, X, y, pool_X, pool_y, sol):
        return cv_fitness(model, X, y, pool_X.iloc[sol], pool_y.iloc[sol],
                          cv=self.cv, fitness=self.fitness,
                          stratified=self.stratified,
                          random_state=self.random_state)

    def _neighbor(self, sol, n_pool, rng):
        new = sol.copy()
        m = max(1, int(round(self.move_frac * len(sol))))
        pos = rng.choice(len(sol), size=m, replace=False)
        if self.replacement:
            new[pos] = rng.choice(n_pool, size=m, replace=True)
        else:
            outside = np.setdiff1d(np.arange(n_pool), sol, assume_unique=False)
            m_eff = min(m, len(outside))
            if m_eff == 0:
                return new
            new[pos[:m_eff]] = rng.choice(outside, size=m_eff, replace=False)
        return new

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

        alpha = (self.t_end / self.t0) ** (1.0 / max(self.budget - 1, 1))

        current = rng.choice(n_pool, size=n_select, replace=self.replacement)
        cur_fit = self._fitness(model, X_train, y_train, pool_X, pool_y, current)
        best, best_fit = current.copy(), cur_fit
        self.history_ = [best_fit]

        for step in range(1, self.budget):
            temp = self.t0 * alpha ** step
            cand = self._neighbor(current, n_pool, rng)
            cand_fit = self._fitness(model, X_train, y_train, pool_X, pool_y, cand)
            delta = cand_fit - cur_fit
            if delta >= 0 or rng.random() < np.exp(delta / temp):
                current, cur_fit = cand, cand_fit
            if cand_fit > best_fit:
                best, best_fit = cand.copy(), cand_fit
            self.history_.append(best_fit)
            if self.verbose and step % 20 == 0:
                print(f"[SA] eval {step}/{self.budget}: T={temp:.4f} "
                      f"current={cur_fit:.4f} best={best_fit:.4f}")

        self.best_fitness_ = best_fit
        self.selected_ids_ = best
        X_res = pd.concat([X_train, pool_X.iloc[best]], ignore_index=True)
        y_res = pd.concat([y_train, pool_y.iloc[best]], ignore_index=True)
        return X_res, y_res
