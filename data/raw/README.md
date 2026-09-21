# Raw datasets

Schema (one row = one drug-target pair), following the thesis NR file:

| column | meaning |
|---|---|
| `drug_no`, `protein_no` | pair identifiers |
| `label` | 1 = interaction, 0 = no known interaction |
| `fp2_*` | drug FP2 fingerprint bits (OpenBabel) |
| remaining columns | protein sequence descriptors (AAC/DPC/PseAAC/PsePSSM etc.) |

Included:
- `NR_AB.csv` — nuclear receptor dataset (1,404 pairs, 90 positives), copied from
  `Thesis/For Thesis/data/NR_AB.csv`.

To prepare (same schema, from the SRX-DTI repository
https://github.com/Khojasteh-hb/SRX-DTI — datasets & feature extraction code of
Khojasteh et al., PLoS ONE 2023, doi: 10.1371/journal.pone.0288173):
- `GPCR_AB.csv`
- `IC_AB.csv`
- `E_AB.csv` (Enzyme)

Keep the drug (A) + protein (B) feature-block combination consistent with
NR_AB so results are comparable across datasets.
