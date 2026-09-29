#!/usr/bin/env bash
# Run the experiment grid (phases P0-P3) with N parallel workers.
#
# Usage:
#   bash scripts/run_grid.sh p0            # thesis reproduction + HistGB equivalence (NR)
#   bash scripts/run_grid.sh p1            # ACO ablation 2x2x2 + fitness (NR)
#   bash scripts/run_grid.sh p2            # target-ratio pilot (NR)
#   bash scripts/run_grid.sh p3            # full comparison, 4 datasets
#   WORKERS=16 MODEL=histgb bash scripts/run_grid.sh p3
#
# Each phase appends to its own results/runs_<phase>.csv. Runs already present
# there are NOT deduplicated -- delete the file before a clean rerun.
# After P2, review results and adjust RATIO_* below before launching P3.

set -u
cd "$(dirname "$0")/.."

WORKERS="${WORKERS:-8}"
MODEL="${MODEL:-gb}"                 # gb | histgb (decide after P0)
SEEDS_CHEAP="0 1 2 3 4 5 6 7 8 9"
SEEDS_ACO="0 1 2 3 4"

# P2-winning oversampling ratios, separated per undersampling arm.
RATIO_RUS_ROS="${RATIO_RUS_ROS:-1.25}"
RATIO_RUS_SMOTE="${RATIO_RUS_SMOTE:-1.25}"
RATIO_RUS_ADASYN="${RATIO_RUS_ADASYN:-1.0}"
RATIO_ACO_ROS="${RATIO_ACO_ROS:-1.5}"
RATIO_ACO_SMOTE="${RATIO_ACO_SMOTE:-1.5}"
RATIO_ACO_ADASYN="${RATIO_ACO_ADASYN:-1.5}"
FITNESS_MODEL="${FITNESS_MODEL:-same}"   # histgb for enzyme (see experiment-log)
ANTS="${ANTS:-10}"                       # P2b: K=10 matches K=20 at half cost
ITERS="${ITERS:-10}"                     # enzyme fallback: 5 (design doc)
P3_ARMS="${P3_ARMS:-all}"                # all | cheap | expensive (RAM tuning)

# HistGB parallelizes internally via OpenMP; with many workers that
# oversubscribes cores, so pin each process to one thread.
export OMP_NUM_THREADS=1

RUN="python3 -u scripts/run_experiment.py"
CMDS=$(mktemp)

case "${1:-}" in
p0)
  OUT=results/runs_p0.csv
  # reproduction of the thesis configuration (legacy ACO rules)
  for s in $SEEDS_ACO; do
    echo "$RUN --dataset nr --method shs-aco-smote --target-count 1500 --legacy --no-stratified --model gb --verbose --seeds $s --out $OUT" >> "$CMDS"
  done
  # GB vs HistGB equivalence on cheap methods, paired seeds
  for m in baseline smote adasyn; do
    for model in gb histgb; do
      echo "$RUN --dataset nr --method $m --model $model --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
    done
  done
  # equivalence inside the ACO loop as well
  for model in histgb gb; do
    for s in $SEEDS_ACO; do
      echo "$RUN --dataset nr --method shs-aco-smote --target-ratio 1.25 --model $model --verbose --seeds $s --out $OUT" >> "$CMDS"
    done
  done
  ;;
p1)
  OUT=results/runs_p1.csv
  # 2x2x2 ablation: pheromone rule x stratified CV x replacement
  for legacy in "" "--legacy"; do
    for strat in "" "--no-stratified"; do
      for repl in "" "--no-replacement"; do
        for s in $SEEDS_ACO; do
          echo "$RUN --dataset nr --method shs-aco-smote --target-ratio 1.25 --model $MODEL --verbose $legacy $strat $repl --seeds $s --out $OUT" >> "$CMDS"
        done
      done
    done
  done
  # fitness-function ablation on the refined variant (f1 = the default
  # ablation corner, already covered above)
  for fit in gmean bas; do
    for s in $SEEDS_ACO; do
      echo "$RUN --dataset nr --method shs-aco-smote --target-ratio 1.25 --model $MODEL --verbose --fitness $fit --seeds $s --out $OUT" >> "$CMDS"
    done
  done
  ;;
p2)
  OUT=results/runs_p2.csv
  for m in shs-rus-ros shs-rus-smote shs-rus-adasyn shs-aco-ros shs-aco-smote shs-aco-adasyn; do
    for r in 1.0 1.25 1.5; do
      if [[ $m == shs-aco-* ]]; then
        for s in $SEEDS_ACO; do
          echo "$RUN --dataset nr --method $m --target-ratio $r --model $MODEL --verbose --seeds $s --out $OUT" >> "$CMDS"
        done
      else
        echo "$RUN --dataset nr --method $m --target-ratio $r --model $MODEL --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
      fi
    done
  done
  ;;
p2b)
  OUT=results/runs_p2b.csv
  # one-factor-at-a-time sensitivity around tuned defaults (rho=0.8, K=20),
  # on shs-aco-smote at the P2-winning ratio (edit RATIO_SENS after P2)
  RATIO_SENS="${RATIO_SENS:-1.25}"
  for rho in 0.5 0.95; do
    for s in $SEEDS_ACO; do
      echo "$RUN --dataset nr --method shs-aco-smote --target-ratio $RATIO_SENS --model $MODEL --verbose --rho $rho --seeds $s --out $OUT" >> "$CMDS"
    done
  done
  for ants in 10 40; do
    for s in $SEEDS_ACO; do
      echo "$RUN --dataset nr --method shs-aco-smote --target-ratio $RATIO_SENS --model $MODEL --verbose --ants $ants --seeds $s --out $OUT" >> "$CMDS"
    done
  done
  # budget-matched SA comparator (reviewer defense: informed selection vs ACO)
  for s in $SEEDS_ACO; do
    echo "$RUN --dataset nr --method shs-sa-smote --target-ratio $RATIO_SENS --model $MODEL --verbose --seeds $s --out $OUT" >> "$CMDS"
  done
  ;;
p3)
  OUT=results/runs_p3.csv
  DS_LIST="${2:-nr gpcr ic enzyme}"   # optional 2nd arg: run one dataset
  for ds in $DS_LIST; do
    if [ "$P3_ARMS" != "expensive" ]; then
      for m in baseline ros smote adasyn smote-enn smote-tomek; do
        echo "$RUN --dataset $ds --method $m --model $MODEL --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
      done
      for o in ros smote adasyn; do
        ru_var="RATIO_RUS_$(echo "$o" | tr '[:lower:]' '[:upper:]')"
        echo "$RUN --dataset $ds --method shs-rus-$o --target-ratio ${!ru_var} --model $MODEL --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
      done
    fi
    if [ "$P3_ARMS" != "cheap" ]; then
      for o in ros smote adasyn; do
        ra_var="RATIO_ACO_$(echo "$o" | tr '[:lower:]' '[:upper:]')"
        for s in $SEEDS_ACO; do
          echo "$RUN --dataset $ds --method shs-aco-$o --target-ratio ${!ra_var} --model $MODEL --fitness-model $FITNESS_MODEL --ants $ANTS --iters $ITERS --verbose --seeds $s --out $OUT" >> "$CMDS"
        done
      done
      for s in $SEEDS_ACO; do
        echo "$RUN --dataset $ds --method shs-sa-smote --target-ratio $RATIO_ACO_SMOTE --model $MODEL --fitness-model $FITNESS_MODEL --ants $ANTS --iters $ITERS --verbose --seeds $s --out $OUT" >> "$CMDS"
      done
    fi
  done
  ;;
hgb)
  OUT=results/runs_hgb.csv
  # hybrid-mode validation on NR: HistGB inside the fitness loop, GB final
  for s in $SEEDS_ACO; do
    echo "$RUN --dataset nr --method shs-aco-smote --target-ratio 1.5 --model gb --fitness-model histgb --verbose --seeds $s --out $OUT" >> "$CMDS"
  done
  # timing + behavior probe on GPCR (2 seeds)
  for s in 0 1; do
    echo "$RUN --dataset gpcr --method shs-aco-smote --target-ratio 1.5 --model gb --fitness-model histgb --verbose --seeds $s --out $OUT" >> "$CMDS"
  done
  ;;
*)
  echo "usage: bash scripts/run_grid.sh {p0|p1|p2|p2b|p3|hgb} [p3-dataset]" >&2
  rm -f "$CMDS"; exit 1
  ;;
esac

N=$(wc -l < "$CMDS")
echo "Phase ${1}: $N jobs, $WORKERS workers, model=$MODEL. Logs: logs/"
mkdir -p logs results
rm -f logs/*.log
nl -ba "$CMDS"

# plain bash job pool (macOS xargs -I has a 255-byte replstr limit)
run_job() {
  local cmd="$1"
  local tag sum
  sum=$(printf %s "$cmd" | cksum | cut -d" " -f1)
  tag="$(echo "$cmd" | tr -cs '[:alnum:]' '-' | cut -c1-110)$sum"
  echo "[start] $cmd"
  if eval "$cmd" > "logs/$tag.log" 2>&1; then
    echo "[done ] $cmd"
  else
    echo "[FAIL ] $cmd (see logs/$tag.log)"
  fi
}

while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  while [ "$(jobs -rp | wc -l)" -ge "$WORKERS" ]; do sleep 2; done
  run_job "$cmd" &
done < "$CMDS"
wait

rm -f "$CMDS"
echo "Phase ${1} finished. Aggregate with:"
echo "  python3 scripts/aggregate_results.py --runs results/runs_${1}.csv"
