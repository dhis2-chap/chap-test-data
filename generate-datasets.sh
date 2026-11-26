#!/usr/bin/env bash
# Write the standard test datasets into datasets/, each with the answer Chap should give in
# expected.json, always the same files (seed 42). With --large, also the large examples
# (up to 52 million rows, about 600 MB).
#
# Usage: ./generate-datasets.sh [--large]
set -euo pipefail
cd "$(dirname "$0")"

# A fixed seed, so these datasets are the same on every machine and every run.
gen() { uv run --quiet chap-test-data generate --seed 42 "$@"; }
monthly=(--period monthly --columns 4 --geometry polygon)
weekly=(--period weekly --columns 4)

gen 01-small-monthly        --org-units 10   --periods 36  "${monthly[@]}"
gen 02-district-weekly      --org-units 150  --periods 365 "${weekly[@]}" --geometry polygon --corners 512
gen 03-facility-points      --org-units 1500 --periods 365 "${weekly[@]}"
gen 04-facility-polygons    --org-units 1500 --periods 365 "${weekly[@]}" --geometry polygon --corners 2048
gen 05-facility-points-2000 --org-units 2000 --periods 365 "${weekly[@]}"
gen 06-geojson-locations    --org-units 50   --periods 104 "${weekly[@]}" --geometry polygon --geojson
gen 07-masked-ranges        --org-units 20   --periods 36  "${monthly[@]}" --masked 201801:201803
gen 08-no-metadata          --org-units 10   --periods 24  "${monthly[@]}" --no-metadata
gen 09-covariate-gaps       --org-units 20   --periods 36  "${monthly[@]}" --covariate-gaps 3
gen 10-missing-locations    --org-units 20   --periods 36  "${monthly[@]}" --drop-locations 4
gen 11-bad-duplicate-rows   --org-units 5    --periods 12  "${monthly[@]}" --duplicate-rows 1
gen 12-bad-text-column      --org-units 5    --periods 12  "${monthly[@]}" --text-column parent
gen 13-bad-no-time-period   --org-units 5    --periods 12  "${monthly[@]}" --drop-time-period
gen 14-bad-spec-version     --org-units 5    --periods 12  "${monthly[@]}" --spec-version 2
gen 15-bad-not-parquet      --org-units 5    --periods 12  "${monthly[@]}" --not-parquet
gen 16-named-columns        --org-units 20   --periods 36  --period monthly --geometry polygon \
  --column malaria_cases --column population --column precipitation --column temperature_2m

if [[ ${1:-} == --large ]]; then
  # 10 years with all 10 columns. Only the first fits Phase 1; the others are its size target.
  gen 20-phase1-max-weekly-10y     --org-units 1900
  gen 21-facilities-20k-weekly-10y --org-units 20000
  gen 22-org-units-100k-monthly-10y --org-units 100000 --period monthly
  gen 23-org-units-100k-weekly-10y  --org-units 100000
fi
