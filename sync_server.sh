#!/usr/bin/env bash
# Pull results/logs from the Hetzner server every 15 min so the server can be
# deleted at any time without losing more than one interval of results.
SERVER=root@77.42.18.46
DEST=/Users/ismankrn/Research/aco-shs
FAILS=0
END=$((SECONDS + 48*3600))
while [ $SECONDS -lt $END ]; do
  if rsync -az --timeout=60 \
      "$SERVER:aco-shs/results/" "$DEST/results/" \
      && rsync -az --timeout=60 \
      "$SERVER:aco-shs/logs/" "$DEST/logs-server/" \
      && rsync -az --timeout=60 \
      "$SERVER:aco-shs/p1_master.log" "$DEST/p1_master_server.log"; then
    FAILS=0
    echo "$(date '+%F %T') synced"
  else
    FAILS=$((FAILS + 1))
    echo "$(date '+%F %T') sync FAILED ($FAILS/5)"
    [ $FAILS -ge 5 ] && { echo "server unreachable 5x, stopping"; exit 0; }
  fi
  sleep 900
done
