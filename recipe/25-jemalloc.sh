#!/usr/bin/env bash
# Phase 2b (after 20-blender.sh, re-run after EVERY rebuild -- ninja relinks bin/blender and drops it):
# make blender use jemalloc instead of oneTBB's tbbmalloc proxy, and bundle the library so the
# portable build does not need the libjemalloc2 package on the target.
# Why: on Thor, Cycles' parallel packed-image load livelocked inside tbbmalloc's scalable_malloc
# (random 1-330 s stalls in scene prep on image-heavy scenes, e.g. Open Data junkshop: 8 of 16 runs).
# With jemalloc: 0 of 24, render speed unchanged, peak RSS ~10% LOWER (30-cycle open+render session).
set -euo pipefail
BLENDER_BUILD="${BLENDER_BUILD:-$HOME/blender-build/blender_bin}"
BIN="$BLENDER_BUILD/bin"
JE=""
# ldconfig lives in /sbin (often not on a normal user's PATH); fall back to the Ubuntu aarch64 path.
for c in $( (/sbin/ldconfig -p 2>/dev/null || true) | awk '/libjemalloc\.so\.2 /{print $NF}') \
         /usr/lib/aarch64-linux-gnu/libjemalloc.so.2; do
  [ -e "$c" ] && { JE=$c; break; }
done
[ -n "$JE" ] || { echo "[25-jemalloc] libjemalloc.so.2 not found: sudo apt install libjemalloc2"; exit 1; }
cp -L "$JE" "$BIN/lib/libjemalloc.so.2"
# blender's RUNPATH starts with $ORIGIN/lib, so the bundled copy is the one that loads.
readelf -d "$BIN/blender" | grep -q 'NEEDED.*libjemalloc\.so\.2' || patchelf --add-needed libjemalloc.so.2 "$BIN/blender"
first=$(readelf -d "$BIN/blender" | awk '/NEEDED/{print $NF; exit}')
[ "$first" = "[libjemalloc.so.2]" ] || { echo "[25-jemalloc] jemalloc is not the first NEEDED ($first)"; exit 1; }
# jemalloc is BSD-2-Clause: ship its license with the binary.
[ -d "$BIN/license/others" ] && cp /usr/share/doc/libjemalloc2/copyright "$BIN/license/others/jemalloc.txt"
echo "[25-jemalloc] ok: first NEEDED $first, bundled $(basename "$JE") from $JE"
