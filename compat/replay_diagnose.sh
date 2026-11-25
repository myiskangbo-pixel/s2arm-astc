#!/usr/bin/env bash
# Deterministic, read-only replay of compat/patches/series against compat/UPSTREAM.
# Stops at the FIRST failing patch and records the reconstructed tree after each success.
set -Eeuo pipefail
trap 'rc=$?; echo "DIAG_SCRIPT_ERROR line=$LINENO rc=$rc command=$BASH_COMMAND" >&2; exit "$rc"' ERR
set -x
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
REV="${1:-HEAD}"
git rev-parse -q --verify "$REV^{commit}" >/dev/null
TMP=$(mktemp -d "${TMPDIR:-/tmp}/ryu-replay.XXXXXX")
trap 'rm -rf "$TMP"' EXIT
rd() { git show "$REV:$1"; }
rd compat/UPSTREAM > "$TMP/UPSTREAM"
COMMIT=$(awk -F '\t' '$1=="commit"{print $2}' "$TMP/UPSTREAM")
[ -n "$COMMIT" ] || { echo "FATAL: compat/UPSTREAM has no commit"; exit 2; }
: > "$TMP/root.mk"
: > "$TMP/src.mk"
while IFS=$'\t' read -r k p id mode; do
  [ "$k" = path ] || continue
  [ -n "${mode:-}" ] || { echo "FATAL: missing mode for $p"; exit 2; }
  git cat-file -e "$id" || { echo "FATAL: missing upstream object $id ($p)"; exit 2; }
  type=blob; [ "$mode" = 040000 ] && type=tree
  case "$p" in
    src/*/*) echo "FATAL: unsupported import path depth: $p"; exit 2 ;;
    src/*) printf '%s %s %s\t%s\n' "$mode" "$type" "$id" "${p#src/}" >> "$TMP/src.mk" ;;
    */*) echo "FATAL: unsupported import path: $p"; exit 2 ;;
    *) printf '%s %s %s\t%s\n' "$mode" "$type" "$id" "$p" >> "$TMP/root.mk" ;;
  esac
done < "$TMP/UPSTREAM"
echo "SRC_MKTREE_INPUT_LINES=$(wc -l < "$TMP/src.mk")"
SRC_TREE=$(git mktree < "$TMP/src.mk" 2>"$TMP/src-mktree.err") || { cat "$TMP/src-mktree.err" >&2; exit 3; }
printf '040000 tree %s\tsrc\n' "$SRC_TREE" >> "$TMP/root.mk"
echo "ROOT_MKTREE_INPUT_LINES=$(wc -l < "$TMP/root.mk")"
PRISTINE=$(git mktree < "$TMP/root.mk" 2>"$TMP/root-mktree.err") || { cat "$TMP/root-mktree.err" >&2; exit 3; }
echo "UPSTREAM_COMMIT=$COMMIT"
echo "PRISTINE_TREE=$PRISTINE"
export GIT_INDEX_FILE="$TMP/replay.idx"
git read-tree "$PRISTINE"
rd compat/patches/series | sed 's/#.*//; s/[[:space:]]*$//' | grep -v '^$' > "$TMP/series"
n=0
while IFS= read -r f; do
  n=$((n+1))
  echo "REPLAY[$n] BEGIN $f"
  if ! rd "compat/patches/$f" > "$TMP/current.patch"; then
    echo "FIRST_FAILURE[$n]=$f (patch file missing at $REV)"
    exit 1
  fi
  if ! git apply --cached --check -p1 --whitespace=nowarn "$TMP/current.patch" 2>"$TMP/error"; then
    echo "FIRST_FAILURE[$n]=$f"
    sed 's/^/APPLY_ERROR: /' "$TMP/error"
    echo "INDEX_BLOBS_AT_FAILURE:"
    awk '/^diff --git /{print $4}' "$TMP/current.patch" | sed 's|^b/||' | while IFS= read -r path; do
      git ls-files -s -- "$path" || true
      case "$path" in
        src/Ryujinx.Common/Ryujinx.Common.csproj|src/Ryujinx.Common/Utilities/NetworkHelpers.cs)
          echo "===== INDEX CONTENT BEFORE FAILED PATCH: $path ====="
          git show ":$path" 2>&1 | nl -ba | sed -n '1,90p'
          ;;
      esac
    done
    echo "===== FAILED PATCH HUNKS ====="
    grep -n -A22 -B4 '^diff --git a/src/Ryujinx.Common/Ryujinx.Common.csproj' "$TMP/current.patch" || true
    echo "===== EXPECTED BASE BLOBS FROM PATCH ====="
    grep -E '^index ' "$TMP/current.patch" || true
    exit 1
  fi
  git apply --cached -p1 --whitespace=nowarn "$TMP/current.patch"
  TREE=$(git write-tree)
  echo "REPLAY[$n] OK $f TREE=$TREE"
done < "$TMP/series"
EXPECT=$(git write-tree)
CUR=$(git rev-parse "$REV:compat/tree")
echo "REPLAY_COMPLETE count=$n EXPECT=$EXPECT CUR=$CUR"
if [ "$EXPECT" = "$CUR" ]; then
  echo "RESULT=PASS"
else
  echo "RESULT=TREE_MISMATCH"
  git diff-tree -r --name-status "$EXPECT" "$CUR" | head -100
  exit 1
fi
