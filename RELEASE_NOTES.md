# blender-5.2.2-thor-aarch64-cuda13 (unofficial community build)

Blender 5.2.2 LTS built from source for **NVIDIA Jetson AGX Thor** (Blackwell, sm_110) with GPU
rendering enabled - the things no prebuilt aarch64 Blender gives you.

## Tested configuration
Jetson AGX Thor, JetPack 7 / L4T R38.4.0, Ubuntu 24.04, aarch64, CUDA 13.0, driver 580.xx.
Other sm_90+ CUDA-13 aarch64 hosts should work (kernels ship compute_90 PTX too) but are unverified.
**Not for Jetson Orin (sm_87)** or x86_64.

## What works (all verified at runtime on the build in this release)
- Cycles GPU (CUDA) - native sm_110 cubin, no first-render JIT stall; first render ~0.7s.
- OpenImageDenoise - CPU and GPU/CUDA (Device: NVIDIA Thor / Type: CUDA / Arch: SM 11.0).
- OSL (Open Shading Language) - CPU.
- EEVEE-Next - GPU-accelerated on **both the OpenGL and Vulkan backends**, GUI and fully headless
  (`--gpu-backend vulkan` renders on Thor's NVIDIA Vulkan 1.4 driver).
- HarfBuzz + FriBidi - complex-script and bidirectional (RTL) text shaping.

## Downloads
- `blender-5.2.2-thor-aarch64-cuda13.tar.zst` (~293 MB) - portable build. Requires JetPack 7 /
  CUDA 13 driver (580+) on the target; we do not bundle NVIDIA libraries.
- `SHA256SUMS` - verify with `sha256sum -c SHA256SUMS`.

## Install / run
```
zstd -d blender-5.2.2-thor-aarch64-cuda13.tar.zst -o blender.tar
tar xf blender.tar
./blender            # or ./blender --version
```
Verify GPU rendering with the scripts in the repo's `verify/` (see README).

## Corresponding source (GPL)
Blender is GPL. The corresponding source for this binary is upstream tag **v5.2.2** plus the patches
in this repo's `PATCHES/` (8 small build-system fixes). Both are provided here. Dependency licenses
are in `licenses/`. Not affiliated with or endorsed by the Blender Foundation.

## Build it yourself
See `README.md` + `recipe/`. Blender 5.2 requires **GCC 14**. The full clone -> patch -> deps ->
blender -> assets -> verify flow was validated from scratch on Jetson AGX Thor and reproduces all
backends (Cycles CUDA, GPU-OIDN, OSL, EEVEE on OpenGL + Vulkan).

## Note vs the 4.5.13 release
The older `v4.5.13-thor-aarch64-cuda13` release remains available for anyone who needs it. 5.2.2 adds
the Vulkan backend and HarfBuzz/FriBidi text shaping on top of the same CUDA/OIDN/OSL feature set.
