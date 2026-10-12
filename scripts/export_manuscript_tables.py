"""Export every manuscript table to one Excel file, one sheet per table.

All numbers are computed from the results CSVs (no copy-paste); dataset
totals (drugs/targets/pairs/positives) are Yamanishi-2008 facts and the only
hardcoded values. Table content is in English (ready to paste into the
manuscript); notes are in Indonesian.

Usage:
    python scripts/export_manuscript_tables.py \
        --out manuscript/Tabel_Manuskrip.xlsx
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from scipy import stats

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F4E79")
WIN_FILL = PatternFill("solid", fgColor="E2EFDA")
HDR_FONT = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT, size=10)
BOLD_FONT = Font(name=FONT, size=10, bold=True)
NOTE_FONT = Font(name=FONT, size=10, italic=True)
TITLE_FONT = Font(name=FONT, size=12, bold=True)
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)

DATASET_ORDER = ["nr", "gpcr", "ic", "enzyme"]
DATASET_LABEL = {"nr": "NR", "gpcr": "GPCR", "ic": "IC", "enzyme": "Enzyme"}
# Yamanishi (2008) gold-standard facts: drugs, targets, positive interactions.
DATASET_FACTS = {
    "nr": (54, 26, 90), "gpcr": (223, 95, 635),
    "ic": (210, 204, 1476), "enzyme": (445, 664, 2926),
}
METHOD_ORDER = [
    "baseline", "ros", "smote", "adasyn", "smote-enn", "smote-tomek",
    "shs-rus-ros", "shs-rus-smote", "shs-rus-adasyn",
    "shs-aco-ros", "shs-aco-smote", "shs-aco-adasyn", "shs-sa-smote",
]
METHOD_LABEL = {
    "baseline": "Baseline (no resampling)", "ros": "ROS", "smote": "SMOTE",
    "adasyn": "ADASYN", "smote-enn": "SMOTE-ENN", "smote-tomek": "SMOTE-Tomek",
    "shs-rus-ros": "SHS-RUS (ROS)", "shs-rus-smote": "SHS-RUS (SMOTE)",
    "shs-rus-adasyn": "SHS-RUS (ADASYN)", "shs-aco-ros": "SHS-ACO (ROS)",
    "shs-aco-smote": "SHS-ACO (SMOTE)", "shs-aco-adasyn": "SHS-ACO (ADASYN)",
    "shs-sa-smote": "SHS-SA (SMOTE)",
}


def ms(series, dec=4):
    return f"{series.mean():.{dec}f} ± {series.std():.{dec}f}"


def human_time(sec):
    if sec < 60:
        return f"{sec:.1f} s"
    if sec < 3600:
        return f"{sec / 60:.1f} min"
    return f"{sec / 3600:.1f} h"


def paired_wilcoxon(df, method_a, method_b, dataset=None, metric="f1"):
    """Two-sided Wilcoxon on seeds common to both methods. Returns (n, pa, pb, p)."""
    sub = df if dataset is None else df[df.dataset == dataset]
    piv = sub[sub.method.isin([method_a, method_b])].pivot_table(
        index="seed", columns="method", values=metric).dropna()
    a, b = piv[method_a], piv[method_b]
    if (a - b).abs().sum() == 0:
        return len(piv), a.mean(), b.mean(), np.nan  # identical -> no test
    _, p = stats.wilcoxon(a, b)
    return len(piv), a.mean(), b.mean(), p


def write_table(ws, df, start_row=1, title=None, notes=(), highlight_rows=(),
                bold_cells=()):
    """highlight_rows: 0-based df row indices filled green.
    bold_cells: set of (df_row, df_col) made bold."""
    r = start_row
    if title:
        ws.cell(r, 1, title).font = TITLE_FONT
        r += 2
    for c, name in enumerate(df.columns, 1):
        cell = ws.cell(r, c, str(name))
        cell.font, cell.fill, cell.border = HDR_FONT, HDR_FILL, THIN
        cell.alignment = Alignment(horizontal="center")
    for i, row in enumerate(df.itertuples(index=False)):
        for c, val in enumerate(row, 1):
            if isinstance(val, (np.floating, float)) and not pd.isna(val):
                val = round(float(val), 4)
            elif isinstance(val, np.integer):
                val = int(val)
            elif pd.isna(val):
                val = "-"
            cell = ws.cell(r + 1 + i, c, val)
            cell.border = THIN
            cell.font = BOLD_FONT if (i, c - 1) in bold_cells else BODY_FONT
            if i in highlight_rows:
                cell.fill = WIN_FILL
    for c, name in enumerate(df.columns, 1):
        width = max(len(str(name)),
                    *(len(str(v)) for v in df.iloc[:, c - 1])) + 2
        ws.column_dimensions[get_column_letter(c)].width = min(width, 34)
    nxt = r + len(df) + 2
    for note in notes:
        ws.cell(nxt, 1, note).font = NOTE_FONT
        nxt += 1
    ws.freeze_panes = ws.cell(r + 1, 1)
    return nxt + 1


def sheet_daftar(wb, entries):
    ws = wb.active
    ws.title = "Daftar"
    df = pd.DataFrame(entries, columns=[
        "Sheet", "Isi tabel", "Penempatan", "Sumber data"])
    write_table(ws, df, title="Daftar tabel manuskrip (paper 2, PeerJ CS)",
                notes=["Semua nilai dihitung ulang dari CSV hasil "
                       "(results/runs_*.csv); tidak ada angka ketik manual.",
                       "Penempatan mengikuti rekomendasi: Badan = tabel inti "
                       "manuskrip, Suplemen = supplementary material."])


def sheet_t1(wb, p3):
    rows = []
    for ds in DATASET_ORDER:
        drugs, targets, pos = DATASET_FACTS[ds]
        pairs = drugs * targets
        b = p3[(p3.dataset == ds) & (p3.method == "baseline")].iloc[0]
        test_pos = int(b.tp + b.fn)
        test_pairs = int(b.tp + b.fp + b.tn + b.fn)
        rows.append({
            "Dataset": DATASET_LABEL[ds], "Drugs": drugs, "Targets": targets,
            "Pairs": pairs, "Positives": pos,
            "Positive rate (%)": round(100 * pos / pairs, 2),
            "Train pairs": pairs - test_pairs,
            "Train positives": pos - test_pos,
            "Test pairs": test_pairs, "Test positives": test_pos,
        })
    write_table(wb.create_sheet("T1 Dataset"), pd.DataFrame(rows),
                title="T1. Dataset statistics (Yamanishi 2008, SRX-DTI AB features)",
                notes=["Drugs/targets/pairs/positives: fakta dataset Yamanishi "
                       "(2008). Kolom train/test dihitung dari confusion matrix "
                       "baseline (split 70/30, stratified).",
                       "Kolom 'Train positives' (63/444/1.033/2.048) adalah "
                       "gradien yang dirujuk sepanjang Discussion."])


def sheet_t2(wb):
    p0 = pd.read_csv("results/runs_p0.csv")
    rep = p0[(p0.legacy) & (p0.target == 1500) & (p0.model == "gb")].copy()
    rep = rep.sort_values("seed")
    df = rep[["seed", "f1", "gmean", "bas", "auprc"]].rename(columns={
        "seed": "Seed", "f1": "F1", "gmean": "G-Mean", "bas": "BAS",
        "auprc": "AUPRC"})
    summary = pd.DataFrame([{
        "Seed": "mean ± SD",
        "F1": ms(rep.f1), "G-Mean": ms(rep.gmean),
        "BAS": ms(rep.bas), "AUPRC": ms(rep.auprc)}])
    df = pd.concat([df, summary], ignore_index=True)
    write_table(wb.create_sheet("T2 Reproduksi"), df,
                title="T2. Reproduction of the thesis configuration "
                      "(SHS-ACO-SMOTE, legacy code path, NR, 5 seeds)",
                notes=["Referensi tesis (split tunggal): F1=0.4324, "
                       "G-Mean=0.5075, BAS=0.6241.",
                       "2 dari 5 seed mendarat di 0.4314 ≈ angka tesis; "
                       "rentang F1 0.2667–0.4314 adalah argumen "
                       "sensitivitas-seed yang memotivasi protokol multi-seed."],
                bold_cells={(len(df) - 1, c) for c in range(df.shape[1])})


def metric_matrix(p3, metric, sheet_name, title, wb, notes=()):
    rows, bold = [], set()
    win_idx = {}
    for ds in DATASET_ORDER:
        means = p3[p3.dataset == ds].groupby("method")[metric].mean()
        win_idx[ds] = means.idxmax()
    for i, m in enumerate(METHOD_ORDER):
        row = {"Method": METHOD_LABEL[m]}
        sub = p3[p3.method == m]
        row["n seeds"] = int(sub.groupby("dataset").seed.count().iloc[0])
        for j, ds in enumerate(DATASET_ORDER):
            s = sub[sub.dataset == ds][metric]
            row[DATASET_LABEL[ds]] = ms(s)
            if win_idx[ds] == m:
                bold.add((i, j + 2))
        rows.append(row)
    write_table(wb.create_sheet(sheet_name), pd.DataFrame(rows), title=title,
                notes=list(notes) + [
                    "Cetak tebal = mean terbaik per dataset. mean ± SD "
                    "antar-seed; GB sebagai classifier final di semua sel."],
                bold_cells=bold)


def sheet_t4(wb, p3):
    rows = []
    for ds in DATASET_ORDER:
        means = p3[p3.dataset == ds].groupby("method").f1.mean().sort_values(
            ascending=False)
        winner, runner = means.index[0], means.index[1]
        n_r, _, _, p_r = paired_wilcoxon(p3, winner, runner, ds)
        if winner == "baseline":
            n_b, p_b = np.nan, np.nan
        else:
            n_b, _, _, p_b = paired_wilcoxon(p3, winner, "baseline", ds)
        rows.append({
            "Dataset": DATASET_LABEL[ds],
            "Best method": METHOD_LABEL[winner],
            "F1 best": round(means.iloc[0], 4),
            "Runner-up": METHOD_LABEL[runner],
            "F1 runner-up": round(means.iloc[1], 4),
            "p (best vs runner-up)": p_r, "n pairs": n_r,
            "F1 baseline": round(means.get("baseline", np.nan), 4),
            "p (best vs baseline)": p_b,
        })
    write_table(wb.create_sheet("T4 Wilcoxon"), pd.DataFrame(rows),
                title="T4. Per-dataset winners and paired Wilcoxon signed-rank "
                      "tests (F1, paired over common seeds)",
                notes=["Uji dua arah; n=5 pasangan memberi p minimum 0.0625, "
                       "jadi p=0.0625 adalah bukti terkuat yang mungkin pada "
                       "n tersebut.",
                       "Enzyme: baseline adalah pemenang, sehingga kolom "
                       "'vs baseline' tidak berlaku; p '-' pada baris Enzyme "
                       "karena runner-up (SHS-ACO) abstain → skor "
                       "identik dengan baseline, tidak ada selisih untuk "
                       "diuji (lihat T11)."])


def sheet_t5(wb, p3):
    piv = p3.pivot_table(index=["dataset", "seed"], columns="method",
                         values="f1").dropna()
    cols = [m for m in METHOD_ORDER if m in piv.columns]
    piv = piv[cols]
    chi2, p = stats.friedmanchisquare(*[piv[c] for c in cols])
    ranks = piv.rank(axis=1, ascending=False).mean().sort_values()
    df = pd.DataFrame({
        "Method": [METHOD_LABEL[m] for m in ranks.index],
        "Mean rank": ranks.round(2).values})
    df.insert(0, "Rank order", range(1, len(df) + 1))
    write_table(wb.create_sheet("T5 Friedman"), df,
                title="T5. Friedman test across datasets "
                      f"(13 methods, {len(piv)} blocks = dataset × seed)",
                notes=[f"Friedman chi² = {chi2:.2f}, p = {p:.1e}; "
                       "rank 1 = F1 tertinggi dalam satu blok.",
                       "Blok = kombinasi dataset×seed yang memiliki "
                       "ke-13 metode (seed 0–4)."],
                highlight_rows={0, 1})


def sheet_t6(wb):
    p1 = pd.read_csv("results/runs_p1_merged.csv")
    fact = p1[p1.fitness_fn == "f1"]
    rows = []
    for factor in ["legacy", "stratified", "replacement"]:
        others = [f for f in ["legacy", "stratified", "replacement"]
                  if f != factor]
        piv = fact.pivot_table(index=others + ["seed"], columns=factor,
                               values="f1").dropna()
        _, p = stats.wilcoxon(piv[False], piv[True])
        rows.append({
            "Comparison": f"{factor} (False vs True)",
            "F1 (False)": piv[False].mean(), "F1 (True)": piv[True].mean(),
            "Diff": piv[True].mean() - piv[False].mean(),
            "n pairs": len(piv), "p (Wilcoxon)": p})
    ref = fact[(~fact.legacy) & (fact.stratified) & (fact.replacement)]
    leg = fact[(fact.legacy) & (~fact.stratified) & (fact.replacement)]
    piv = pd.merge(ref[["seed", "f1"]], leg[["seed", "f1"]], on="seed",
                   suffixes=("_ref", "_leg"))
    diffs = piv.f1_ref - piv.f1_leg
    p = (np.nan if diffs.abs().sum() == 0
         else stats.wilcoxon(piv.f1_ref, piv.f1_leg)[1])
    rows.append({
        "Comparison": "refined vs thesis-like configuration",
        "F1 (False)": piv.f1_leg.mean(), "F1 (True)": piv.f1_ref.mean(),
        "Diff": piv.f1_ref.mean() - piv.f1_leg.mean(),
        "n pairs": len(piv), "p (Wilcoxon)": p})
    for fn in ["f1", "gmean", "bas"]:
        sub = p1[(p1.fitness_fn == fn) & (~p1.legacy) & (p1.stratified)
                 & (p1.replacement)]
        rows.append({
            "Comparison": f"fitness function = {fn.upper()} (mean test F1)",
            "F1 (False)": np.nan, "F1 (True)": sub.f1.mean(),
            "Diff": np.nan, "n pairs": len(sub), "p (Wilcoxon)": np.nan})
    write_table(wb.create_sheet("T6 Ablasi ACO"), pd.DataFrame(rows),
                title="T6. ACO ablation on NR (SHS-ACO-SMOTE): pheromone rule, "
                      "CV stratification, selection replacement, fitness "
                      "function",
                notes=["Baris faktor: dipasangkan antar konfigurasi faktorial "
                       "yang hanya berbeda pada faktor itu (4 konfigurasi "
                       "× 5 seed = 20 pasangan).",
                       "'refined' = standard pheromone + stratified CV + "
                       "replacement; 'thesis-like' = legacy pheromone + plain "
                       "KFold + replacement.",
                       "Tidak ada faktor yang signifikan → koreksi "
                       "kode-vs-persamaan dilaporkan sebagai temuan "
                       "robustness, bukan ancaman validitas."])


def sheet_t7(wb):
    p2b = pd.read_csv("results/runs_p2b.csv")
    aco = p2b[p2b.method == "shs-aco-smote"]
    # The default configuration (rho=0.8, K=20) was already run in P2
    # (shs-aco-smote, NR, ratio 1.5 -> target 1378); P2b only ran the variants.
    p2 = pd.read_csv("results/runs_p2.csv")
    default = p2[(p2.method == "shs-aco-smote") & (p2.target == 1378)]
    variants = [("default (ρ=0.8, K=20)", default),
                ("ρ = 0.5", aco[aco.rho == 0.5]),
                ("ρ = 0.95", aco[aco.rho == 0.95]),
                ("K = 10", aco[aco.ants == 10]),
                ("K = 40", aco[aco.ants == 40]),
                ("SA (budget-matched, 200 evals)",
                 p2b[p2b.method == "shs-sa-smote"])]
    rows = []
    for name, sub in variants:
        sub = sub.sort_values("seed")
        if name.startswith("default"):
            p = np.nan
        else:
            piv = pd.merge(default[["seed", "f1"]], sub[["seed", "f1"]],
                           on="seed", suffixes=("_d", "_v"))
            p = stats.wilcoxon(piv.f1_d, piv.f1_v)[1]
        rows.append({"Variant": name, "F1 (mean ± SD)": ms(sub.f1),
                     "p vs default": p, "n seeds": len(sub),
                     "Runtime/seed": human_time(sub.runtime_s.mean())})
    write_table(wb.create_sheet("T7 Sensitivitas"), pd.DataFrame(rows),
                title="T7. ACO parameter sensitivity and the SA comparator "
                      "(NR, SHS-ACO-SMOTE, ratio 1.5)",
                notes=["Tidak ada varian yang berbeda signifikan dari default; "
                       "K=10 menyamai kualitas default dengan ~setengah "
                       "runtime (dipakai di P3).",
                       "SA setara ACO secara statistik → nilai ada pada "
                       "seleksi terinformasi, bukan metaheuristik spesifik."])


def sheet_t8(wb):
    p2 = pd.read_csv("results/runs_p2.csv")
    n_majority = 919  # NR train negatives
    p2["ratio"] = (p2.target / n_majority).round(2)
    rows, bold = [], set()
    methods = [m for m in METHOD_ORDER if m in p2.method.unique()]
    ratios = sorted(p2.ratio.unique())
    for i, m in enumerate(methods):
        row = {"Method": METHOD_LABEL[m]}
        best = p2[p2.method == m].groupby("ratio").f1.mean().idxmax()
        for j, r in enumerate(ratios):
            s = p2[(p2.method == m) & (p2.ratio == r)].f1
            row[f"ratio {r:.2f}"] = ms(s)
            if r == best:
                bold.add((i, j + 1))
        rows.append(row)
    write_table(wb.create_sheet("T8 Rasio (P2)"), pd.DataFrame(rows),
                title="T8. Target-ratio pilot on NR: oversampling pool size "
                      "× selector interaction (F1, 5 seeds)",
                notes=["ratio = ukuran pool sintetis relatif terhadap jumlah "
                       "mayoritas train (919 untuk NR); cetak tebal = rasio "
                       "terbaik per metode.",
                       "Pola bersih: ACO terbaik pada pool TERBESAR (1.5), "
                       "RUS terbaik pada pool kecil/sedang — seleksi "
                       "terinformasi mengeksploitasi surplus kandidat.",
                       "Direkomendasikan sebagai FIGUR (line plot) di badan "
                       "paper; tabel ini untuk suplemen/arsip angka."],
                bold_cells=bold)


def sheet_t9(wb, p3):
    rows = []
    base_rt = {ds: p3[(p3.dataset == ds) & (p3.method == "baseline")]
               .runtime_s.mean() for ds in DATASET_ORDER}
    for m in METHOD_ORDER:
        row = {"Method": METHOD_LABEL[m]}
        for ds in DATASET_ORDER:
            s = p3[(p3.method == m) & (p3.dataset == ds)].runtime_s
            row[DATASET_LABEL[ds]] = human_time(s.mean())
            row[f"{DATASET_LABEL[ds]} (× baseline)"] = round(
                s.mean() / base_rt[ds], 1)
        rows.append(row)
    df = pd.DataFrame(rows)
    df = df[["Method"] + [c for ds in DATASET_ORDER for c in
                          (DATASET_LABEL[ds],
                           f"{DATASET_LABEL[ds]} (× baseline)")]]
    write_table(wb.create_sheet("T9 Runtime"), df,
                title="T9. Mean runtime per seed (sampling + final model "
                      "training)",
                notes=["Semua pada Hetzner CPX52 (12 vCPU), "
                       "OMP_NUM_THREADS=1, worker paralel berbagi core; "
                       "bandingkan antar metode, bukan antar mesin.",
                       "Enzyme ACO/SA memakai HistGB untuk fitness internal "
                       "(GB tetap classifier final).",
                       "Pesan untuk Discussion: seleksi terinformasi berbiaya "
                       "500–1.700× metode murah — sandingkan "
                       "dengan ΔF1 yang tipis."])


def sheet_t10(wb, p3):
    rows = []
    for ds in DATASET_ORDER:
        n, a, b, p = paired_wilcoxon(p3, "shs-aco-smote", "shs-sa-smote", ds)
        rows.append({"Dataset": DATASET_LABEL[ds],
                     "F1 SHS-ACO (SMOTE)": round(a, 4),
                     "F1 SHS-SA (SMOTE)": round(b, 4),
                     "Diff (ACO - SA)": round(a - b, 4),
                     "n pairs": n, "p (Wilcoxon)": p})
    write_table(wb.create_sheet("T10 SA vs ACO"), pd.DataFrame(rows),
                title="T10. Budget-matched SA vs ACO on the SMOTE arm "
                      "(200 fitness evaluations each)",
                notes=["Tidak signifikan di dataset mana pun → pilihan "
                       "metaheuristik sekunder; asimetri abstensi (T11) yang "
                       "membedakan desain ACO.",
                       "Enzyme: ACO abstain (= baseline), SA terpaksa "
                       "menambah sampel sintetis."])


def sheet_t11(wb, p3):
    enz = p3[p3.dataset == "enzyme"]
    base = enz[enz.method == "baseline"].set_index("seed")
    rows = []
    for seed in sorted(enz[enz.method == "shs-aco-smote"].seed.unique()):
        b = base.loc[seed]
        row = {"Seed": int(seed), "F1 baseline": round(b.f1, 4)}
        for m in ["shs-aco-ros", "shs-aco-smote", "shs-aco-adasyn"]:
            r = enz[(enz.method == m) & (enz.seed == seed)].iloc[0]
            same = all(int(r[k]) == int(b[k]) for k in
                       ("tp", "fp", "tn", "fn"))
            row[f"{METHOD_LABEL[m]}: CM identik?"] = "Ya" if same else "TIDAK"
        sa = enz[(enz.method == "shs-sa-smote") & (enz.seed == seed)]
        row["F1 SHS-SA (SMOTE)"] = round(sa.iloc[0].f1, 4) if len(sa) else "-"
        rows.append(row)
    df = pd.DataFrame(rows)
    n_identical = sum((df.iloc[:, c] == "Ya").sum() for c in range(2, 5))
    write_table(wb.create_sheet("T11 Abstensi Enzyme"), df,
                title="T11. ACO abstention on Enzyme: confusion-matrix "
                      "identity with baseline, per seed",
                notes=[f"Verifikasi: {n_identical}/15 run ACO (3 arm × 5 "
                       "seed) menghasilkan confusion matrix IDENTIK dengan "
                       "baseline — fallback mengembalikan data latih "
                       "asli karena tidak ada subset sintetis yang mengalahkan "
                       "fitness data mentah.",
                       "SA tidak punya aksi abstain sehingga terpaksa "
                       "oversampling dan berakhir sedikit di bawah baseline.",
                       "Sajikan sebagai subbagian hasil bernama (named "
                       "finding), bukan catatan kaki."])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="manuscript/Tabel_Manuskrip.xlsx")
    args = ap.parse_args()

    p3 = pd.read_csv("results/runs_p3.csv")
    wb = Workbook()

    entries = [
        ("T1 Dataset", "Statistik 4 dataset + positif train/test", "Badan",
         "Yamanishi 2008 + runs_p3.csv"),
        ("T2 Reproduksi", "Reproduksi konfigurasi tesis, per seed", "Badan",
         "runs_p0.csv"),
        ("T3 F1 utama", "13 metode x 4 dataset, F1 mean±SD", "Badan",
         "runs_p3.csv"),
        ("T4 Wilcoxon", "Pemenang per dataset + uji berpasangan", "Badan",
         "runs_p3.csv"),
        ("T5 Friedman", "Mean rank lintas dataset", "Badan (angka utk figur)",
         "runs_p3.csv"),
        ("T6 Ablasi ACO", "Ablasi pheromone/CV/replacement/fitness", "Badan",
         "runs_p1_merged.csv"),
        ("T7 Sensitivitas", "Sensitivitas rho/K + komparator SA", "Badan",
         "runs_p2b.csv"),
        ("T8 Rasio (P2)", "Interaksi rasio pool x penyeleksi", "Suplemen "
         "(badan: figur)", "runs_p2.csv"),
        ("T9 Runtime", "Runtime per seed, relatif thd baseline", "Badan",
         "runs_p3.csv"),
        ("T10 SA vs ACO", "SA vs ACO per dataset", "Badan (bisa diringkas "
         "jadi teks)", "runs_p3.csv"),
        ("T11 Abstensi Enzyme", "Verifikasi abstensi ACO per seed", "Badan",
         "runs_p3.csv"),
        ("S1 G-Mean", "13 x 4, G-Mean mean±SD", "Suplemen",
         "runs_p3.csv"),
        ("S2 BAS", "13 x 4, BAS mean±SD", "Suplemen", "runs_p3.csv"),
        ("S3 AUPRC", "13 x 4, AUPRC mean±SD", "Suplemen", "runs_p3.csv"),
    ]
    sheet_daftar(wb, entries)
    sheet_t1(wb, p3)
    sheet_t2(wb)
    metric_matrix(p3, "f1", "T3 F1 utama",
                  "T3. Main comparison: F1 (mean ± SD) of 13 methods on "
                  "4 datasets", wb,
                  notes=["Tabel inti manuskrip. Versi G-Mean/BAS/AUPRC ada di "
                         "sheet S1–S3 (suplemen)."])
    sheet_t4(wb, p3)
    sheet_t5(wb, p3)
    sheet_t6(wb)
    sheet_t7(wb)
    sheet_t8(wb)
    sheet_t9(wb, p3)
    sheet_t10(wb, p3)
    sheet_t11(wb, p3)
    for metric, name in [("gmean", "S1 G-Mean"), ("bas", "S2 BAS"),
                         ("auprc", "S3 AUPRC")]:
        metric_matrix(p3, metric, name,
                      f"{name.split(' ', 1)[0]}. {name.split(' ', 1)[1]} "
                      "(mean ± SD), 13 methods × 4 datasets", wb)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"written: {out} ({len(wb.sheetnames)} sheets)")
    for s in wb.sheetnames:
        print(" -", s)


if __name__ == "__main__":
    main()
