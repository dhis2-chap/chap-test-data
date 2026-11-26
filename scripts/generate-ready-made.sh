#!/usr/bin/env bash
# Write the common test datasets into datasets/, each with the answer Chap should give in
# expected.json, always the same files (seed 42).
#
# Every dataset is written as Parquet (observations.parquet, locations.parquet), as GeoJSON
# (locations.geojson) and as the make-dataset JSON body the Modeling App sends today
# (make-dataset.columns.json). The large datasets come last: a few GB and a few minutes.
#
# Usage: scripts/generate-ready-made.sh [--standard-only]     (--standard-only skips the large ones)
set -euo pipefail
cd "$(dirname "$0")/.."  # the repository root, so datasets/ and the scripts are found
source scripts/common.sh

# A fixed seed, so these datasets are the same on every machine and every run.
gen() {
  show uv run chap-test-data generate --seed 42 "$@"
  uv run --quiet chap-test-data generate --seed 42 "$@"
}
formats=(--format geojson --format json-columns)
monthly=(--period monthly --columns 4 --geometry polygon "${formats[@]}")
weekly=(--period weekly --columns 4 "${formats[@]}")
faulty=(--period monthly --columns 4 --geometry polygon)  # broken on purpose; no other formats

gen 01-small-monthly        --org-units 10   --periods 36  "${monthly[@]}"
gen 02-district-weekly      --org-units 150  --periods 365 "${weekly[@]}" --geometry polygon
gen 03-facility-points      --org-units 1500 --periods 365 "${weekly[@]}"
gen 04-facility-polygons    --org-units 1500 --periods 365 "${weekly[@]}" --geometry polygon --corners 2048
gen 05-facility-points-2000 --org-units 2000 --periods 365 "${weekly[@]}"
gen 06-geojson-locations    --org-units 50   --periods 104 "${weekly[@]}" --geometry polygon --geojson
gen 07-masked-ranges        --org-units 20   --periods 36  "${monthly[@]}" --masked 201801:201803
gen 08-no-metadata          --org-units 10   --periods 24  "${monthly[@]}" --no-metadata
gen 09-covariate-gaps       --org-units 20   --periods 36  "${monthly[@]}" --covariate-gaps 3
gen 10-missing-locations    --org-units 20   --periods 36  "${monthly[@]}" --drop-locations 4
gen 11-bad-duplicate-rows   --org-units 5    --periods 12  "${faulty[@]}" --duplicate-rows 1
gen 12-bad-text-column      --org-units 5    --periods 12  "${faulty[@]}" --text-column parent
gen 13-bad-no-time-period   --org-units 5    --periods 12  "${faulty[@]}" --drop-time-period
gen 14-bad-spec-version     --org-units 5    --periods 12  "${faulty[@]}" --spec-version 2
gen 15-bad-not-parquet      --org-units 5    --periods 12  "${faulty[@]}" --not-parquet
gen 16-named-columns        --org-units 20   --periods 36  --period monthly --geometry polygon "${formats[@]}" \
  --column malaria_cases --column population --column precipitation --column temperature_2m

[[ ${1:-} == --standard-only ]] && exit 0

# Large: 10 years with all 10 value columns. Only the first fits Phase 1; the others are the size
# target for stored files (Phase 2). The 52 million row set gets no JSON: it would be about 5 GB.
gen 20-phase1-max-weekly-10y      --org-units 1900   "${formats[@]}"
gen 21-facilities-20k-weekly-10y  --org-units 20000  "${formats[@]}"
gen 22-org-units-100k-monthly-10y --org-units 100000 --period monthly "${formats[@]}"
gen 23-org-units-100k-weekly-10y  --org-units 100000 --format geojson
