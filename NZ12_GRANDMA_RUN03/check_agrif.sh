
#!/bin/bash
set -euo pipefail

BASE="/home/behrense/cylc-run/NZ12_GRANDMA_RUN03/run1/log/job/19400101T0000Z/ocean_ice"
LOG=$(readlink -f "$BASE/NN/job.out")

echo "Log: $LOG"
echo

for tag in \
    "AGRIF TRACE 1" \
    "AGRIF CREATE_VAR BEFORE" \
    "AGRIF CREATE_VAR AFTER" \
    "AGRIF RECURSE BEFORE" \
    "AGRIF RECURSE AFTER" \
    "AGRIF TRACE 2" \
    "AGRIF TRACE 3" \
    "AGRIF GM BEFORE 5" \
    "AGRIF GM AFTER 5"
do
    printf "%-30s %6s\n" "$tag" "$(grep -c "$tag" "$LOG" || true)"
done

echo
echo "Last AGRIF debug lines:"
grep -E 'AGRIF (TRACE|GM|CREATE_VAR|RECURSE)' "$LOG" | tail -40 || true

