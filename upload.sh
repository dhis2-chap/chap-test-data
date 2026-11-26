#!/usr/bin/env bash
# Upload one dataset folder to Chap's POST /v1/crud/datasets/files with plain curl, directly or
# through a DHIS2 route. The same as `chap-test-data upload`, for machines without Python.
#
# Usage: ./upload.sh [--dhis2] [--dry-run] datasets/<name>
#
#   --dhis2    go through the DHIS2 route ($DHIS2_URL/api/routes/$ROUTE_CODE/run/...)
#   --dry-run  validate only (dryRun=true); nothing is imported
#
# Settings (environment):
#   CHAP_URL        Chap API, used without --dhis2         (default http://localhost:8000)
#   CHAP_API_TOKEN  sent as a bearer token without --dhis2 (default: none)
#   DHIS2_URL       DHIS2, used with --dhis2              (default http://localhost:8080)
#   DHIS2_USER / DHIS2_PASSWORD                           (default admin / district)
#   ROUTE_CODE      the route's code in DHIS2             (default chap)
set -euo pipefail

CHAP_URL=${CHAP_URL:-http://localhost:8000}
DHIS2_URL=${DHIS2_URL:-http://localhost:8080}
DHIS2_USER=${DHIS2_USER:-admin}
DHIS2_PASSWORD=${DHIS2_PASSWORD:-district}
ROUTE_CODE=${ROUTE_CODE:-chap}

via=direct
query=""
while [[ $# -gt 0 && $1 == --* ]]; do
  case $1 in
    --dhis2) via=dhis2 ;;
    --dry-run) query="?dryRun=true" ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
dir=${1:?usage: ./upload.sh [--dhis2] [--dry-run] datasets/<name>}

observations=$dir/observations.parquet
locations=$dir/locations.parquet
[[ -f $locations ]] || locations=$dir/locations.geojson
[[ -f $observations && -f $locations ]] || { echo "$dir needs observations.parquet and locations.parquet or .geojson" >&2; exit 2; }

auth=()
if [[ $via == dhis2 ]]; then
  url="$DHIS2_URL/api/routes/$ROUTE_CODE/run/v1/crud/datasets/files$query"
  auth=(-u "$DHIS2_USER:$DHIS2_PASSWORD")
else
  url="$CHAP_URL/v1/crud/datasets/files$query"
  [[ -n ${CHAP_API_TOKEN:-} ]] && auth=(-H "Authorization: Bearer $CHAP_API_TOKEN")
fi

curl -sS ${auth[@]+"${auth[@]}"} -X POST "$url" \
  -F "observations=@$observations" \
  -F "locations=@$locations" \
  -w $'\nHTTP %{http_code} in %{time_total}s\n'
