#!/usr/bin/env bash
# Pull results/logs from the Hetzner server every 15 min (port from ~/.ssh/config).
SERVER=root@77.42.18.46
DEST=/Users/ismankrn/Research/aco-shs
END=$((SECONDS + 72*3600))
while [ $SECONDS -lt $END ]; do
  ok=1
  rsync -az --timeout=90 "$SERVER:aco-shs/results/" "$DEST/results/" || ok=0
  rsync -az --timeout=90 "$SERVER:aco-shs/logs/" "$DEST/logs-server/" || ok=0
  rsync -az --timeout=90 --include="*_master.log" --exclude="*" "$SERVER:aco-shs/" "$DEST/" || ok=0
  if [ $ok -eq 1 ]; then echo "$(date '+%F %T') synced"; else echo "$(date '+%F %T') sync FAILED (lanjut coba lagi)"; fi
  sleep 900
done
