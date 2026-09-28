#!/usr/bin/env bash
# Скачивает сырые данные для пересчёта цифр блоков 02 и 05 (США).
# Запуск: bash fetch.sh   (файлы ложатся в ./raw). Скачано 28.09.2026.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
cd raw

# --- FRED (BEA NIPA, BLS CPI, BLS CES) ---
# A679RC1Q027SBEA  Private fixed investment in information processing equipment and software (NIPA 5.3.5), млрд $ SAAR
# Y034RC1Q027SBEA  ... Equipment: Information processing equipment (NIPA 5.5.5)
# B935RC1Q027SBEA  ... Information processing equipment: Computers and peripheral equipment
# B985RC1Q027SBEA  ... Intellectual property products: Software (NIPA 5.6.5)
# Y033RC1Q027SBEA  ... Nonresidential: Equipment (всё оборудование)
# Y001RC1Q027SBEA  ... Nonresidential: Intellectual property products
# GDP              номинальный ВВП, млрд $ SAAR
# CUSR0000SEEE01   CPI-U: Computers, peripherals, and smart home assistants (SA), дек. 2007 = 100
# CUUR0000SEEE01   то же, NSA
# CPIAUCSL         CPI-U all items (SA) — для сравнения
# CES5051800001    All Employees, Computing Infrastructure Providers, Data Processing, Web Hosting, and Related Services (SA), тыс.
for s in A679RC1Q027SBEA Y034RC1Q027SBEA B935RC1Q027SBEA B985RC1Q027SBEA Y033RC1Q027SBEA Y001RC1Q027SBEA GDP \
         CUSR0000SEEE01 CUUR0000SEEE01 CPIAUCSL CES5051800001; do
  curl -sS -o "$s.csv" "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$s"
done

# --- Census, Value of Construction Put in Place (C30) ---
# privsatime.xlsx — частное строительство, SAAR, млн $, помесячно с янв. 1993 (колонка «Data center» — с янв. 2014)
# privtime.xlsx   — то же без сезонной корректировки (для календарных годовых сумм)
curl -sS -o privsatime.xlsx "https://www.census.gov/construction/c30/xlsx/privsatime.xlsx"
curl -sS -o privtime.xlsx   "https://www.census.gov/construction/c30/xlsx/privtime.xlsx"

# Конкорданс NAICS 2017 → 2022 (проверка непрерывности отрасли 518210 для CES5051800001)
curl -sS -o naics_2017_to_2022.xlsx "https://www.census.gov/naics/concordances/2017_to_2022_NAICS.xlsx"

# --- SEC XBRL companyfacts (нужен User-Agent с контактом) ---
UA="research cosmiksoul research@example.com"
# Alphabet, Microsoft, Amazon, Meta, Oracle + Google Inc. (до реорганизации 2015, для ряда «с 2009»)
for c in 0001652044 0000789019 0001018724 0001326801 0001341439 0001288776; do
  curl -sS --compressed -H "User-Agent: $UA" -o "CIK$c.json" "https://data.sec.gov/api/xbrl/companyfacts/CIK$c.json"
  sleep 0.3
done
ls -la
