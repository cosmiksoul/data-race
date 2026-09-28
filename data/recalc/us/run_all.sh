#!/usr/bin/env bash
# Полный пересчёт: скачать сырьё (можно пропустить, если raw/ уже есть) и пересчитать.
set -euo pipefail
cd "$(dirname "$0")"
[ "${SKIP_FETCH:-0}" = "1" ] || bash fetch.sh
python3 r1_nipa_share.py
python3 r3_r4_cpi_ces.py
python3 r5_census_construction.py
python3 r6_sec_capex_fcf.py > derived/r6_output.txt && tail -25 derived/r6_output.txt
python3 build_claims.py
