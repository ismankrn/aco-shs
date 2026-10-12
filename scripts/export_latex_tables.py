"""Generate the LaTeX tables for the paper-2 manuscript scaffold.

Every table is recomputed from results/runs_*.csv (same logic as
scripts/export_manuscript_tables.py) and written as a standalone booktabs
tabular to manuscript/latex/tables/*.tex, which main.tex \\input{}s.
Rerun after any change to the results CSVs:

    python scripts/export_latex_tables.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

OUT = Path("manuscript/latex/tables")
DATASETS = ["nr", "gpcr", "ic", "enzyme"]
DLABEL = {"nr": "NR", "gpcr": "GPCR", "ic": "IC", "enzyme": "Enzyme"}
FACTS = {"nr": (54, 26, 90), "gpcr": (223, 95, 635),
         "ic": (210, 204, 1476), "enzyme": (445, 664, 2926)}
METHODS = [
    "baseline", "ros", "smote", "adasyn", "smote-enn", "smote-tomek",
    "shs-rus-ros", "shs-rus-smote", "shs-rus-adasyn",
    "shs-aco-ros", "shs-aco-smote", "shs-aco-adasyn", "shs-sa-smote",
]
MLABEL = {
    "baseline": "Baseline (no resampling)", "ros": "ROS", "smote": "SMOTE",
    "adasyn": "ADASYN", "smote-enn": "SMOTE-ENN", "smote-tomek": "SMOTE-Tomek",
    "shs-rus-ros": "SHS-RUS (ROS)", "shs-rus-smote": "SHS-RUS (SMOTE)",
    "shs-rus-adasyn": "SHS-RUS (ADASYN)", "shs-aco-ros": "SHS-ACO (ROS)",
    "shs-aco-smote": "SHS-ACO (SMOTE)", "shs-aco-adasyn": "SHS-ACO (ADASYN)",
    "shs-sa-smote": "SHS-SA (SMOTE)",
}


def ms(s, dec=4):
    return f"{s.mean():.{dec}f} $\\pm$ {s.std():.{dec}f}"


def human_time(sec):
    if sec < 60:
        return f"{sec:.1f}\\,s"
    if sec < 3600:
        return f"{sec / 60:.1f}\\,min"
    return f"{sec / 3600:.1f}\\,h"


def fmt_p(p):
    if pd.isna(p):
        return "--"
    return f"{p:.4f}" if p >= 0.0001 else f"{p:.1e}"


def tabular(cols, rows, align=None):
    align = align or "l" + "c" * (len(cols) - 1)
    lines = [f"\\begin{{tabular}}{{{align}}}", "\\toprule",
             " & ".join(cols) + " \\\\", "\\midrule"]
    for r in rows:
        if r == "MIDRULE":
            lines.append("\\midrule")
        else:
            lines.append(" & ".join(str(v) for v in r) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def write(name, text):
    (OUT / name).write_text(text)
    print(f"written: {OUT / name}")


def t_datasets(p3):
    rows = []
    for d in DATASETS:
        drugs, targets, pos = FACTS[d]
        pairs = drugs * targets
        b = p3[(p3.dataset == d) & (p3.method == "baseline")].iloc[0]
        test_pos = int(b.tp + b.fn)
        rows.append([DLABEL[d], drugs, targets, f"{pairs:,}", f"{pos:,}",
                     f"{100 * pos / pairs:.2f}", f"{pos - test_pos:,}",
                     f"{test_pos:,}"])
    write("t_datasets.tex", tabular(
        ["Dataset", "Drugs", "Targets", "Pairs", "Positives",
         "Positive rate (\\%)", "Train positives", "Test positives"], rows))


def t_reproduction():
    p0 = pd.read_csv("results/runs_p0.csv")
    rep = p0[(p0.legacy) & (p0.target == 1500) & (p0.model == "gb")]
    rep = rep.sort_values("seed")
    rows = [[int(r.seed), f"{r.f1:.4f}", f"{r.gmean:.4f}", f"{r.bas:.4f}",
             f"{r.auprc:.4f}"] for r in rep.itertuples()]
    rows.append("MIDRULE")
    rows.append(["Mean $\\pm$ SD", ms(rep.f1), ms(rep.gmean), ms(rep.bas),
                 ms(rep.auprc)])
    write("t_reproduction.tex", tabular(
        ["Seed", "F1", "G-Mean", "BAS", "AUPRC"], rows))


def t_ablation():
    p1 = pd.read_csv("results/runs_p1_merged.csv")
    fact = p1[p1.fitness_fn == "f1"]
    rows = []
    for factor, label in [("legacy", "Pheromone rule (standard vs legacy)"),
                          ("stratified", "Fitness CV (plain vs stratified)"),
                          ("replacement",
                           "Selection (w/o vs with replacement)")]:
        others = [f for f in ["legacy", "stratified", "replacement"]
                  if f != factor]
        piv = fact.pivot_table(index=others + ["seed"], columns=factor,
                               values="f1").dropna()
        _, p = stats.wilcoxon(piv[False], piv[True])
        rows.append([label, f"{piv[False].mean():.4f}",
                     f"{piv[True].mean():.4f}", len(piv), fmt_p(p)])
    ref = fact[(~fact.legacy) & (fact.stratified) & (fact.replacement)]
    leg = fact[(fact.legacy) & (~fact.stratified) & (fact.replacement)]
    piv = pd.merge(ref[["seed", "f1"]], leg[["seed", "f1"]], on="seed",
                   suffixes=("_ref", "_leg"))
    _, p = stats.wilcoxon(piv.f1_ref, piv.f1_leg)
    rows.append(["Refined vs thesis-like configuration",
                 f"{piv.f1_leg.mean():.4f}", f"{piv.f1_ref.mean():.4f}",
                 len(piv), fmt_p(p)])
    rows.append("MIDRULE")
    for fn in ["f1", "gmean", "bas"]:
        sub = p1[(p1.fitness_fn == fn) & (~p1.legacy) & (p1.stratified)
                 & (p1.replacement)]
        rows.append([f"Fitness function = {fn.upper()}", "--",
                     f"{sub.f1.mean():.4f}", len(sub), "--"])
    write("t_ablation.tex", tabular(
        ["Comparison", "F1 (variant A)", "F1 (variant B)", "$n$",
         "$p$ (Wilcoxon)"], rows))


def t_sensitivity():
    p2b = pd.read_csv("results/runs_p2b.csv")
    p2 = pd.read_csv("results/runs_p2.csv")
    aco = p2b[p2b.method == "shs-aco-smote"]
    default = p2[(p2.method == "shs-aco-smote") & (p2.target == 1378)]
    variants = [("Default ($\\rho$=0.8, $K$=20)", default),
                ("$\\rho$ = 0.5", aco[aco.rho == 0.5]),
                ("$\\rho$ = 0.95", aco[aco.rho == 0.95]),
                ("$K$ = 10", aco[aco.ants == 10]),
                ("$K$ = 40", aco[aco.ants == 40]),
                ("SA (budget-matched)",
                 p2b[p2b.method == "shs-sa-smote"])]
    rows = []
    for name, sub in variants:
        if name.startswith("Default"):
            p = None
        else:
            piv = pd.merge(default[["seed", "f1"]], sub[["seed", "f1"]],
                           on="seed", suffixes=("_d", "_v"))
            _, p = stats.wilcoxon(piv.f1_d, piv.f1_v)
        rows.append([name, ms(sub.f1), fmt_p(np.nan if p is None else p),
                     human_time(sub.runtime_s.mean())])
    write("t_sensitivity.tex", tabular(
        ["Variant", "F1 (mean $\\pm$ SD)", "$p$ vs default",
         "Runtime/seed"], rows))


def t_ratio():
    p2 = pd.read_csv("results/runs_p2.csv")
    p2["ratio"] = (p2.target / 919).round(2)
    ratios = sorted(p2.ratio.unique())
    rows = []
    for m in [m for m in METHODS if m in p2.method.unique()]:
        g = p2[p2.method == m].groupby("ratio").f1
        best = g.mean().idxmax()
        row = [MLABEL[m]]
        for r in ratios:
            cell = ms(g.get_group(r))
            row.append(f"\\textbf{{{cell}}}" if r == best else cell)
        rows.append(row)
    write("t_ratio.tex", tabular(
        ["Method"] + [f"Ratio {r:.2f}" for r in ratios], rows))


def t_main(p3, metric="f1", fname="t_main_f1.tex"):
    win = {d: p3[p3.dataset == d].groupby("method")[metric].mean().idxmax()
           for d in DATASETS}
    rows = []
    for m in METHODS:
        sub = p3[p3.method == m]
        n = int(sub.groupby("dataset").seed.count().iloc[0])
        row = [MLABEL[m], n]
        for d in DATASETS:
            cell = ms(sub[sub.dataset == d][metric])
            row.append(f"\\textbf{{{cell}}}" if win[d] == m else cell)
        rows.append(row)
    write(fname, tabular(
        ["Method", "$n$"] + [DLABEL[d] for d in DATASETS], rows))


def t_tests(p3):
    rows = []
    for d in DATASETS:
        means = p3[p3.dataset == d].groupby("method").f1.mean().sort_values(
            ascending=False)
        winner, runner = means.index[0], means.index[1]

        def wilc(a, b):
            piv = p3[(p3.dataset == d) & p3.method.isin([a, b])].pivot_table(
                index="seed", columns="method", values="f1").dropna()
            if (piv[a] - piv[b]).abs().sum() == 0:
                return len(piv), np.nan
            return len(piv), stats.wilcoxon(piv[a], piv[b])[1]

        n_r, p_r = wilc(winner, runner)
        p_b = np.nan
        if winner != "baseline":
            _, p_b = wilc(winner, "baseline")
        rows.append([DLABEL[d], MLABEL[winner], f"{means.iloc[0]:.4f}",
                     MLABEL[runner], fmt_p(p_r),
                     f"{means.get('baseline'):.4f}", fmt_p(p_b)])
    write("t_tests.tex", tabular(
        ["Dataset", "Best method", "F1", "Runner-up",
         "$p$ (vs runner-up)", "F1 baseline", "$p$ (vs baseline)"], rows))


def t_sa_vs_aco(p3):
    rows = []
    for d in DATASETS:
        piv = p3[(p3.dataset == d)
                 & p3.method.isin(["shs-aco-smote", "shs-sa-smote"])
                 ].pivot_table(index="seed", columns="method",
                               values="f1").dropna()
        a, b = piv["shs-aco-smote"], piv["shs-sa-smote"]
        _, p = stats.wilcoxon(a, b)
        rows.append([DLABEL[d], f"{a.mean():.4f}", f"{b.mean():.4f}",
                     f"{a.mean() - b.mean():+.4f}", len(piv), fmt_p(p)])
    write("t_sa_vs_aco.tex", tabular(
        ["Dataset", "F1 SHS-ACO (SMOTE)", "F1 SHS-SA (SMOTE)",
         "Diff.", "$n$", "$p$ (Wilcoxon)"], rows))


def t_runtime(p3):
    base = {d: p3[(p3.dataset == d) & (p3.method == "baseline")]
            .runtime_s.mean() for d in DATASETS}
    rows = []
    for m in METHODS:
        row = [MLABEL[m]]
        for d in DATASETS:
            s = p3[(p3.method == m) & (p3.dataset == d)].runtime_s.mean()
            row.append(f"{human_time(s)} ({s / base[d]:.0f}$\\times$)")
        rows.append(row)
    write("t_runtime.tex", tabular(
        ["Method"] + [DLABEL[d] for d in DATASETS], rows,
        align="l" + "r" * len(DATASETS)))


def t_abstention(p3):
    enz = p3[p3.dataset == "enzyme"]
    base = enz[enz.method == "baseline"].set_index("seed")
    rows = []
    for seed in sorted(enz[enz.method == "shs-aco-smote"].seed.unique()):
        b = base.loc[seed]
        row = [int(seed), f"{b.f1:.4f}"]
        for m in ["shs-aco-ros", "shs-aco-smote", "shs-aco-adasyn"]:
            r = enz[(enz.method == m) & (enz.seed == seed)].iloc[0]
            same = all(int(r[k]) == int(b[k]) for k in
                       ("tp", "fp", "tn", "fn"))
            row.append("identical" if same else "\\textbf{DIFFERENT}")
        sa = enz[(enz.method == "shs-sa-smote") & (enz.seed == seed)]
        row.append(f"{sa.iloc[0].f1:.4f}" if len(sa) else "--")
        rows.append(row)
    write("t_abstention.tex", tabular(
        ["Seed", "F1 baseline", "ACO (ROS)", "ACO (SMOTE)", "ACO (ADASYN)",
         "F1 SHS-SA (SMOTE)"], rows))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p3 = pd.read_csv("results/runs_p3.csv")
    t_datasets(p3)
    t_reproduction()
    t_ablation()
    t_sensitivity()
    t_ratio()
    t_main(p3)
    t_tests(p3)
    t_sa_vs_aco(p3)
    t_runtime(p3)
    t_abstention(p3)
    # Supplementary metric matrices.
    for metric in ("gmean", "bas", "auprc"):
        t_main(p3, metric=metric, fname=f"s_{metric}.tex")


if __name__ == "__main__":
    main()
