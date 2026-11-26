#!/usr/bin/env bash
# Upload one dataset folder to Chap's POST /v1/crud/datasets/files with plain curl, directly or
# through a DHIS2 route. The same as `chap-test-data upload`, for machines without Python.
#
# Usage: scripts/upload-curl.sh [--dhis2] [--dry-run] [--json] [--wait] datasets/<name>
#
#   --dhis2    go through the DHIS2 route ($DHIS2_URL/api/routes/$ROUTE_CODE/run/...)
#   --dry-run  validate only (dryRun=true); nothing is imported
#   --wait     after a real import, wait until Chap has stored the dataset and print its id
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
wait=false
while [[ $# -gt 0 && $1 == --* ]]; do
  case $1 in
    --dhis2) via=dhis2 ;;
    --dry-run) query="?dryRun=true" ;;
    --json) json=true ;;
    --wait) wait=true ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
dir=${1:?usage: scripts/upload-curl.sh [--dhis2] [--dry-run] [--json] [--wait] datasets/<name>}
while [[ $dir == */ && $dir != / ]]; do dir=${dir%/}; done  # datasets/x/ (as tab completion writes it) is datasets/x

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
  base="$DHIS2_URL/api/routes/$ROUTE_CODE/run"
  auth=(-u "$DHIS2_USER:$DHIS2_PASSWORD")
else
  base=$CHAP_URL
  [[ -n ${CHAP_API_TOKEN:-} ]] && auth=(-H "Authorization: Bearer $CHAP_API_TOKEN")
fi
url="$base/$path$query"

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

answer=$(curl -sS ${auth[@]+"${auth[@]}"} ${limit[@]+"${limit[@]}"} -X POST "$url" "${body[@]}" \
  -w $'\nHTTP %{http_code} in %{time_total}s')
printf '%s\n' "$answer"

# The first value of a JSON field in an answer, without needing jq or Python.
field() {
  grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"\{0,1\}[^\",}]*" <<<"$2" | head -1 | sed 's/^[^:]*:[[:space:]]*"\{0,1\}//'
}

if [[ $wait == true && -z $query ]]; then
  [[ ${answer##*$'\n'} == "HTTP 200 "* ]] || exit 1
  job=$(field id "$answer")
  [[ -n $job ]] || { echo "no job id in the answer" >&2; exit 1; }
  show curl -sS ${shown_auth[@]+"${shown_auth[@]}"} "$base/v1/jobs/$job"
  printf 'waiting for job %s' "$job" >&2
  for _ in $(seq 1 600); do
    info=$(curl -sS ${auth[@]+"${auth[@]}"} "$base/v1/jobs/$job")
    status=$(field status "$info")
    case $status in
      SUCCESS) printf ' done\n' >&2; printf 'dataset id: %s\n' "$(field result "$info")"; exit 0 ;;
      FAILURE) printf ' failed: %s\n' "$(field error "$info")" >&2; exit 1 ;;
    esac
    printf '.' >&2
    sleep 3
  done
  echo " still not done after 30 minutes" >&2
  exit 1
fi
