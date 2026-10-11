# blender-5.2.2-thor-aarch64-cuda13-r2 (unofficial community build)

**r2 replaces the first 5.2.2 download - please update.** That build rendered *instanced* objects
(linked duplicates, motion-blurred objects, subsurface-scattering materials) **invisible on the GPU**
in Cycles CUDA - for example the Open Data "classroom" scene lost all of its desks and chairs and
"monster" lost the monster. Cause: a GCC 14 aarch64 miscompile in Cycles' BVH2 packer (details in
`CHANGES-vs-upstream.md`, patch 0009). CPU renders, EEVEE and the 4.5.13 release were not affected.
Check any build with `blender -b --factory-startup -P verify/cycles_instancing_test.py`.

## What's new in r2
- **Fix:** instanced objects render on the GPU again (PATCHES/0009). GPU renders now match CPU on the
  Open Data scenes and on hair / volume / SSS / motion-blur test scenes.
- **Faster Cycles on Thor:** tuned sm_110 launch bounds for the BVH intersect and shade kernels
  (PATCHES/0010 + 0011). Measured on Thor: Open Data +20/+39/+37% (monster/junkshop/classroom, total
  +30%); fixed-sample renders 1.04-1.35x on 7 scenes, never slower; images match the stock kernel
  within stock-vs-stock run-to-run noise. The stock kernel ships alongside as
  `5.2/scripts/addons_core/cycles/lib/kernel_sm_110.cubin.zst.stock` (see the README-thor-kernel.txt
  next to it to switch back).
- **jemalloc instead of oneTBB's malloc proxy** (recipe/25-jemalloc.sh, library bundled in `lib/`):
  removes random 1-330 s scene-load stalls on image-heavy scenes; peak memory ~10% lower.
- New `verify/cycles_instancing_test.py`.
- Cleaner packaging (recipe/40-package.sh): no build-machine paths or user names inside the tarball,
  debug info stripped, Python caches not shipped (rebuilt on first use), libraries load only from `lib/`.

## Tested configuration
Jetson AGX Thor, JetPack 7 / L4T R38.4.0, Ubuntu 24.04, aarch64, CUDA 13.0, driver 580.xx.
Other sm_90+ CUDA-13 aarch64 hosts should work (kernels ship compute_90 PTX too) but are unverified.
**Not for Jetson Orin (sm_87)** or x86_64.

## What works (all verified at runtime on the build in this release)
- Cycles GPU (CUDA) - native sm_110 cubin (tuned launch bounds), no first-render JIT stall; first render ~0.7s;
  instanced objects (linked duplicates, motion blur, SSS) verified against CPU.
- OpenImageDenoise - CPU and GPU/CUDA (Device: NVIDIA Thor / Type: CUDA / Arch: SM 11.0).
- OSL (Open Shading Language) - CPU.
- EEVEE-Next - GPU-accelerated on **both the OpenGL and Vulkan backends**, GUI and fully headless
  (`--gpu-backend vulkan` renders on Thor's NVIDIA Vulkan 1.4 driver).
- HarfBuzz + FriBidi - complex-script and bidirectional (RTL) text shaping.

## Downloads
- `blender-5.2.2-thor-aarch64-cuda13-r2.tar.zst` (~281 MB) - portable build. Requires JetPack 7 /
  CUDA 13 driver (580+) on the target; we do not bundle NVIDIA libraries.
- `SHA256SUMS` - verify with `sha256sum -c SHA256SUMS`.

## Install / run
```
zstd -d blender-5.2.2-thor-aarch64-cuda13-r2.tar.zst -o blender.tar
tar xf blender.tar
./blender            # or ./blender --version
```
Verify GPU rendering with the scripts in the repo's `verify/` (see README).

## Corresponding source (GPL)
Blender is GPL. The corresponding source for this binary is upstream tag **v5.2.2** plus the patches
in this repo's `PATCHES/` (8 small build-system fixes + 0009 bug fix + 0010/0011 Cycles tuning). Both are provided here. Dependency licenses
are in `licenses/`. Not affiliated with or endorsed by the Blender Foundation.

## Build it yourself
See `README.md` + `recipe/`. Blender 5.2 requires **GCC 14**. The full clone -> patch -> deps ->
blender -> assets -> verify flow was validated from scratch on Jetson AGX Thor and reproduces all
backends (Cycles CUDA, GPU-OIDN, OSL, EEVEE on OpenGL + Vulkan).

## Note vs the 4.5.13 release
The older `v4.5.13-thor-aarch64-cuda13` release remains available for anyone who needs it. 5.2.2 adds
the Vulkan backend and HarfBuzz/FriBidi text shaping on top of the same CUDA/OIDN/OSL feature set.
