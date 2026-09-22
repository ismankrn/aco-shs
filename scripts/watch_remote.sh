#!/usr/bin/env bash
# Pantau progres fase eksperimen di server dari mesin lokal.
#
# Pakai:  bash scripts/watch_remote.sh [fase] [interval_detik]
# Contoh: bash scripts/watch_remote.sh p2        # refresh tiap 60 detik
#         bash scripts/watch_remote.sh p2 30     # refresh tiap 30 detik
# Hentikan dengan Ctrl-C.

SERVER=root@77.42.18.46
PHASE="${1:-p2}"
INTERVAL="${2:-60}"

while true; do
  clear
  echo "=== $(date '+%H:%M:%S')  fase $PHASE @ $SERVER  (refresh ${INTERVAL}s, Ctrl-C untuk berhenti) ==="
  echo
  ssh -o ConnectTimeout=15 "$SERVER" "cd aco-shs && bash scripts/progress.sh $PHASE" 2>/dev/null \
    || echo "(server tidak terjangkau -- dicoba lagi ${INTERVAL} detik)"
  sleep "$INTERVAL"
done
