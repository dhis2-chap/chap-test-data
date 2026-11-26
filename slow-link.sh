#!/usr/bin/env bash
# Upload a dataset over a simulated slow link, with real latency and limited bandwidth, and report
# the time. The upload runs with curl (upload.sh) in a small container on Chap's Docker network,
# whose network interface is shaped with Linux tc netem, so TCP behaves as on a distant link.
#
# Usage: ./slow-link.sh [--delay 150ms] [--rate 10mbit] [upload.sh options] datasets/<name>
#   --delay   added once per round trip (default 100ms)
#   --rate    upload bandwidth (default 10mbit)
#   other options go to upload.sh: --dhis2, --dry-run, --json
#
# Needs Chap started with `docker compose -p chap-test-data up` (and the DHIS2 in dhis2/ for --dhis2).
# Settings: CHAP_NETWORK (default chap-test-data_default), and upload.sh's, with Chap at
# http://chap:8000 and DHIS2 at http://web:8080 as seen from that network.
set -euo pipefail
cd "$(dirname "$0")"

delay=100ms
rate=10mbit
args=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --delay) delay=$2; shift 2 ;;
    --rate) rate=$2; shift 2 ;;
    *) args+=("$1"); shift ;;
  esac
done

docker run --rm --cap-add NET_ADMIN --network "${CHAP_NETWORK:-chap-test-data_default}" \
  -v "$PWD:/work:ro" -w /work \
  -e CHAP_URL="${CHAP_URL:-http://chap:8000}" -e DHIS2_URL="${DHIS2_URL:-http://web:8080}" \
  -e CHAP_API_TOKEN="${CHAP_API_TOKEN:-}" -e DHIS2_USER="${DHIS2_USER:-admin}" \
  -e DHIS2_PASSWORD="${DHIS2_PASSWORD:-district}" -e ROUTE_CODE="${ROUTE_CODE:-chap}" \
  alpine:3.20 sh -c "
    apk add --no-cache --quiet bash curl iproute2 >/dev/null &&
    tc qdisc add dev eth0 root netem delay $delay rate $rate &&
    echo 'link: $delay delay, $rate' &&
    ./upload.sh ${args[*]} | tail -1"
