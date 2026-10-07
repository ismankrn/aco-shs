#!/usr/bin/env bash
# Evakuasi total hasil dari server sebelum instance dihapus.
# Pakai: bash ~/Research/aco-shs/evacuate.sh
set -e
SERVER=root@77.42.18.46
DEST=/Users/ismankrn/Research/aco-shs
cd "$DEST"

echo "[1/5] Tarik semua hasil (results/) ..."
rsync -az --timeout=120 "$SERVER:aco-shs/results/" results/

echo "[2/5] Tarik semua log job (konvergensi ACO/SA utk figur) + log operasional ..."
rsync -az --timeout=120 "$SERVER:aco-shs/logs/" logs-server-final/
rsync -az --timeout=120 "$SERVER:aco-shs/p3_master.log" p3_master_server.log || true
rsync -az --timeout=120 "$SERVER:/root/watchdog.log" watchdog_server.log || true

echo "[3/5] Verifikasi file kritis ..."
ROWS=$(tail -n +2 results/runs_p3.csv | wc -l | tr -d " ")
echo "  runs_p3.csv: $ROWS baris (harus 440)"
[ "$ROWS" = "440" ] || { echo "  !! BARIS KURANG - JANGAN HAPUS SERVER DULU"; exit 1; }
REMOTE_MD5=$(ssh "$SERVER" "md5sum aco-shs/results/runs_p3.csv" | cut -d" " -f1)
LOCAL_MD5=$(md5 -q results/runs_p3.csv)
echo "  md5 server=$REMOTE_MD5"
echo "  md5 lokal =$LOCAL_MD5"
[ "$REMOTE_MD5" = "$LOCAL_MD5" ] || { echo "  !! MD5 BEDA - ulangi"; exit 1; }

echo "[4/5] Arsipkan log konvergensi ke results/ (ikut git) ..."
tar -czf results/logs_server_final.tar.gz logs-server-final p3_master_server.log watchdog_server.log 2>/dev/null

echo "[5/5] Matikan loop sinkron lokal (tidak diperlukan lagi) ..."
pkill -f sync_server.sh 2>/dev/null || true

echo
echo "=== EVAKUASI SELESAI - AMAN MENGHAPUS INSTANCE DI DASHBOARD HETZNER ==="
echo "Jangan lupa: commit arsip -> cd $DEST && git add results/ && git commit -m 'Archive server logs' && git push"
