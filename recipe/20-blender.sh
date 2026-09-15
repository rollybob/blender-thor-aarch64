#!/usr/bin/env bash
# Phase 2: configure + build + install Blender itself against the harvested deps (~15 min compile).
set -euo pipefail

: "${BLENDER_SRC:?set BLENDER_SRC to your patched blender v4.5.13 checkout}"
BLENDER_BUILD="${BLENDER_BUILD:-$HOME/blender-build/blender_bin}"
LIBDIR="${LIBDIR:-$BLENDER_SRC/lib/linux_arm64}"
CUDA="${CUDA:-/usr/local/cuda-13}"

export PATH="/usr/lib/ccache:$CUDA/bin:$PATH"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1745584760}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-12}"

# Cycles CUDA arch:
#   sm_110    = native cubin for Thor -> NO first-render PTX->SASS JIT (~371s saved).
#   compute_90 = Hopper PTX fallback -> JITs to any sm_90+ at runtime (portability + safety net).
# NOTE: compute_120 would be WRONG here - consumer-Blackwell PTX needs sm>=12.0; Thor is sm_110.
CYCLES_ARCH="${CYCLES_ARCH:-sm_110;compute_90}"

echo "[20-blender] BLENDER_SRC=$BLENDER_SRC  BUILD=$BLENDER_BUILD"
echo "[20-blender] LIBDIR=$LIBDIR  CUDA=$CUDA  CYCLES_ARCH=$CYCLES_ARCH"
cd "$BLENDER_SRC"

# -DLIBDIR is REQUIRED: platform_unix.cmake only auto-detects the libdir when it carries a .git
# submodule marker, which a harvested lib/ tree does not have.
cmake -G Ninja -S "$BLENDER_SRC" -B "$BLENDER_BUILD" \
  -DLIBDIR="$LIBDIR" \
  -DWITH_CYCLES_CUDA_BINARIES=ON \
  -DCYCLES_CUDA_BINARIES_ARCH="$CYCLES_ARCH" \
  -DWITH_CYCLES_DEVICE_OPTIX=OFF \
  -DWITH_OPENIMAGEDENOISE=ON \
  -DWITH_CYCLES_OSL=ON \
  -DWITH_VULKAN_BACKEND=OFF \
  -DCUDA_TOOLKIT_ROOT_DIR="$CUDA" \
  -DWITH_INSTALL_PORTABLE=ON

ninja -C "$BLENDER_BUILD" -j12 install

echo "[20-blender] done -> $BLENDER_BUILD/bin/blender"
echo "[20-blender] next: run 30-assets.sh to un-stub the bundled brush/geometry-node assets."
