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


def fig_ratio():
    """F2: oversampling-pool ratio x selector interaction on NR (P2)."""
    p2 = pd.read_csv("results/runs_p2.csv")
    n_majority = 919  # NR train negatives
    p2["ratio"] = (p2.target / n_majority).round(2)
    arm_color = {"ros": "#D55E00", "smote": "#0072B2", "adasyn": "#009E73"}
    sel_style = {"rus": dict(ls="--", marker="o", mfc="white"),
                 "aco": dict(ls="-", marker="o")}

    fig, ax = plt.subplots(figsize=(5.4, 3.9))
    for sel in ("rus", "aco"):
        for arm in ("ros", "smote", "adasyn"):
            g = (p2[p2.method == f"shs-{sel}-{arm}"]
                 .groupby("ratio").f1.mean().sort_index())
            ax.plot(g.index, g.values, color=arm_color[arm], lw=1.6, ms=5,
                    label=f"SHS-{sel.upper()} ({arm.upper()})",
                    **sel_style[sel])

    ax.set_xticks([1.0, 1.25, 1.5])
    ax.set_xlabel("Synthetic pool size ratio "
                  "(pool size / majority training size)")
    ax.set_ylabel("F1 (mean over seeds)")
    ax.legend(frameon=False, fontsize="x-small", ncol=2, loc="lower center",
              bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"F2_ratio_interaction.{ext}")
    plt.close(fig)
    print("written: F2_ratio_interaction.pdf/png")


FAMILY_COLOR = {}
for _name, _methods, _color, _ in FAMILIES:
    for _m in _methods:
        FAMILY_COLOR[_m] = _color
FAMILY_COLOR["baseline"] = "#000000"


def fig_friedman():
    """F4: Friedman mean ranks with the Nemenyi critical difference."""
    from scipy.stats import friedmanchisquare, studentized_range

    p3 = pd.read_csv("results/runs_p3.csv")
    piv = p3.pivot_table(index=["dataset", "seed"], columns="method",
                         values="f1").dropna()
    methods = list(piv.columns)
    k, n = len(methods), len(piv)
    chi2, p = friedmanchisquare(*[piv[m] for m in methods])
    ranks = piv.rank(axis=1, ascending=False).mean().sort_values()
    # Nemenyi CD: q_alpha = studentized range (k groups, df=inf) / sqrt(2).
    q_alpha = studentized_range.ppf(0.95, k, np.inf) / np.sqrt(2)
    cd = q_alpha * np.sqrt(k * (k + 1) / (6.0 * n))

    label = {"baseline": "Baseline", "ros": "ROS", "smote": "SMOTE",
             "adasyn": "ADASYN", "smote-enn": "SMOTE-ENN",
             "smote-tomek": "SMOTE-Tomek", "shs-rus-ros": "SHS-RUS (ROS)",
             "shs-rus-smote": "SHS-RUS (SMOTE)",
             "shs-rus-adasyn": "SHS-RUS (ADASYN)",
             "shs-aco-ros": "SHS-ACO (ROS)",
             "shs-aco-smote": "SHS-ACO (SMOTE)",
             "shs-aco-adasyn": "SHS-ACO (ADASYN)",
             "shs-sa-smote": "SHS-SA (SMOTE)"}

    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    ypos = np.arange(len(ranks))[::-1]  # best on top
    for y, (m, r) in zip(ypos, ranks.items()):
        color = FAMILY_COLOR[m]
        ax.hlines(y, 0, r, color=color, lw=1.1, alpha=0.5)
        ax.plot(r, y, "o", color=color, ms=6)
        ax.annotate(f"{r:.2f}", (r, y), textcoords="offset points",
                    xytext=(7, -3), fontsize=7.5, color="#333333")

    # Methods whose rank is within CD of the best are statistically
    # indistinguishable from it (Nemenyi, alpha = 0.05).
    best = ranks.iloc[0]
    ax.axvline(best + cd, color="#777777", lw=0.9, ls="--")
    ax.text(best + cd + 0.15, ypos[0] + 0.3,
            f"best rank + CD\n(CD = {cd:.2f}, Nemenyi $\\alpha$=0.05)",
            fontsize=7.5, color="#555555", va="top")

    ax.set_yticks(ypos)
    ax.set_yticklabels([label[m] for m in ranks.index], fontsize=8)
    ax.set_xlim(0, 13)
    ax.set_xlabel(f"Mean Friedman rank over {n} dataset × seed blocks "
                  "(lower is better)")
    ax.set_title(f"Friedman $\\chi^2$ = {chi2:.1f}, p = {p:.1e}", fontsize=9,
                 loc="left")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"F4_friedman_ranks.{ext}")
    plt.close(fig)
    print("written: F4_friedman_ranks.pdf/png")
    print(f"  k={k}, N={n}, q_alpha={q_alpha:.3f}, CD={cd:.3f}")
    within = ranks[ranks <= best + cd]
    print(f"  within CD of best: {', '.join(within.index)}")


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


def _pad_mean(traces, evals_per_iter):
    """Flat-pad monotone best-so-far traces to a common grid; return x, mean."""
    n = max(len(b) for _, _, b in traces)
    xs = np.arange(n) * evals_per_iter
    mean = np.mean([np.pad(b, (0, n - len(b)), mode="edge")
                    for _, _, b in traces], axis=0)
    return xs, mean


def fig_convergence():
    logdir = Path("logs-server")
    aco_files = sorted(logdir.glob(
        "*nr-method-shs-aco-smote-target-ratio-1-5-model-gb-verbose-seeds*"))
    sa_files = sorted(logdir.glob(
        "*nr-method-shs-sa-smote-target-ratio-1-5-model-gb-verbose-seeds*"))
    k10_files = sorted(logdir.glob(
        "*nr-method-shs-aco-smote-target-ratio-1-5-model-gb-verbose-ants-10*"))
    k40_files = sorted(logdir.glob(
        "*nr-method-shs-aco-smote-target-ratio-1-5-model-gb-verbose-ants-40*"))
    aco = [parse_aco(f, evals_per_iter=20) for f in aco_files]  # K=20
    sa = [parse_sa(f) for f in sa_files]
    k10 = [parse_aco(f, evals_per_iter=10) for f in k10_files]
    k40 = [parse_aco(f, evals_per_iter=40) for f in k40_files]
    assert len(aco) == len(sa) == len(k10) == len(k40) == 5

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.6, 3.7), sharey=True)

    # ---- panel (a): budget-matched ACO vs SA ----
    for seed, xs, best in aco:
        ax.plot(xs, best, color="#0072B2", lw=0.7, alpha=0.35, zorder=2)
    for seed, xs, best in sa:
        ax.plot(xs, best, color="#E69F00", lw=0.7, alpha=0.4, zorder=2)
    xs_a, mean_a = _pad_mean(aco, 20)
    ax.plot(xs_a, mean_a, color="#0072B2", lw=2.2, marker="o", ms=3.5,
            label="ACO (K=20)", zorder=4)
    xs_s = sa[0][1]
    mean_s = np.mean([b for _, _, b in sa], axis=0)
    ax.plot(xs_s, mean_s, color="#E69F00", lw=2.2, marker="s", ms=3.5,
            label="SA (budget-matched)", zorder=4)
    plain = np.mean([b[0] for _, _, b in aco])
    ax.axhline(plain, color="#555555", lw=0.9, ls="--", zorder=1)
    ax.text(103, plain + 0.008, "plain-data fitness", fontsize=7.5,
            color="#555555", ha="center", va="bottom")
    ax.set_xlim(0, 205)
    ax.set_xticks(range(0, 201, 40))
    ax.set_xlabel("Fitness evaluations (shared budget = 200)")
    ax.set_ylabel("Best-so-far internal CV fitness (F1)")
    ax.set_title("(a) ACO vs budget-matched SA", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    # ---- panel (b): number of ants ----
    for traces, k, color in [(k10, 10, "#8FC3E4"), (aco, 20, "#0072B2"),
                             (k40, 40, "#01395C")]:
        xs, mean = _pad_mean(traces, k)
        bx.plot(xs, mean, color=color, lw=1.9, marker="o", ms=3,
                label=f"K = {k} (budget {10 * k})")
    bx.axhline(plain, color="#555555", lw=0.9, ls="--", zorder=1)
    bx.set_xlim(0, 410)
    bx.set_xticks(range(0, 401, 100))
    bx.set_xlabel("Fitness evaluations (N = 10 iterations)")
    bx.set_title("(b) Effect of the number of ants", fontsize=9, loc="left")
    bx.legend(frameon=False, fontsize=8, loc="center right")

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"F3_convergence.{ext}")
    plt.close(fig)
    print("written: F3_convergence.pdf/png (two panels)")
    print(f"  plain-data fitness (mean): {plain:.4f}")
    print(f"  final means: K20 {mean_a[-1]:.4f}; SA {mean_s[-1]:.4f}")
    for traces, k in [(k10, 10), (k40, 40)]:
        xs, mean = _pad_mean(traces, k)
        print(f"  K{k} final: {mean[-1]:.4f} at eval {xs[-1]}")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_gradient()
    fig_ratio()
    fig_convergence()
    fig_friedman()
