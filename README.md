# SHS-ACO for Imbalanced DTI Prediction — Paper 2

Extended study of Sequential Hybrid Sampling with ACO-based undersampling for
drug-target interaction (DTI) prediction. Builds on the thesis code in
`../Thesis/For Thesis/` (R. N. Harahap, Telkom University) with a refactored,
seeded, and ablatable implementation.

See **docs/experiment-design.md** for research questions, protocol, and phases.

## Layout

```
src/shs/            library: ACO undersampler, samplers, metrics, data loaders
scripts/            run_experiment.py (one config, many seeds) / aggregate_results.py
config/             experiment grid reference
data/raw/           input datasets (NR included; GPCR/IC/Enzyme to prepare)
data/processed/     optional caches
results/            runs.csv (appended per run) + summary.csv
notebooks/          exploration only — results must come from scripts/
```

## Quickstart

```bash
pip install -r requirements.txt

# baseline on NR, 5 seeds
python scripts/run_experiment.py --dataset nr --method baseline --seeds 0 1 2 3 4

# proposed method (refined ACO)
python scripts/run_experiment.py --dataset nr --method shs-aco-smote \
    --target-ratio 1.25 --fitness f1 --seeds 0 1 2 3 4

# thesis-reproduction mode (P0 sanity check)
python scripts/run_experiment.py --dataset nr --method shs-aco-smote \
    --target-count 1500 --legacy --no-stratified --seeds 42

# tables + significance tests
python scripts/aggregate_results.py --metric f1
```

## Notes

- Resampling is applied to the training split only; the 30% test split is untouched.
- `--legacy` reproduces the thesis pheromone-update rule `(1-ρ·τ)+Δ`; the default
  is the standard `(1-ρ)·τ+Δ` (see docs/experiment-design.md, RQ3).
- GPCR/IC/Enzyme features: prepare per `data/raw/README.md` from
  https://github.com/Khojasteh-hb/SRX-DTI
