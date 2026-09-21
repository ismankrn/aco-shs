"""Aggregate results/runs.csv into summary tables and significance tests.

Outputs:
- results/summary.csv        mean +/- std per (dataset, method) for each metric
- printed Wilcoxon signed-rank tests (per dataset, best method vs the others,
  paired over seeds)
- printed Friedman test across methods (blocks = dataset x seed), when at
  least three methods share complete blocks

Usage:
    python scripts/aggregate_results.py [--runs results/runs.csv] [--metric f1]
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

METRICS = ["f1", "gmean", "bas", "auprc", "accuracy"]


def summarize(df):
    g = df.groupby(["dataset", "method"])
    parts = []
    for metric in METRICS:
        s = g[metric].agg(["mean", "std", "count"])
        s.columns = [f"{metric}_{c}" for c in s.columns]
        parts.append(s)
    return pd.concat(parts, axis=1).reset_index()


def wilcoxon_vs_best(df, metric):
    for ds, sub in df.groupby("dataset"):
        pivot = sub.pivot_table(index="seed", columns="method", values=metric)
        pivot = pivot.dropna(axis=1)
        if pivot.shape[1] < 2 or pivot.shape[0] < 5:
            print(f"[{ds}] not enough paired seeds/methods for Wilcoxon "
                  f"({pivot.shape[0]} seeds, {pivot.shape[1]} methods)")
            continue
        best = pivot.mean().idxmax()
        print(f"\n[{ds}] Wilcoxon signed-rank on {metric}, "
              f"best = {best} (mean {pivot[best].mean():.4f}):")
        for m in pivot.columns:
            if m == best:
                continue
            try:
                stat, pval = stats.wilcoxon(pivot[best], pivot[m])
                flag = " *" if pval < 0.05 else ""
                print(f"  vs {m:<18} mean {pivot[m].mean():.4f}  p={pval:.4f}{flag}")
            except ValueError as e:  # identical samples
                print(f"  vs {m:<18} skipped ({e})")


def friedman(df, metric):
    pivot = df.pivot_table(index=["dataset", "seed"], columns="method",
                           values=metric).dropna()
    if pivot.shape[1] < 3 or pivot.shape[0] < 2:
        print("\nFriedman test skipped: need >=3 methods with complete blocks.")
        return
    stat, pval = stats.friedmanchisquare(*[pivot[c] for c in pivot.columns])
    print(f"\nFriedman test on {metric} over {pivot.shape[0]} blocks, "
          f"{pivot.shape[1]} methods: chi2={stat:.3f}, p={pval:.6f}")
    ranks = pivot.rank(axis=1, ascending=False).mean().sort_values()
    print("Mean ranks (lower is better):")
    for m, r in ranks.items():
        print(f"  {m:<20} {r:.2f}")
    try:
        import scikit_posthocs as sp
        nemenyi = sp.posthoc_nemenyi_friedman(pivot.values)
        nemenyi.index = nemenyi.columns = pivot.columns
        print("\nNemenyi post-hoc p-values:")
        print(nemenyi.round(4).to_string())
    except ImportError:
        print("(install scikit-posthocs for the Nemenyi post-hoc table)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", default="results/runs.csv")
    p.add_argument("--metric", default="f1", choices=METRICS)
    args = p.parse_args()

    df = pd.read_csv(args.runs)
    summary = summarize(df)
    out = Path(args.runs).parent / "summary.csv"
    summary.to_csv(out, index=False)

    disp = summary[["dataset", "method"]].copy()
    for metric in METRICS:
        disp[metric] = (summary[f"{metric}_mean"].map("{:.4f}".format) + " ± "
                        + summary[f"{metric}_std"].fillna(0).map("{:.4f}".format))
    print(disp.to_string(index=False))
    print(f"\nSummary written to {out}")

    wilcoxon_vs_best(df, args.metric)
    friedman(df, args.metric)


if __name__ == "__main__":
    main()
