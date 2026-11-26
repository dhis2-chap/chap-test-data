#!/usr/bin/env bash
# Upload one dataset folder to Chap's POST /v1/crud/datasets/files with plain curl, directly or
# through a DHIS2 route. The same as `chap-test-data upload`, for machines without Python.
#
# Usage: scripts/upload-curl.sh [--dhis2] [--dry-run] [--json] datasets/<name>
#
#   --dhis2    go through the DHIS2 route ($DHIS2_URL/api/routes/$ROUTE_CODE/run/...)
#   --dry-run  validate only (dryRun=true); nothing is imported
#   --json     send the folder's make-dataset.columns.json to make-dataset instead, as the Modeling
#              App does today (generate the dataset with --format json-columns)
#
# Settings (environment):
#   CHAP_URL        Chap API, used without --dhis2         (default http://localhost:8000)
#   CHAP_API_TOKEN  sent as a bearer token without --dhis2 (default: none)
#   DHIS2_URL       DHIS2, used with --dhis2              (default http://localhost:8080)
#   DHIS2_USER / DHIS2_PASSWORD                           (default admin / district)
#   ROUTE_CODE      the route's code in DHIS2             (default chap)
#   BANDWIDTH       send at most this many Mbit/s, as a slow link would (default: as fast as possible)
set -euo pipefail
source "$(dirname "$0")/common.sh"

CHAP_URL=${CHAP_URL:-http://localhost:8000}
DHIS2_URL=${DHIS2_URL:-http://localhost:8080}
DHIS2_USER=${DHIS2_USER:-admin}
DHIS2_PASSWORD=${DHIS2_PASSWORD:-district}
ROUTE_CODE=${ROUTE_CODE:-chap}

via=direct
query=""
json=false
while [[ $# -gt 0 && $1 == --* ]]; do
  case $1 in
    --dhis2) via=dhis2 ;;
    --dry-run) query="?dryRun=true" ;;
    --json) json=true ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
dir=${1:?usage: scripts/upload-curl.sh [--dhis2] [--dry-run] [--json] datasets/<name>}

observations=$dir/observations.parquet
locations=$dir/locations.parquet
[[ -f $locations ]] || locations=$dir/locations.geojson
[[ -f $observations && -f $locations ]] || { echo "$dir needs observations.parquet and locations.parquet or .geojson" >&2; exit 2; }

path=v1/crud/datasets/files
body=(-F "observations=@$observations" -F "locations=@$locations")
if [[ $json == true ]]; then
  [[ -f $dir/make-dataset.columns.json ]] || { echo "$dir has no make-dataset.columns.json" >&2; exit 2; }
  path=v1/analytics/make-dataset
  body=(-H "Content-Type: application/json" --data-binary "@$dir/make-dataset.columns.json")
fi

auth=()
if [[ $via == dhis2 ]]; then
  url="$DHIS2_URL/api/routes/$ROUTE_CODE/run/$path$query"
  auth=(-u "$DHIS2_USER:$DHIS2_PASSWORD")
else
  url="$CHAP_URL/$path$query"
  [[ -n ${CHAP_API_TOKEN:-} ]] && auth=(-H "Authorization: Bearer $CHAP_API_TOKEN")
fi

limit=()
if [[ -n ${BANDWIDTH:-} ]]; then
  limit=(--limit-rate "$(awk -v m="$BANDWIDTH" 'BEGIN { printf "%d", m * 125000 }')")  # Mbit/s to bytes/s
fi

# Show the command, with the password and token hidden.
shown_auth=()
if [[ $via == dhis2 ]]; then
  shown_auth=(-u "$DHIS2_USER:***")
elif [[ -n ${CHAP_API_TOKEN:-} ]]; then
  shown_auth=(-H "Authorization: Bearer ***")
fi
show curl -sS ${shown_auth[@]+"${shown_auth[@]}"} ${limit[@]+"${limit[@]}"} -X POST "$url" "${body[@]}"

curl -sS ${auth[@]+"${auth[@]}"} ${limit[@]+"${limit[@]}"} -X POST "$url" "${body[@]}" \
  -w $'\nHTTP %{http_code} in %{time_total}s\n'
