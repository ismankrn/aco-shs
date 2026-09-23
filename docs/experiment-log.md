# Experiment log

## P0 — reproduction & HistGB equivalence (NR) — completed 2026-09-22

75 rows in `results/runs_p0.csv` (60 cheap-method seeds + 15 ACO seeds).

### 1. Thesis reproduction — PASS
`shs-aco-smote --target-count 1500 --legacy --no-stratified`, GB, 5 seeds:
mean F1 = 0.3606 ± 0.0707, range [0.2667, 0.4314]. Two of five seeds land at
0.4314 ≈ the thesis single-split figure (0.4324). Conclusion: the thesis result
is reproducible but sits at the optimistic end of the seed distribution —
exactly the seed-sensitivity argument motivating paper 2's repeated protocol.

### 2. GB vs HistGB equivalence — MIXED; keep GB for NR phases
Paired Wilcoxon on F1:

| method | n | GB | HistGB | diff | p |
|---|---|---|---|---|---|
| baseline | 10 | 0.3138 | 0.3520 | +0.038 | 0.027 (HistGB better) |
| smote | 10 | 0.3744 | 0.3704 | −0.004 | 0.625 (equivalent) |
| adasyn | 10 | 0.3824 | 0.3099 | −0.073 | 0.008 (HistGB worse) |
| shs-aco-smote (ratio 1.25) | 5 | 0.3291 | 0.3317 | +0.003 | 1.000 (equivalent) |

HistGB is NOT a blanket substitute (ADASYN degrades significantly). Inside the
SMOTE-based ACO loop it is statistically indistinguishable, but the speedup on
NR is only ~1.23× (6,500 vs 8,474 s/seed; OMP_NUM_THREADS=1, small data), so it
is not worth the extra explanation burden there.

**Decision:** P1 and P2 run with `MODEL=gb`. Before P3, run a small GB-vs-HistGB
equivalence check on GPCR (cheap methods + a few ACO seeds), where HistGB's
advantage should actually materialize; decide per-oversampler.

### Runtime observations (per ACO seed, NR, 8 parallel workers)
- GB: 7,500–11,700 s (≈2–3 h)
- HistGB: 5,400–7,600 s (≈1.5–2 h)
- Per-seed job granularity + 8 workers finished all 15 ACO seeds overnight.

## P1 — ACO ablation on NR — completed 2026-09-23

50 runs (10 configs x 5 seeds) in `results/runs_p1_merged.csv` (merged with the
7 pre-reboot seeds, duplicates dropped; values identical as runs are seed-deterministic).

### RQ3 — none of the three refinements changes performance significantly
Paired Wilcoxon over 20 config-seed pairs per factor (F1):

| factor | False | True | diff | p |
|---|---|---|---|---|
| legacy pheromone | 0.3338 | 0.3347 | +0.001 | 0.925 |
| stratified CV | 0.3368 | 0.3317 | −0.005 | 0.554 |
| with replacement | 0.3244 | 0.3441 | +0.020 | 0.112 |

Refined (std+strat+repl) vs thesis-like (legacy+plain+repl): p = 1.0.
The legacy-pheromone code/equation discrepancy therefore does NOT affect NR
results — report as a correction plus a robustness finding.

### RQ4 — fitness function
F1 and G-Mean fitness give near-identical final models (F1 0.338 vs 0.339);
BAS fitness is worse (0.308). Keep F1 as the fitness function.

### Decision for P2/P3
Adopt the **refined configuration**: standard pheromone update (matches the
published equations), stratified fitness CV, selection with replacement,
fitness = F1. Justified by methodological correctness since performance is
statistically indistinguishable across all variants.

Runtime: ~1.8-2.0 h per ACO seed on CPX42 (8 workers); full phase ~12 h wall.

## P2 — target-ratio pilot on NR — completed 2026-09-23

135 runs (6 SHS methods x 3 ratios). Winning ratios (mean F1, best in bold
per arm): shs-rus: ros 1.25 (0.4725), smote 1.25 (0.3759), adasyn 1.0
(0.3805). shs-aco: ros 1.5 (0.4751), smote 1.5 (0.3431), adasyn 1.5 (0.3603).
Clean interaction: ACO's best is always the largest pool (informed selection
exploits surplus), RUS's best is small/moderate pools (random selection is
hurt by it). Headline shift vs paper 1: under repeated evaluation the ROS
arms dominate NR (F1 44-48%) over SMOTE (31-38%).

## P2b — ACO parameter sensitivity + SA comparator — completed 2026-09-24

25 runs on shs-aco-smote ratio 1.5. Paired Wilcoxon vs default (rho=0.8,
K=20, F1 0.3431): rho=0.5 p=1.0; rho=0.95 p=0.63; K=10 p=1.0; K=40 p=0.31;
SA (budget-matched 200 evals) p=0.63. Conclusions:
- ACO is insensitive to rho and K in reasonable ranges (robustness).
- K=10 matches default quality at HALF the runtime (52 vs 107 min/seed);
  K=40 trends worse at 2x cost. Practical note for the paper.
- **SA is statistically equivalent to ACO** (SA 0.3565 vs ACO 0.3431,
  SA wins 3/5 seeds): the value lies in informed selection itself, not the
  specific metaheuristic. SA joins P3's SMOTE arm to settle this across
  datasets.

### Decisions for P3
- Per-arm ratios: RUS ros/smote/adasyn = 1.25/1.25/1.0; ACO (and SA-smote)
  = 1.5 for all arms.
- Keep K=20 (consistency with P2-chosen ratios); K=10 documented as fallback.
- Pending: GB-vs-HistGB mini-equivalence on GPCR, then CPX42 -> CPX62.

## HistGB check + fit-time calibration — 2026-09-24

Hybrid mode (HistGB fitness, GB final) on NR: worse in 5/5 seeds vs pure GB
(0.3177 vs 0.3431, p=0.125) -> avoid where GB is affordable. Single-fit times
(server, OMP=1): IC gb 96 s / histgb 13.6 s; Enzyme gb 810 s / histgb 82.7 s.
**P3 policy:** K=10 (P2b-validated), pure GB fitness for NR/GPCR/IC; Enzyme
uses HistGB fitness (GB final) as the only feasible option — uniform within
the dataset, reported transparently. Enzyme runs with reduced workers (RAM).
