#!/usr/bin/env bash
# Phase 1: build Blender's dependency stack ("make deps") for Jetson Thor / sm_90+ aarch64.
# This is the long/expensive phase (LLVM, OSL, OIDN, USD, OpenVDB, ffmpeg, ...). Our patch set
# (applied to BLENDER_SRC) fixes the aarch64/CUDA-13 breakages; see PATCHES/ and CHANGES-vs-upstream.md.
set -euo pipefail

: "${BLENDER_SRC:?set BLENDER_SRC to your patched blender v4.5.13 checkout}"
DEPS_BUILD="${DEPS_BUILD:-$HOME/blender-build/deps_arm64}"
LIBDIR="${LIBDIR:-$BLENDER_SRC/lib/linux_arm64}"
CUDA="${CUDA:-/usr/local/cuda-13}"

# ccache first (warms across the 6+ deps iterations), then CUDA 13 nvcc.
export PATH="/usr/lib/ccache:$CUDA/bin:$PATH"
# Reproducible-ish timestamps (matches our build); any fixed value is fine.
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1745584760}"
# CRUCIAL: the top level is Ninja, but sub-builds (LLVM etc.) use "Unix Makefiles" via
# `cmake --build`, which is SERIAL unless CMAKE_BUILD_PARALLEL_LEVEL is set -> otherwise LLVM
# compiles single-threaded for hours.
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-12}"

echo "[10-deps] BLENDER_SRC=$BLENDER_SRC"
echo "[10-deps] DEPS_BUILD=$DEPS_BUILD  LIBDIR=$LIBDIR  CUDA=$CUDA"
cd "$BLENDER_SRC"

cmake -G Ninja -S build_files/build_environment -B "$DEPS_BUILD" -DHARVEST_TARGET="$LIBDIR"

# -j3 keeps a few heavy deps in flight without oversubscribing; -k0 = keep going, surface all errors.
ninja -C "$DEPS_BUILD" -j3 -k0 install

echo "[10-deps] done. Harvested deps -> $LIBDIR"
echo "[10-deps] NOTE: a corrupt tarball download (e.g. gmp MD5 mismatch) is transient:"
echo "          rm the bad file under $DEPS_BUILD/downloads (or packages/) and re-run."
