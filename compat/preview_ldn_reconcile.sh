#!/usr/bin/env bash
# Preview a deterministic consolidation of the four overlapping LDN patches.
# This only changes the CI runner's working tree. Review the uploaded patch
# artifact before applying any generated changes to the PR branch.
set -Eeuo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
OUT=${S2A_COMPAT_PREVIEW_OUT:-build/compat-integrity}
PATCH_DIR=compat/patches
SERIES="$PATCH_DIR/series"
MANIFEST="compat/改动清单.md"
mkdir -p "$OUT/superseded"

OBSOLETE=(
  20261121-2020-ldn-route-select-by-system-route.patch
  20261122-2357-ldn-auto-and-socket-route.patch
  20261123-0113-ldn-prefer-lan-gateway-route.patch
  20261123-0820-ldn-dual-protocol-auto.patch
)

present=0
for p in "${OBSOLETE[@]}"; do
  if grep -Fxq "$p" "$SERIES"; then present=$((present + 1)); fi
done

if [ "$present" -eq 0 ]; then
  echo "mode=verify-existing" > "$OUT/summary.txt"
  set +e
  bash compat/verify.sh --rev "$(git rev-parse HEAD)" > "$OUT/verify.log" 2>&1
  rc=$?
  set -e
  cat "$OUT/verify.log"
  echo "verify_rc=$rc" >> "$OUT/summary.txt"
  exit "$rc"
fi

[ "$present" -eq "${#OBSOLETE[@]}" ] || {
  echo "Partial obsolete LDN patch set: found $present of ${#OBSOLETE[@]}" >&2
  exit 2
}

python3 - "$SERIES" "${OBSOLETE[@]}" <<'PY'
import sys
path = sys.argv[1]
remove = set(sys.argv[2:])
with open(path, encoding="utf-8") as f:
    lines = f.read().splitlines()
present = {line.strip() for line in lines}
missing = sorted(remove - present)
if missing:
    raise SystemExit("series is missing expected entries: " + ", ".join(missing))
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(line for line in lines if line.strip() not in remove) + "\n")
PY

for p in "${OBSOLETE[@]}"; do
  [ -f "$PATCH_DIR/$p" ] || { echo "Missing patch file: $p" >&2; exit 2; }
  mv "$PATCH_DIR/$p" "$OUT/superseded/$p"
done

# Record the exact tree delta before generating the consolidated patch.
set +e
bash compat/verify.sh --trees > "$OUT/tree_hashes.txt" 2> "$OUT/tree_hashes.err"
trees_rc=$?
set -e
read -r EXPECT CUR < "$OUT/tree_hashes.txt"
[ -n "${EXPECT:-}" ] && [ -n "${CUR:-}" ] || {
  cat "$OUT/tree_hashes.err" >&2
  echo "verify.sh --trees did not return both tree IDs" >&2
  exit 3
}
git diff-tree -r --name-status "$EXPECT" "$CUR" > "$OUT/tree_diff.txt"

WHY="将四个重叠的 LDN 路由/自动联机补丁合并为一个从现有补丁序列到 compat/tree 的可重放增量补丁；保留 compat/tree 最终源码，不改功能实现。"
set +e
bash compat/patch_new.sh ldn-reconcile "$WHY" > "$OUT/patch_new.log" 2>&1
rc=$?
set -e
cat "$OUT/patch_new.log"
echo "patch_new_rc=$rc" > "$OUT/summary.txt"
[ "$rc" -eq 0 ] || exit "$rc"

NEW=$(grep -Eo '[0-9]{8}-[0-9]{4}-ldn-reconcile\.patch' "$OUT/patch_new.log" | tail -1)
[ -n "$NEW" ] || { echo "Could not identify generated patch name" >&2; exit 4; }
cp "$PATCH_DIR/$NEW" "$OUT/$NEW"
cp "$SERIES" "$OUT/series"

# Keep the manifest's historical entries, but mark the four superseded patches.
python3 - "$MANIFEST" "$NEW" "${OBSOLETE[@]}" <<'PY'
import sys
path, new = sys.argv[1], sys.argv[2]
obsolete = set(sys.argv[3:])
with open(path, encoding="utf-8") as f:
    lines = f.read().splitlines()
out = []
for line in lines:
    if line.startswith("|"):
        cells = line.split("|")
        if len(cells) >= 4 and cells[1].strip() in obsolete:
            cells[3] = cells[3].rstrip() + f"（已由 {new} 合并替代）"
            line = "|".join(cells)
    out.append(line)
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
PY
cp "$MANIFEST" "$OUT/改动清单.md"

set +e
bash compat/verify.sh > "$OUT/verify.log" 2>&1
verify_rc=$?
set -e
cat "$OUT/verify.log"
echo "mode=preview-generated" >> "$OUT/summary.txt"
echo "patch=$NEW" >> "$OUT/summary.txt"
echo "verify_rc=$verify_rc" >> "$OUT/summary.txt"
echo "patch_sha256=$(shasum -a 256 "$OUT/$NEW" | awk '{print $1}')" >> "$OUT/summary.txt"
echo "patch_files=$(grep -c '^diff --git' "$OUT/$NEW")" >> "$OUT/summary.txt"
exit "$verify_rc"
