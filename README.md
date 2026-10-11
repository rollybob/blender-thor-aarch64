# Blender 5.2.2 for Jetson Thor (aarch64) with CUDA Cycles + OIDN + OSL + Vulkan

An **unofficial community build recipe** (and optional prebuilt binary) of Blender 5.2.2 LTS for
NVIDIA **Jetson AGX Thor** (Blackwell, sm_110) with GPU rendering enabled - the things no prebuilt
aarch64 Blender gives you:

- **Cycles GPU (CUDA)** on the Blackwell GPU - native `sm_110` cubin (no first-render JIT stall) plus
  `compute_90` PTX fallback for any sm_90+ device.
- **OpenImageDenoise** on both **CPU and GPU/CUDA** (the GPU path is the tricky one - see below).
- **OSL** (Open Shading Language) on CPU.
- **EEVEE-Next** realtime rasterizer on **both the OpenGL and Vulkan backends**, GPU-accelerated,
  working in the GUI and fully headless (Thor ships a working NVIDIA Vulkan 1.4 driver).
- **HarfBuzz + FriBidi** for complex-script and bidirectional (RTL) text shaping.

> **Update 2026-10-11 - please use release `r2`.** The first 5.2.2 download rendered *instanced* objects
> (linked duplicates, motion-blurred objects, subsurface-scattering materials) **invisible on the GPU**
> (Cycles CUDA) - e.g. the Open Data "classroom" scene lost all its desks and chairs. Cause: a GCC 14
> aarch64 miscompile in Cycles' BVH2 packer; fixed by `PATCHES/0009`. CPU and EEVEE renders were not
> affected, nor is the 4.5.13 release. `verify/cycles_instancing_test.py` checks any build for it.
> r2 also brings tuned sm_110 Cycles kernels (Open Data +30% on Thor) and jemalloc (no scene-load stalls).

> Not affiliated with or endorsed by the Blender Foundation. "Blender" is their trademark; this is a
> modified community build, named to avoid any confusion with official releases.

## Who this is for
- **Tested on:** Jetson AGX Thor, JetPack 7 / L4T R38.4.0, Ubuntu 24.04, aarch64, CUDA 13.0,
  driver 580.xx.
- **Should also work (unverified):** other sm_90+ CUDA-13 aarch64 hosts (the Cycles kernels include
  compute_90 PTX). Treat as best-effort.
- **NOT supported:** Jetson **Orin (sm_87)** or older, x86_64 (use official builds), Windows/macOS.

> Older release: **Blender 4.5.13 LTS** for the same platform is still available under
> [Releases](../../releases) (`v4.5.13-thor-aarch64-cuda13`) if you need it.

## Option A - run the prebuilt binary (if a Release is attached)
1. Requires the target to have JetPack 7 / CUDA 13 driver (580+) installed (we do not bundle NVIDIA
   libraries; Cycles dlopens the system CUDA driver).
2. Download `blender-5.2.2-thor-aarch64-cuda13-r2.tar.zst` from Releases, verify against `SHA256SUMS`,
   extract, run `./blender`.
3. Sanity-check GPU rendering with the scripts in `verify/` (below).

## Option B - build from source (the golden path)
Everything is in `recipe/`. Read `recipe/00-prereqs.md` first (note: **Blender 5.2 requires GCC 14**),
then:
```
# 1. get + patch the source (see 00-prereqs.md for the LFS details - important!)
# GIT_LFS_SKIP_SMUDGE avoids smudging every LFS blob on checkout (a plain clone can hang);
# we then pull only the datafiles we need.
GIT_LFS_SKIP_SMUDGE=1 git clone --branch v5.2.2 --single-branch \
    https://github.com/blender/blender.git && cd blender
git config lfs.url https://projects.blender.org/blender/blender.git/info/lfs
git lfs pull --include="release/datafiles/**"
git am /path/to/this-repo/PATCHES/00*.patch   # 0001..0011

# 2. build
export BLENDER_SRC=$PWD
/path/to/this-repo/recipe/10-deps.sh      # dependency stack (long: LLVM/OSL/OIDN/USD/...)
/path/to/this-repo/recipe/20-blender.sh   # Blender itself, built with GCC 14 (~15-20 min)
/path/to/this-repo/recipe/25-jemalloc.sh  # link + bundle jemalloc (re-run after EVERY rebuild)
# optional: a portable tarball with build-machine paths removed (refuses to pack if any remain)
OUT_NAME=my-blender /path/to/this-repo/recipe/40-package.sh
/path/to/this-repo/recipe/30-assets.sh    # un-stub bundled brush/geometry-node assets
```
The build lands at `$BLENDER_BUILD/bin/blender` (default `~/blender-build/blender_bin/bin/blender`).

## Verify it actually uses the GPU (do this!)
A build that *compiles* is not proof a GPU feature *works* - the OIDN GPU path in particular fails
silently to CPU if built wrong. Runtime proofs in `verify/`:
- `blender -b -P verify/cycles_gpu_test.py` - CUDA device = 'NVIDIA Thor', non-black denoised render.
  First render is ~0.7s with the native sm_110 cubin (was ~371s with PTX-JIT only).
- `OIDN_VERBOSE=2 blender -b -P verify/cycles_oidn_gpu_test.py` - OIDN banner must say
  `Type: CUDA` / `Arch: SM 11.0`.
- `verify/oidn_cuda_test.c` - standalone OIDN C-API GPU-device test (compile + run against libOpenImageDenoise).
- `blender -b -P verify/cycles_osl_test.py` - OSL shading system active; render tracks the OSL source.
- `blender --gpu-backend opengl -b -P verify/eevee_headless_test.py` - headless EEVEE renders a non-black PNG.
- `blender --gpu-backend vulkan -b -P verify/eevee_headless_test.py` - same, on the Vulkan backend.
- `blender -b --factory-startup -P verify/cycles_instancing_test.py` - linked duplicates, motion blur and
  SSS objects render on the GPU exactly as on the CPU (`RESULT: OK`). The first 5.2.2 build fails this.

## What's different from stock, and why
See `CHANGES-vs-upstream.md` for a per-patch explanation. Short version: small `.cmake` fixes for
aarch64/CUDA-13 breakages plus two build-graph fixes upstream 5.2 is missing. The two that matter
most are CPU-OSL (disabling the broken OptiX shadeops path on ARM) and GPU-OIDN via
`OIDN_DEVICE_CUDA_API=RuntimeStatic` with sm_110 arch fixups (dodging a silent
`__cudaLaunchKernel` dlopen failure). Vulkan / HarfBuzz / FriBidi are configure flags in
`recipe/20-blender.sh`, not source patches. Since r2: `0009` fixes instanced objects vanishing on the
GPU (GCC 14 aarch64 miscompile), `0010`/`0011` tune the sm_110 Cycles kernels' launch bounds, and
`recipe/25-jemalloc.sh` swaps oneTBB's malloc proxy for jemalloc.

## Licensing
- Blender is **GPL** (GPLv2-or-later; GPLv3 for parts). The corresponding source for any binary here
  is upstream tag **v5.2.2** plus the patches in `PATCHES/` - both are provided.
- Bundled dependencies keep their own licenses; see `licenses/`.
- Our own files in this repo (recipe scripts, docs, verify helpers) are dedicated to the public
  domain under CC0 - see `LICENSE`.
