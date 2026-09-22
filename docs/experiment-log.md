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
