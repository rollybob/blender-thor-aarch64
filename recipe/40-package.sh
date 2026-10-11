#!/usr/bin/env bash
# Phase 4 (optional): package a portable, SANITIZED tarball of the installed build.
#   OUT_NAME=blender-5.2.2-thor-aarch64-cuda13 recipe/40-package.sh
# Optional: EXCLUDE_FROM=<rsync exclude file>, PRE_PACK_HOOK=<shell snippet run on the staged tree>.
# A build tree remembers where it was built: RUNPATHs, debug info, compiled OSL shaders (.oso), Python
# sysconfig and bytecode caches, even the zstd-compressed Cycles kernels all embed absolute paths under the
# builder's $HOME. This script copies $BLENDER_BUILD/bin to a staging dir and then:
#   1. drops every __pycache__ (Python rebuilds them on first use),
#   2. strips debug info from ELF files (it carries full source paths; not needed to run),
#   3. rewrites the remaining "$HOME/" prefixes - also inside zstd-compressed files - to a SAME-LENGTH
#      placeholder ("/build____.../") so binary string tables stay valid,
#   4. sets blender's / blender-thumbnailer's RUNPATH to just $ORIGIN/lib (everything ships in lib/),
#   5. refuses to package if "$HOME" or the user name still appears anywhere (compressed files included),
# then writes $OUT_NAME.tar.zst (root-owned entries) + SHA256SUMS into $OUT_DIR.
set -euo pipefail
BLENDER_BUILD="${BLENDER_BUILD:-$HOME/blender-build/blender_bin}"
OUT_DIR="${OUT_DIR:-$PWD}"
OUT_NAME="${OUT_NAME:-blender-5.2.2-thor-aarch64-cuda13}"
STAGE="${STAGE:-$OUT_DIR/stage/bin}"
SRC="${STAGE_SRC:-$BLENDER_BUILD/bin}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$STAGE"

echo "[40-package] staging $SRC -> $STAGE"
rsync -a --delete --delete-excluded --exclude '__pycache__' ${EXCLUDE_FROM:+--exclude-from="$EXCLUDE_FROM"} \
  "$SRC/" "$STAGE/"
# Optional hook for release-specific extras (e.g. extra docs/files); STAGE is exported for it.
export STAGE
if [ -n "${PRE_PACK_HOOK:-}" ]; then bash -c "$PRE_PACK_HOOK"; fi

echo "[40-package] stripping debug info, rewriting \$HOME prefix"
python3 "$HERE/sanitize_tree.py" rewrite "$STAGE" "$HOME/"

for b in blender blender-thumbnailer; do
  if [ -e "$STAGE/$b" ]; then patchelf --set-rpath '$ORIGIN/lib' "$STAGE/$b"; fi
done

python3 "$HERE/sanitize_tree.py" scan "$STAGE" "$HOME" "$(id -un)"

cd "$OUT_DIR"
rm -f "$OUT_NAME.tar.zst"
tar -C "$STAGE" --owner=0 --group=0 --numeric-owner -cf - . | zstd -q -19 -T0 -o "$OUT_NAME.tar.zst"
sha256sum "$OUT_NAME.tar.zst" > SHA256SUMS
echo "[40-package] wrote $OUT_DIR/$OUT_NAME.tar.zst"
cat SHA256SUMS
