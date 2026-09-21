# Raw datasets

Schema (one row = one drug-target pair), identical to the thesis NR file:

| column | meaning |
|---|---|
| `drug_no` | row index into the dataset's `*_drug_names.csv` (KEGG D-code order) |
| `protein_no` | protein index in FASTA order (`data/srx-source/sequences/`) |
| `label` | 1 = gold-standard interaction, 0 = unlabeled pair |
| `fp2_*` (256) | drug FP2 fingerprint counts, min-max scaled per column over the dataset's drugs |
| `AAC_*` (20), `DPC_*` (400) | protein amino-acid / dipeptide composition, min-max scaled per column over the dataset's proteins |

Files (pairs = full drug x protein cartesian product):

| file | drugs x proteins | pairs | positives |
|---|---|---|---|
| `NR_AB.csv` | 54 x 26 | 1,404 | 90 (6.41%) |
| `GPCR_AB.csv` | 223 x 95 | 21,185 | 635 (3.00%) |
| `IC_AB.csv` | 210 x 204 | 42,840 | 1,476 (3.45%) |
| `E_AB.csv.gz` | 445 x 664 | 295,480 | 2,926 (0.99%) |

`NR_AB.csv` is the canonical thesis file (verified byte-equal to SRX-DTI's
`NR-run/df_NR_AB.csv`). The other three are generated locally and are NOT in
git (too large); regenerate any of them deterministically with:

```bash
python scripts/build_dataset.py gpcr ic enzyme
```

Provenance: raw inputs in `data/srx-source/` come from the SRX-DTI repository
(https://github.com/Khojasteh-hb/SRX-DTI; Khojasteh et al., PLoS ONE 2023,
doi: 10.1371/journal.pone.0288173), which uses the Yamanishi et al. (2008)
gold-standard datasets. The build pipeline was reverse-engineered from their
assembled NR file and validated to reproduce it exactly (see
`scripts/build_dataset.py --validate`).

Note: the "AB" suffix = protein feature groups A (AAC) + B (DPC) in SRX-DTI's
naming; drug features are always FP2.
