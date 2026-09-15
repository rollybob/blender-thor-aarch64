# Blender 4.5.13 for Jetson Thor (aarch64) with CUDA Cycles + OIDN + OSL

An **unofficial community build recipe** (and optional prebuilt binary) of Blender 4.5.13 LTS for
NVIDIA **Jetson AGX Thor** (Blackwell, sm_110) with GPU rendering enabled - the things no prebuilt
aarch64 Blender gives you:

- **Cycles GPU (CUDA)** on the Blackwell GPU - native `sm_110` cubin (no first-render JIT stall) plus
  `compute_90` PTX fallback for any sm_90+ device.
- **OpenImageDenoise** on both **CPU and GPU/CUDA** (the GPU path is the tricky one - see below).
- **OSL** (Open Shading Language) on CPU.
- **EEVEE-Next** realtime rasterizer, GPU-accelerated, works both in the GUI and fully headless.

> Not affiliated with or endorsed by the Blender Foundation. "Blender" is their trademark; this is a
> modified community build, named to avoid any confusion with official releases.

## Who this is for
- **Tested on:** Jetson AGX Thor, JetPack 7 / L4T R38.4.0, Ubuntu 24.04, aarch64, CUDA 13.0,
  driver 580.xx.
- **Should also work (unverified):** other sm_90+ CUDA-13 aarch64 hosts (the Cycles kernels include
  compute_90 PTX). Treat as best-effort.
- **NOT supported:** Jetson **Orin (sm_87)** or older, x86_64 (use official builds), Windows/macOS.

## Option A - run the prebuilt binary (if a Release is attached)
1. Requires the target to have JetPack 7 / CUDA 13 driver (580+) installed (we do not bundle NVIDIA
   libraries; Cycles dlopens the system CUDA driver).
2. Download `blender-4.5.13-thor-aarch64-cuda13.tar.zst` from Releases, verify against `SHA256SUMS`,
   extract, run `./blender`.
3. Sanity-check GPU rendering with the scripts in `verify/` (below).

## Option B - build from source (the golden path)
Everything is in `recipe/`. Read `recipe/00-prereqs.md` first, then:
```
# 1. get + patch the source (see 00-prereqs.md for the LFS details - important!)
# GIT_LFS_SKIP_SMUDGE avoids smudging every LFS blob on checkout (a plain clone can hang);
# we then pull only the datafiles we need.
GIT_LFS_SKIP_SMUDGE=1 git clone --branch v4.5.13 --single-branch \
    https://github.com/blender/blender.git && cd blender
git config lfs.url https://projects.blender.org/blender/blender.git/info/lfs
git lfs pull --include="release/datafiles/**"
git am /path/to/this-repo/PATCHES/000*.patch

# 2. build
export BLENDER_SRC=$PWD
/path/to/this-repo/recipe/10-deps.sh      # dependency stack (long: LLVM/OSL/OIDN/USD/...)
/path/to/this-repo/recipe/20-blender.sh   # Blender itself (~15 min)
/path/to/this-repo/recipe/30-assets.sh    # un-stub bundled brush/geometry-node assets
```
The build lands at `$BLENDER_BUILD/bin/blender` (default `~/blender-build/blender_bin/bin/blender`).

## Verify it actually uses the GPU (do this!)
A build that *compiles* is not proof a GPU feature *works* - the OIDN GPU path in particular fails
silently to CPU if built wrong. Runtime proofs in `verify/`:
- `blender -b -P verify/cycles_gpu_test.py` - CUDA device = 'NVIDIA Thor', non-black denoised render.
  First render is ~1s with the native sm_110 cubin (was ~371s with PTX-JIT only).
- `OIDN_VERBOSE=2 blender -b -P verify/cycles_oidn_gpu_test.py` - OIDN banner must say `Type: CUDA`.
- `verify/oidn_cuda_test.c` - standalone OIDN C-API GPU-device test (compile + run against libOpenImageDenoise).
- `blender -b -P verify/cycles_osl_test.py` - OSL shading system active; render tracks the OSL source.
- `blender -b -P verify/eevee_headless_test.py` - headless EEVEE renders a non-black PNG (no X needed).

## What's different from stock, and why
See `CHANGES-vs-upstream.md` for a per-patch explanation. Short version: 8 small `.cmake` fixes for
aarch64/CUDA-13 breakages (libtool splits, setuptools crash, wayland libdir, ffmpeg/libdrm link) plus
the two that matter most - CPU-OSL by disabling the broken OptiX shadeops path on ARM, and GPU-OIDN
via `OIDN_DEVICE_CUDA_API=RuntimeStatic` (dodging a silent `__cudaLaunchKernel` dlopen failure).

## Licensing
- Blender is **GPL** (GPLv2-or-later; GPLv3 for parts). The corresponding source for any binary here
  is upstream tag **v4.5.13** plus the patches in `PATCHES/` - both are provided.
- Bundled dependencies keep their own licenses; see `licenses/`.
- Our own files in this repo (recipe scripts, docs, verify helpers) are dedicated to the public
  domain under CC0 - see `LICENSE`.
