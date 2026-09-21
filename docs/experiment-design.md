# Experiment Design — Paper 2: SHS-ACO on Imbalanced DTI Prediction

Extension of the thesis / IJ-AI manuscript ("Ant colony based sequential hybrid
sampling for imbalanced drug-target interaction prediction"). Goal: raise the
evidence level from one dataset + single split to a multi-dataset, statistically
tested study with stronger comparators — targeting PeerJ Computer Science
(alternatives: Journal of Biomedical Informatics, Applied Soft Computing).

## 1. Research questions

- **RQ1 (generality).** Does SHS with ACO-based undersampling improve minority-class
  performance consistently across the four Yamanishi DTI datasets (NR, GPCR, IC,
  Enzyme), not just NR?
- **RQ2 (comparators).** Does SHS-ACO outperform established one-shot hybrid
  resamplers (SMOTE-ENN, SMOTE-Tomek) that were absent from paper 1?
- **RQ3 (algorithm).** Do three refinements of the thesis ACO improve it:
  (a) standard pheromone evaporation `(1-ρ)·τ + Δ` instead of the legacy rule
  `(1-ρ·τ) + Δ` found in the thesis code; (b) stratified fitness CV instead of
  plain KFold; (c) selection without replacement?
- **RQ4 (fitness).** How does the choice of ACO fitness function (F1 vs G-Mean vs
  BAS) shift the precision/recall operating point of the final classifier?

RQ3 is the paper's main novelty claim beyond breadth: the legacy update rule is a
faithful-reproduction finding (code vs. equation discrepancy) that we correct and
ablate — an honest and citable contribution.

## 2. Datasets

| Dataset | Source file (SRX-DTI schema) | Positives | Notes |
|---|---|---|---|
| NR | `NR_AB.csv` (already in `data/raw/`) | 90 / 1,404 (6%) | thesis dataset |
| GPCR | `GPCR_AB.csv` (to prepare) | ~635 interactions | |
| IC | `IC_AB.csv` (to prepare) | ~1,476 interactions | |
| Enzyme | `E_AB.csv` (to prepare) | ~2,926 interactions | largest; longest runtime |

Features: FP2 drug fingerprint + protein sequence descriptors, same pipeline as
Khojasteh et al. (PLoS ONE 2023). Their data/code: https://github.com/Khojasteh-hb/SRX-DTI.
Prepare the three new CSVs in the NR_AB schema (`drug_no, protein_no, label, features...`);
see `data/raw/README.md`.

## 3. Methods under comparison (12)

1. `baseline` — Gradient Boosting, no resampling
2. `ros`, `smote`, `adasyn` — classic oversampling to majority count
3. `smote-enn`, `smote-tomek` — established hybrids (new comparators)
4. `shs-rus-{ros,smote,adasyn}` — SHS with random undersampling
5. `shs-aco-{ros,smote,adasyn}` — SHS with ACO undersampling (proposed)

Classifier fixed to Gradient Boosting (winner of the paper-1 baseline);
optionally add XGBoost as a secondary classifier if reviewers ask.

## 4. Protocol

- **Split.** Stratified 70/30 train/test; resampling on the train split only.
- **Repetition.** 10 seeds (0–9) for cheap methods; ≥5 seeds for SHS-ACO
  (computational budget, see §7). Same seed set across methods so tests are paired.
- **Oversampling target.** Ratio-based: minority target ∈ {1.0, 1.25, 1.5} × majority
  count (replaces the absolute 1000/1500/2000 of paper 1, which does not transfer
  across datasets). Pilot on NR picks the best ratio per method; the full grid on
  the other datasets uses that ratio.
- **ACO parameters.** τ0=0.3, ρ=0.8, K=20 ants, N=10 iterations, max_idle=5,
  5-fold fitness CV (thesis-tuned values).
- **Metrics.** F1 (primary), G-Mean, BAS, AUPRC (new — threshold-free and standard
  for imbalanced problems), plus the confusion matrix and runtime.
- **Statistics.** Per dataset: Wilcoxon signed-rank, best method vs others, paired
  over seeds (α=0.05). Across datasets: Friedman test on (dataset × seed) blocks +
  Nemenyi post-hoc and mean ranks (Demšar-style comparison).

## 5. Experiment phases

- **P0 — Reproduction sanity check.** Run `--legacy --no-stratified --target-count 1500`
  with `shs-aco-smote` on NR and confirm the pipeline reproduces the thesis-level
  result (~F1 43% at seed-dependent variation). Establishes continuity with paper 1.
- **P1 — Ablation on NR (RQ3, RQ4).** 2×2×2 (pheromone rule × stratified ×
  replacement) with shs-aco-smote, 5 seeds; then fitness ∈ {f1, gmean, bas} for the
  best variant. Output: the "refined ACO" configuration.
- **P2 — Target-ratio pilot on NR.** All SHS methods × ratio {1.0, 1.25, 1.5},
  5 seeds → pick best ratio per method.
- **P3 — Full comparison (RQ1, RQ2).** 12 methods × 4 datasets × 10 seeds (5 for
  ACO), best configurations from P1/P2.
- **P4 — Statistics & writing.** `aggregate_results.py`, tables, convergence plots
  (`ACOUndersampler.history_`), runtime table.

## 6. Deliverable tables/figures for the paper

1. Dataset statistics table (4 datasets)
2. Ablation table (P1): legacy vs refined ACO on NR
3. Main results: mean±std F1/G-Mean/BAS/AUPRC per method per dataset (P3)
4. Statistical tests: Wilcoxon p-values + Friedman/Nemenyi mean ranks
5. Fitness-function ablation (precision/recall trade-off)
6. ACO convergence curves; runtime comparison bar chart

## 7. Computational budget

One ACO run ≈ (1 + K×N_effective) × cv model fits ≈ up to 1,000 GB fits.
Measured single GB fits: NR ≈ 1.3 s, GPCR ≈ 26 s — so full ACO ≈ 1.5–2 h/seed on
NR but ≈ 8 h/seed on GPCR and worse on IC/Enzyme with classic
`GradientBoostingClassifier`. Mitigations, in order of preference:
1. Run a GB vs `HistGradientBoostingClassifier` equivalence check on NR early
   (P0); HistGB is 10–100× faster at this scale and would make the full grid
   tractable — if results match, use HistGB inside the ACO fitness loop (and
   report both on the final models).
2. Run per-dataset/seed jobs in parallel (each is single-threaded).
3. If Enzyme remains infeasible, reduce its ACO budget (K=10, N=5) and report
   it as a scalability observation.
Cache resampled datasets under `data/processed/` if reruns are needed.

## 8. Threats to validity (address in the paper)

- Unlabeled pairs treated as negatives (standard caveat in this dataset family)
- No feature selection by design (isolates the sampling effect) — state explicitly
- Seed sensitivity: mitigated by repetition + paired tests
- The legacy-vs-standard pheromone finding must be reported transparently as a
  correction of the earlier implementation
