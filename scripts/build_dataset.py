"""Build the pairwise feature CSVs (NR/GPCR/IC/Enzyme) in the NR_AB schema.

Reverse-engineered from the SRX-DTI repository (Khojasteh et al., PLoS ONE 2023,
https://github.com/Khojasteh-hb/SRX-DTI) and validated to reproduce their
`NR-run/df_NR_AB.csv` (= the thesis NR_AB.csv) exactly:

1. Drug block  : FP2 fingerprint count matrix (row order = *_drug_names.csv),
                 min-max scaled per column over that dataset's drugs.
2. Protein block: AAC (20) + DPC (400) computed from the FASTA file
                 (protein_no = FASTA order), min-max scaled per column over
                 that dataset's proteins.
3. Pairs       : full drug x protein cartesian product, drug-major order;
                 label 1 iff (hsa, drug) is in the gold-standard relation list.

Inputs live in data/srx-source/ (copied from the SRX-DTI repo).

Usage:
    python scripts/build_dataset.py nr [--out data/raw] [--validate FILE]
    python scripts/build_dataset.py gpcr ic enzyme
"""

import argparse
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

AA = "ACDEFGHIKLMNPQRSTVWY"

SOURCES = {
    "nr":     {"fp2": "NR_drug_fp2.csv",   "names": "NR_drug_names.csv",
               "seq": "Nuclear receptor.txt", "rel": "Nuclear receptor.txt",
               "out": "NR_AB.csv"},
    "gpcr":   {"fp2": "GPCR_drug_fp2.csv", "names": "GPCR_drug_names.csv",
               "seq": "GPCR.txt", "rel": "GPCR.txt", "out": "GPCR_AB.csv"},
    "ic":     {"fp2": "IC_drug_fp2.csv",   "names": "IC_drug_names.csv",
               "seq": "Ion channel.txt", "rel": "Ion channel.txt",
               "out": "IC_AB.csv"},
    "enzyme": {"fp2": "EN_drug_fp2.csv",   "names": "EN_drug_names.csv",
               "seq": "Enzyme.txt", "rel": "Enzyme.txt",
               "out": "E_AB.csv.gz"},
}


def read_fasta(path):
    """Read FASTA; drop non-standard residues (e.g. selenocysteine 'U'),
    matching SRX-DTI's readFasta.py + the re.sub('-','') in its AAC/DPC."""
    records = re.split(r">", Path(path).read_text())[1:]
    out = []
    for r in records:
        lines = r.strip().splitlines()
        seq = "".join(l.strip() for l in lines[1:]).upper()
        seq = re.sub(f"[^{AA}]", "", seq)
        out.append((lines[0].split()[0], seq))
    return out


def aac(seq):
    c = Counter(seq)
    return [c[a] / len(seq) for a in AA]


def dpc(seq):
    idx = {a: i for i, a in enumerate(AA)}
    t = [0] * 400
    for j in range(len(seq) - 1):
        t[idx[seq[j]] * 20 + idx[seq[j + 1]]] += 1
    s = sum(t)
    return [x / s for x in t] if s else [0.0] * 400


def minmax(mat):
    mn, mx = mat.min(0), mat.max(0)
    rng = np.where(mx - mn == 0, 1.0, mx - mn)
    return (mat - mn) / rng


def build(name, src_dir):
    cfg = SOURCES[name]
    src = Path(src_dir)

    fp2_raw = pd.read_csv(src / "fp2" / cfg["fp2"], index_col=0)
    drug_names = pd.read_csv(src / "fp2" / cfg["names"], index_col=0)["drug_name"].tolist()
    fp2 = minmax(fp2_raw.values.astype(float))

    fastas = read_fasta(src / "sequences" / cfg["seq"])
    prot_names = [n.replace("hsa", "hsa:") if ":" not in n else n for n, _ in fastas]
    prot = minmax(np.array([aac(s) + dpc(s) for _, s in fastas]))

    positives = set()
    for line in Path(src / "relations" / cfg["rel"]).read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            positives.add((parts[0], parts[1]))  # (hsa:xxx, Dxxxxx)

    n_drug, n_prot = len(drug_names), len(prot_names)
    drug_idx = np.repeat(np.arange(n_drug), n_prot)
    prot_idx = np.tile(np.arange(n_prot), n_drug)
    labels = np.fromiter(
        ((prot_names[p], drug_names[d]) in positives
         for d, p in zip(drug_idx, prot_idx)), dtype=int, count=n_drug * n_prot)

    fp2_cols = [f"fp2_{i}" for i in range(fp2.shape[1])]
    prot_cols = [f"AAC_{i}" for i in range(20)] + [f"DPC_{i}" for i in range(400)]
    df = pd.DataFrame(
        np.hstack([fp2[drug_idx], prot[prot_idx]]),
        columns=fp2_cols + prot_cols)
    df.insert(0, "label", labels)
    df.insert(0, "protein_no", prot_idx)
    df.insert(0, "drug_no", drug_idx)

    n_pos = int(labels.sum())
    print(f"[{name}] {n_drug} drugs x {n_prot} proteins = {len(df)} pairs, "
          f"{n_pos} positives ({100 * n_pos / len(df):.2f}%)")
    if n_pos != len(positives):
        print(f"[{name}] WARNING: relation list has {len(positives)} pairs "
              f"but only {n_pos} matched — check name normalization!")
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("datasets", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--src", default="data/srx-source")
    p.add_argument("--out", default="data/raw")
    p.add_argument("--validate", help="existing CSV to compare against (numeric equality)")
    args = p.parse_args()

    for name in args.datasets:
        df = build(name, args.src)
        if args.validate:
            ref = pd.read_csv(args.validate)
            ref = ref.drop(columns=[c for c in ("Unnamed: 0",) if c in ref.columns])
            same_meta = (df[["drug_no", "protein_no", "label"]].values
                         == ref[["drug_no", "protein_no", "label"]].values).all()
            feat = [c for c in df.columns if c not in ("drug_no", "protein_no", "label")]
            close = np.allclose(df[feat].values, ref[feat].values, atol=1e-9)
            print(f"[{name}] validation vs {args.validate}: meta={same_meta} features={close}")
            if not (same_meta and close):
                raise SystemExit(1)
        out = Path(args.out) / SOURCES[name]["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, float_format="%.10g")
        print(f"[{name}] written: {out}")


if __name__ == "__main__":
    main()
