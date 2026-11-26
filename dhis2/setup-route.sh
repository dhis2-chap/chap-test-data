#!/usr/bin/env bash
# Wait for DHIS2, then create (or replace) the route that forwards to Chap.
#
# Settings (environment): DHIS2_URL, DHIS2_USER, DHIS2_PASSWORD, ROUTE_CODE as in upload.sh,
#   CHAP_ROUTE_TARGET  Chap as DHIS2 sees it (default http://chap:8000)
#   CHAP_API_TOKEN     if Chap needs a token, the route sends it (default: none)
set -euo pipefail

DHIS2_URL=${DHIS2_URL:-http://localhost:8080}
DHIS2_USER=${DHIS2_USER:-admin}
DHIS2_PASSWORD=${DHIS2_PASSWORD:-district}
ROUTE_CODE=${ROUTE_CODE:-chap}
CHAP_ROUTE_TARGET=${CHAP_ROUTE_TARGET:-http://chap:8000}
auth=(-u "$DHIS2_USER:$DHIS2_PASSWORD")

printf 'waiting for DHIS2 at %s' "$DHIS2_URL"
until [[ $(curl -s -o /dev/null -w '%{http_code}' "${auth[@]}" "$DHIS2_URL/api/system/info") == 200 ]]; do
  printf '.'
  sleep 5
done
echo " up: $(curl -s "${auth[@]}" "$DHIS2_URL/api/system/info" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])')"

existing=$(curl -s "${auth[@]}" "$DHIS2_URL/api/routes?filter=code:eq:$ROUTE_CODE&fields=id" |
  python3 -c 'import json,sys; r=json.load(sys.stdin)["routes"]; print(r[0]["id"] if r else "")')
if [[ -n $existing ]]; then
  curl -s -o /dev/null "${auth[@]}" -X DELETE "$DHIS2_URL/api/routes/$existing"
fi

body=$(ROUTE_CODE=$ROUTE_CODE TARGET=$CHAP_ROUTE_TARGET python3 -c '
import json, os
route = {"name": "Chap", "code": os.environ["ROUTE_CODE"], "url": os.environ["TARGET"] + "/**", "responseTimeoutSeconds": 30}
token = os.environ.get("CHAP_API_TOKEN")
if token:
    route["headers"] = {"Authorization": f"Bearer {token}"}
print(json.dumps(route))')
curl -s "${auth[@]}" -H 'Content-Type: application/json' -X POST "$DHIS2_URL/api/routes" -d "$body" |
  python3 -c 'import json,sys; d=json.load(sys.stdin); print("route", d.get("httpStatus"), d.get("response", {}).get("uid", d.get("message")))'
echo "uploads go to $DHIS2_URL/api/routes/$ROUTE_CODE/run/v1/crud/datasets/files"
