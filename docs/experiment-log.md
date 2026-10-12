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

## P3 — full comparison, 4 datasets — COMPLETED 2026-10-08

440 runs (13 methods x 4 datasets), zero duplicates. Headline results (F1 means):

| dataset | winner | F1 | baseline | notes |
|---|---|---|---|---|
| NR | ros / shs-rus-ros | 0.457-0.473 | 0.324 | sampling pays hugely (+15 pp) |
| GPCR | shs-sa-smote | 0.365 | 0.193 | SMOTE family leads; selection ~neutral |
| IC | shs-aco-adasyn | 0.346 | 0.160 | ACO adds (thin) on top of ADASYN |
| Enzyme | baseline | 0.185 | — | NO sampling method beats baseline |

Key findings:
1. **No universal winner**: each dataset crowns a different oversampler
   (ROS -> SMOTE -> ADASYN -> none), tracking minority-data richness
   (63 / 444 / 1,033 / 2,048 real positives). The benefit of sampling and of
   informed selection decays monotonically along this gradient.
2. **ACO abstention property (unplanned, verified)**: on Enzyme, ACO's
   fitness never found a synthetic subset beating the raw data, so its
   fallback returned the ORIGINAL training set in 15/15 runs — confusion
   matrices identical to baseline. SA, lacking an abstention option, was
   forced to oversample and landed slightly below baseline. Informed
   selection with a null action doubles as a safety valve.
3. **ROS ceiling**: informed selection cannot rescue ROS on any large
   dataset (GPCR/IC ~equal to plain ROS; Enzyme rescued only via abstention).
4. **SA vs ACO**: no significant difference on any dataset (p=0.125-0.812);
   SA wins GPCR nominally, ACO wins IC/Enzyme nominally. Metaheuristic
   choice is secondary — but the abstention asymmetry favors the ACO design.
5. **Friedman across datasets** (13 methods, 20 blocks, chi2=42.5, p=2.7e-5):
   top mean ranks are shs-aco-adasyn (4.85) and shs-aco-smote (5.00), ahead
   of smote-tomek (5.62); bottom: baseline/ros/rus-ros (~9.4). If forced to
   pick one method blind, SHS-ACO is the safest — but per-dataset tailoring
   beats any single choice.
6. **Nemenyi post-hoc** (computed for figure F4): q_0.05(k=13) = 3.313,
   CD = 4.08 ranks. Only baseline (9.43), ROS (9.43) and SHS-RUS-ROS (9.45)
   are separable from the top-ranked SHS-ACO-ADASYN (4.85 + 4.08 = 8.93);
   the ten SMOTE/ADASYN-based methods are mutually indistinguishable at
   this N — consistent with the per-dataset Wilcoxon picture.
