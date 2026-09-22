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

# Best oversampling ratio per SHS method -- EDIT after inspecting P2 results.
RATIO_ROS="${RATIO_ROS:-1.25}"
RATIO_SMOTE="${RATIO_SMOTE:-1.25}"
RATIO_ADASYN="${RATIO_ADASYN:-1.25}"

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
p3)
  OUT=results/runs_p3.csv
  for ds in nr gpcr ic enzyme; do
    for m in baseline ros smote adasyn smote-enn smote-tomek; do
      echo "$RUN --dataset $ds --method $m --model $MODEL --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
    done
    for o in ros smote adasyn; do
      r_var="RATIO_$(echo "$o" | tr '[:lower:]' '[:upper:]')"
      r="${!r_var}"
      echo "$RUN --dataset $ds --method shs-rus-$o --target-ratio $r --model $MODEL --seeds $SEEDS_CHEAP --out $OUT" >> "$CMDS"
      for s in $SEEDS_ACO; do
        echo "$RUN --dataset $ds --method shs-aco-$o --target-ratio $r --model $MODEL --verbose --seeds $s --out $OUT" >> "$CMDS"
      done
    done
  done
  ;;
*)
  echo "usage: bash scripts/run_grid.sh {p0|p1|p2|p3}" >&2
  rm -f "$CMDS"; exit 1
  ;;
esac

N=$(wc -l < "$CMDS")
echo "Phase ${1}: $N jobs, $WORKERS workers, model=$MODEL. Logs: logs/"
mkdir -p logs results
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
