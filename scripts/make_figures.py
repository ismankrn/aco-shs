"""Generate manuscript figures F1 (gradient) and F3 (convergence).

F1  manuscript/F1_gradient.{pdf,png}
    Delta-F1 vs baseline of the best method per family, across the four
    datasets ordered by real minority richness in the training split
    (63 / 444 / 1,033 / 2,048 positives). Computed from results/runs_p3.csv.

F3  manuscript/F3_convergence.{pdf,png}
    Best-so-far internal CV fitness vs number of fitness evaluations for
    the budget-matched pair on NR (200 evaluations each): ACO default
    (K=20 ants x N=10 iterations, P2 logs) vs SA (P2b logs), 5 seeds.
    Parsed from the verbose traces evacuated from the server.

Usage:
    python scripts/make_figures.py
"""

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

OUT = Path("manuscript")
DATASETS = ["nr", "gpcr", "ic", "enzyme"]
LABELS = {"nr": "NR", "gpcr": "GPCR", "ic": "IC", "enzyme": "Enzyme"}
TRAIN_POS = {"nr": 63, "gpcr": 444, "ic": 1033, "enzyme": 2048}
ARM = {"ros": "ROS", "smote": "SMOTE", "adasyn": "ADASYN",
       "smote-enn": "SMOTE-ENN", "smote-tomek": "SMOTE-Tomek",
       "shs-rus-ros": "ROS", "shs-rus-smote": "SMOTE",
       "shs-rus-adasyn": "ADASYN", "shs-aco-ros": "ROS",
       "shs-aco-smote": "SMOTE", "shs-aco-adasyn": "ADASYN",
       "shs-sa-smote": "SMOTE"}

FAMILIES = [
    ("Plain oversampling", ["ros", "smote", "adasyn"], "#999999", "o"),
    ("Cleaning hybrids", ["smote-enn", "smote-tomek"], "#CC79A7", "s"),
    ("SHS-RUS", ["shs-rus-ros", "shs-rus-smote", "shs-rus-adasyn"],
     "#009E73", "^"),
    ("SHS-SA", ["shs-sa-smote"], "#E69F00", "D"),
    ("SHS-ACO", ["shs-aco-ros", "shs-aco-smote", "shs-aco-adasyn"],
     "#0072B2", "v"),
]


def fig_gradient():
    p3 = pd.read_csv("results/runs_p3.csv")
    means = p3.groupby(["dataset", "method"]).f1.mean()
    x = [TRAIN_POS[d] for d in DATASETS]

    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    ax.axhline(0, color="black", lw=0.8, zorder=1)

    tops = {d: -1.0 for d in DATASETS}
    for name, methods, color, marker in FAMILIES:
        ys = []
        for d in DATASETS:
            sub = means[d][[m for m in methods if m in means[d]]]
            dy = sub.max() - means[d]["baseline"]
            ys.append(dy)
            tops[d] = max(tops[d], dy)
        ax.plot(x, ys, marker=marker, color=color, lw=1.6, ms=5,
                label=name, zorder=3)

    # Overall winning oversampler per dataset, annotated above the lines.
    for d in DATASETS:
        winner = means[d].idxmax()
        label = ("none\n(baseline)" if winner == "baseline"
                 else ARM.get(winner, winner))
        ax.annotate(label, (TRAIN_POS[d], tops[d]),
                    textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=7.5, color="#444444", fontweight="bold")

    # Abstention callout on the SHS-ACO Enzyme point.
    aco_enz = (means["enzyme"][["shs-aco-ros", "shs-aco-smote",
                                "shs-aco-adasyn"]].max()
               - means["enzyme"]["baseline"])
    ax.annotate("ACO abstains\n(returns original data)",
                xy=(TRAIN_POS["enzyme"], aco_enz),
                xytext=(620, 0.035), fontsize=7.5, ha="center",
                color="#0072B2",
                arrowprops=dict(arrowstyle="->", color="#0072B2", lw=0.9,
                                shrinkB=4))

    ax.set_xscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{TRAIN_POS[d]:,}\n{LABELS[d]}" for d in DATASETS])
    ax.minorticks_off()
    ax.set_ylim(top=max(tops.values()) + 0.035)
    ax.set_xlabel("Real minority (positive) interactions in the training split")
    ax.set_ylabel("$\\Delta$F1 of best method in family vs. baseline")
    ax.legend(frameon=False, fontsize=8, loc="center left",
              bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"F1_gradient.{ext}")
    plt.close(fig)
    print("written: F1_gradient.pdf/png")


RE_ACO = re.compile(r"\[ACO\] iter (\d+)/(\d+): best_found=([0-9.]+) "
                    r"best=([0-9.]+)")
RE_SA = re.compile(r"\[SA\] eval (\d+)/(\d+): .*best=([0-9.]+)")
RE_SEED = re.compile(r"seed=(\d+) F1=")


def parse_aco(path, evals_per_iter):
    text = Path(path).read_text()
    rows = RE_ACO.findall(text)
    seed = int(RE_SEED.search(text).group(1))
    plain = float(rows[0][3])  # 'best' at iter 1 = plain-data fitness
    found = np.array([float(r[2]) for r in rows])
    best = np.maximum.accumulate(np.concatenate([[plain], found]))
    best = np.maximum(best, plain)
    xs = np.arange(len(best)) * evals_per_iter
    return seed, xs, best


def parse_sa(path):
    text = Path(path).read_text()
    rows = RE_SA.findall(text)
    seed = int(RE_SEED.search(text).group(1))
    xs = np.array([int(r[0]) for r in rows])
    best = np.array([float(r[2]) for r in rows])
    return seed, xs, best


def fig_convergence():
    logdir = Path("logs-server")
    aco_files = sorted(logdir.glob(
        "*nr-method-shs-aco-smote-target-ratio-1-5-model-gb-verbose-seeds*"))
    sa_files = sorted(logdir.glob(
        "*nr-method-shs-sa-smote-target-ratio-1-5-model-gb-verbose-seeds*"))
    aco = [parse_aco(f, evals_per_iter=20) for f in aco_files]  # K=20
    sa = [parse_sa(f) for f in sa_files]
    assert len(aco) == 5 and len(sa) == 5, (len(aco), len(sa))

    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    for seed, xs, best in aco:
        ax.plot(xs, best, color="#0072B2", lw=0.7, alpha=0.35, zorder=2)
    for seed, xs, best in sa:
        ax.plot(xs, best, color="#E69F00", lw=0.7, alpha=0.4, zorder=2)

    # Some seeds stop early (max_idle); extend best-so-far flat to the full
    # grid, which is exact for a monotone best-so-far curve.
    n_a = max(len(b) for _, _, b in aco)
    xs_a = np.arange(n_a) * 20
    mean_a = np.mean([np.pad(b, (0, n_a - len(b)), mode="edge")
                      for _, _, b in aco], axis=0)
    ax.plot(xs_a, mean_a, color="#0072B2", lw=2.2, marker="o", ms=3.5,
            label="ACO (K=20 ants × N=10 iterations)", zorder=4)

    # SA logs print every 20 evals (20..180); align on the common grid.
    xs_s = sa[0][1]
    mean_s = np.mean([b for _, _, b in sa], axis=0)
    ax.plot(xs_s, mean_s, color="#E69F00", lw=2.2, marker="s", ms=3.5,
            label="SA (budget-matched)", zorder=4)

    # Plain-data fitness reference (ACO's abstention threshold), mean of seeds.
    plain = np.mean([b[0] for _, _, b in aco])
    ax.axhline(plain, color="#555555", lw=0.9, ls="--", zorder=1)
    ax.text(198, plain, "plain-data fitness (ACO abstention threshold)",
            fontsize=7.5, color="#555555", ha="right", va="bottom")

    ax.set_xlim(0, 205)
    ax.set_xticks(range(0, 201, 40))
    ax.set_xlabel("Fitness evaluations (shared budget = 200)")
    ax.set_ylabel("Best-so-far internal CV fitness (F1)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"F3_convergence.{ext}")
    plt.close(fig)
    print("written: F3_convergence.pdf/png")
    print(f"  plain-data fitness (mean): {plain:.4f}")
    print(f"  ACO final best (mean): {mean_a[-1]:.4f} at eval {xs_a[-1]}")
    print(f"  SA last logged best (mean): {mean_s[-1]:.4f} at eval {xs_s[-1]}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_gradient()
    fig_convergence()
