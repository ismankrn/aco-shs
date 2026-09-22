"""Export an Excel recap of a phase's results CSV.

Sheets (created when applicable):
- Ringkasan      : phase overview + best configuration per metric
- Agregat        : mean/std per configuration for every metric
- GB vs HistGB   : paired model comparison with Wilcoxon p-values
- Reproduksi     : per-seed rows of the thesis-reproduction config (legacy)
- Semua run      : raw rows

All cells are computed values (no formulas), so the file is a stable snapshot.

Usage:
    python scripts/export_analysis.py --runs results/runs_p0.csv \
        --out results/analysis/P0_rekap.xlsx
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from scipy import stats

METRICS = ["f1", "gmean", "bas", "auprc", "accuracy"]
CFG_COLS = ["dataset", "method", "model", "target", "fitness_fn",
            "legacy", "stratified", "replacement"]

FONT = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT, size=10)
TITLE_FONT = Font(name=FONT, size=12, bold=True)
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)


def write_table(ws, df, start_row=1, title=None):
    r = start_row
    if title:
        ws.cell(r, 1, title).font = TITLE_FONT
        r += 2
    for c, name in enumerate(df.columns, 1):
        cell = ws.cell(r, c, str(name))
        cell.font, cell.fill, cell.border = HDR_FONT, HDR_FILL, THIN
        cell.alignment = Alignment(horizontal="center")
    for i, row in enumerate(df.itertuples(index=False), 1):
        for c, val in enumerate(row, 1):
            if isinstance(val, (np.floating, float)) and not pd.isna(val):
                val = round(float(val), 4)
            elif pd.isna(val):
                val = "-"
            cell = ws.cell(r + i, c, val)
            cell.font, cell.border = BODY_FONT, THIN
    for c, name in enumerate(df.columns, 1):
        width = max(len(str(name)), *(len(str(v)) for v in df.iloc[:, c - 1])) + 2
        ws.column_dimensions[get_column_letter(c)].width = min(width, 28)
    ws.freeze_panes = ws.cell(r + 1, 1)
    return r + len(df) + 2


def cfg_frame(df):
    cols = [c for c in CFG_COLS if c in df.columns]
    d = df.copy()
    d[cols] = d[cols].astype(object).where(pd.notna(d[cols]), "-")
    return d, cols


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    df = pd.read_csv(args.runs)
    d, cols = cfg_frame(df)
    wb = Workbook()

    # --- Agregat ---
    agg = (d.groupby(cols, dropna=False)
             .agg(seeds=("seed", "count"),
                  **{f"{m}_{s}": (m, s) for m in METRICS for s in ("mean", "std")},
                  runtime_mean_s=("runtime_s", "mean"))
             .reset_index())

    # --- Ringkasan ---
    ws = wb.active
    ws.title = "Ringkasan"
    ws.cell(1, 1, f"Rekap hasil: {Path(args.runs).name}").font = TITLE_FONT
    ws.cell(2, 1, f"Total run: {len(df)} baris, "
                  f"{agg.shape[0]} konfigurasi, dataset: "
                  f"{', '.join(sorted(df.dataset.unique()))}").font = BODY_FONT
    best_rows = []
    for m in METRICS[:4]:
        i = agg[f"{m}_mean"].idxmax()
        r = agg.loc[i]
        best_rows.append({"metrik": m, "konfigurasi terbaik":
                          " | ".join(f"{c}={r[c]}" for c in cols if r[c] != "-"),
                          "mean": r[f"{m}_mean"], "std": r[f"{m}_std"],
                          "seeds": r["seeds"]})
    write_table(ws, pd.DataFrame(best_rows), start_row=4,
                title="Konfigurasi terbaik per metrik (berdasarkan mean)")

    write_table(wb.create_sheet("Agregat"), agg)

    # --- GB vs HistGB (paired Wilcoxon) ---
    if d["model"].nunique() > 1:
        pair_cols = [c for c in cols if c != "model"]
        rows = []
        for key, sub in d.groupby(pair_cols, dropna=False):
            piv = sub.pivot_table(index="seed", columns="model", values="f1")
            if {"gb", "histgb"} <= set(piv.columns):
                piv = piv.dropna()
                try:
                    _, pval = stats.wilcoxon(piv["gb"], piv["histgb"])
                except ValueError:
                    pval = np.nan
                label = " | ".join(f"{c}={v}" for c, v in zip(pair_cols, key)
                                   if v != "-")
                rows.append({"konfigurasi": label, "n seed": len(piv),
                             "F1 GB": piv["gb"].mean(),
                             "F1 HistGB": piv["histgb"].mean(),
                             "selisih (HistGB-GB)": piv["histgb"].mean() - piv["gb"].mean(),
                             "p Wilcoxon": pval,
                             "kesimpulan": ("setara" if pd.isna(pval) or pval >= 0.05
                                            else ("HistGB lebih baik"
                                                  if piv["histgb"].mean() > piv["gb"].mean()
                                                  else "GB lebih baik"))})
        if rows:
            write_table(wb.create_sheet("GB vs HistGB"), pd.DataFrame(rows),
                        title="Uji ekuivalensi model (Wilcoxon berpasangan, F1)")

    # --- Reproduksi (legacy rows) ---
    if "legacy" in df.columns and "target" in df.columns and \
            ((df["legacy"]) & (df["target"] == 1500)).any():
        rep = df[(df["legacy"]) & (df["target"] == 1500)].copy()
        keep = ["dataset", "method", "model", "target", "seed",
                "tp", "fp", "tn", "fn"] + METRICS + ["runtime_s"]
        rep = rep[[c for c in keep if c in rep.columns]].sort_values("seed")
        ws = wb.create_sheet("Reproduksi")
        nxt = write_table(ws, rep, title="Konfigurasi legacy (reproduksi tesis), per seed")
        ws.cell(nxt, 1, "Referensi tesis (split tunggal): F1=0.4324, "
                        "G-Mean=0.5075, BAS=0.6241").font = Font(
            name=FONT, size=10, italic=True)

    write_table(wb.create_sheet("Semua run"), d)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"written: {out} ({len(wb.sheetnames)} sheet: {', '.join(wb.sheetnames)})")


if __name__ == "__main__":
    main()
