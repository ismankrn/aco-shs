#!/usr/bin/env bash
# Show grid progress: completed seeds + mean F1 per job, active processes,
# and the last log line of every job.
#
# Usage: bash scripts/progress.sh [p0|p1|p2|p3]

cd "$(dirname "$0")/.."
PHASE="${1:-p0}"
CSV="results/runs_${PHASE}.csv"

if [ -f "$CSV" ]; then
  echo "== Completed seeds per job ($CSV):"
  python3 - "$CSV" <<'EOF'
import sys
import pandas as pd
df = pd.read_csv(sys.argv[1])
cols = [c for c in ("method", "model", "target", "fitness_fn") if c in df.columns]
g = (df.groupby(cols, dropna=False)
       .agg(seeds=("seed", "count"), f1_mean=("f1", "mean"),
            mean_runtime_s=("runtime_s", "mean"))
       .round(4))
print(g.to_string())
EOF
else
  echo "== $CSV not found yet (no seed finished)."
fi

echo
echo "== Active run_experiment.py processes: $(pgrep -f run_experiment.py | wc -l | tr -d ' ')"
echo
echo "== Last line of each job log:"
for f in logs/*.log; do
  [ -e "$f" ] || continue
  printf "%-68.68s | %s\n" "$(basename "$f" .log)" "$(tail -1 "$f")"
done
