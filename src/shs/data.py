"""Dataset loaders.

Each raw CSV follows the schema of the thesis NR file: an index column,
`drug_no`, `protein_no`, `label` (0/1), then the drug FP2 fingerprint and
protein descriptor features. The GPCR / IC / Enzyme files must be prepared
in the same schema from the SRX-DTI repository
(https://github.com/Khojasteh-hb/SRX-DTI) — see data/raw/README.md.
"""

from pathlib import Path

import pandas as pd

DATASETS = {
    "nr": "NR_AB.csv",
    "gpcr": "GPCR_AB.csv",
    "ic": "IC_AB.csv",
    "enzyme": "E_AB.csv.gz",
}

_META_COLS = ["Unnamed: 0", "drug_no", "protein_no", "label"]


def load_dataset(name, data_dir="data/raw"):
    """Return (X: DataFrame of features, y: Series of int labels)."""
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset '{name}'; choose from {sorted(DATASETS)}")
    path = Path(data_dir) / DATASETS[name]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Regenerate it with: "
            f"python scripts/build_dataset.py {name}")
    df = pd.read_csv(path)
    y = df["label"].astype(int)
    X = df.drop(columns=[c for c in _META_COLS if c in df.columns])
    return X, y
