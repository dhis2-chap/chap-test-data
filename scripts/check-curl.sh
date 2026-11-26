#!/usr/bin/env bash
# Dry-run every dataset under a folder with plain curl and compare Chap's answer with its
# expected.json. The same as `chap-test-data check`, for machines without uv.
#
# Usage: scripts/check-curl.sh [--dhis2] [folder]     (default folder: datasets; settings as upload-curl.sh)
set -uo pipefail
cd "$(dirname "$0")/.."  # the repository root, so datasets/ and the scripts are found

args=()
[[ ${1:-} == --dhis2 ]] && { args=(--dhis2); shift; }
root=${1:-datasets}

failed=0
printf '%-34s %-6s %-38s %s\n' dataset result expected got
for dir in "$root"/*/; do
  dir=${dir%/}
  [[ -f $dir/expected.json ]] || continue
  answer=$(scripts/upload-curl.sh ${args[@]+"${args[@]}"} --dry-run "$dir")
  verdict=$(python3 - "$dir/expected.json" "$answer" <<'PY'
import json, sys
expected = json.load(open(sys.argv[1]))
body, _, status = sys.argv[2].rpartition("\n")
http = int(status.split()[1])
try:
    answer = json.loads(body)
except json.JSONDecodeError:
    answer = {"raw": body[:200]}
if http == 200:
    got = f"200 imported={answer.get('importedCount')} rejected={len(answer.get('rejected', []))}"
    ok = http == expected["http"] and answer.get("importedCount") == expected["importedCount"] \
        and len(answer.get("rejected", [])) == expected["rejected"]
else:
    got = f"{http} {json.dumps(answer.get('detail', answer))[:70]}"
    ok = http == expected["http"] and expected.get("detail", "") in json.dumps(answer)
want = (f"200 imported={expected['importedCount']} rejected={expected['rejected']}" if expected["http"] == 200
        else f"{expected['http']} ...{expected.get('detail', '')}...")
print(f"{'ok' if ok else 'FAIL'}\t{want}\t{got}")
PY
)
  IFS=$'\t' read -r result want got <<<"$verdict"
  printf '%-34s %-6s %-38s %s\n' "$(basename "$dir")" "$result" "$want" "$got"
  [[ $result == ok ]] || failed=$((failed + 1))
done
echo
[[ $failed -eq 0 ]] && echo "all datasets gave the expected answer" || echo "$failed dataset(s) differ from expected.json"
exit $((failed > 0))
