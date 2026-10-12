# What we changed vs upstream Blender v5.2.2, and why

The source delta is small (11 patches; see `PATCHES/`; 0009-0011 added in release r2). Each fix corresponds to a concrete wall hit
when building Blender with CUDA-Cycles + OIDN + OSL + Vulkan on Jetson Thor (Blackwell sm_110,
JetPack 7, CUDA 13, Ubuntu 24.04 aarch64). The Cycles CUDA arch selection, the Vulkan/HarfBuzz/FriBidi
feature flags, and the GCC-14 compiler pin are **not** source patches - they are configure flags set
by `recipe/20-blender.sh` (see "Configure-flag choices" at the bottom).

## The patches (PATCHES/000*.patch)

### 0001 - deps/cython: tolerate setuptools 63.2.0 install_egg_info crash (|| true)
setuptools 63.2.0 crashes in `install_egg_info` AFTER Cython's files are already installed and numpy
has built. Appending `|| true` lets the deps build continue past the harmless post-install crash.

### 0002 - deps/wayland: harvest wayland/lib (aarch64) not wayland/lib64
On aarch64 the wayland dependency installs into `lib/`, not `lib64/`; fix the harvest path so the
files are actually collected into the harvest target.

### 0003 - deps/osl: do not force OSL_USE_OPTIX=ON on ARM (CPU-only OSL)
Upstream forces OSL's OptiX path on. That path compiles OSL shadeops to PTX via clang
(LLVM_COMPILE_CUDA), which breaks on CUDA 13 + clang 17 in `texture_fetch_functions.h`. It is also
pointless on Jetson: there is no OptiX runtime and Blender is built `WITH_CYCLES_DEVICE_OPTIX=OFF`,
so Cycles runs OSL on the CPU regardless. Leaving `OSL_USE_OPTIX=OFF` means `find_package(CUDA)`
never runs and the CUDA_FOUND-gated GPU-shadeops block is skipped; only the CPU LLVM-bitcode path
builds. Result: working CPU OSL (GPU-OSL is not available on Jetson, which is expected, not a gap).

### 0004 - deps/oidn: enable CUDA GPU device on sm_110 (RuntimeStatic + arch fixups)  [the important one]
Enables GPU-accelerated OpenImageDenoise on Thor. Two parts:
 1. `-DOIDN_DEVICE_CUDA_API=RuntimeStatic`. OIDN's default `Driver` backend (`curtn.cpp` shim) does
    not provide `__cudaLaunchKernel` - the internal symbol CUDA 13's nvcc lowers `<<<>>>` launches to.
    So `device_cuda.so` builds fine but fails to dlopen at runtime with
    `undefined symbol: __cudaLaunchKernel`, and OIDN SILENTLY falls back to the CPU denoiser (no
    error). `RuntimeStatic` links the real `libcudart_static.a`, which has the symbol.
 2. sm_110 arch fixups via `OIDN_PATCH_COMMAND` (OIDN 2.5.0's gencode is SASS-only, no PTX -> Thor
    needs a native sm_110 cubin): add 110 to `OIDN_CUDA_SM_FLAGS` and `OIDN_CUDA_SM80_FLAGS`, and
    widen `isSupported()` from `<= 109` to `<= 119` (stock 2.5.0 accepts 75..109 and 120..129,
    excluding Thor's 110).

### 0005 - deps: annotate CPU-only OSL; exclude wayland_weston on aarch64
Document why `osl.cmake` is CPU-only (see 0003) and exclude the `wayland_weston` test compositor
(needs cairo/xcb-randr/libinput; not needed for headless or normal Cycles/EEVEE use). `libglu` and
`mesa` - excluded on ARM in the 4.5 recipe - were dropped upstream in Blender 5.x, so only the weston
exclusion remains.

### 0006 - blender: link libdrm for our DRM/kmsgrab-enabled deps-ffmpeg
Our deps ffmpeg is built with DRM/kmsgrab; link `libdrm` so the Blender link step resolves the DRM
symbols.

### 0007 - deps/vulkan: external_spirv_tools must depend on external_python
`external_spirv_tools` configures with `-DPython3_EXECUTABLE=${PYTHON_BINARY}` and does
`find_package(Python3 REQUIRED COMPONENTS Interpreter)`, but upstream 5.2's `add_dependencies()`
lists only `external_spirv_headers`. Under a parallel deps build (`ninja -j`) spirv_tools' configure
can run before the deps Python is built and fail with
`Could NOT find Python3 ... Cannot run the interpreter`. `shaderc.cmake` already declares this edge;
spirv_tools should too. (Needed once Vulkan is enabled, which pulls spirv_tools into the build.)

### 0008 - deps/zstandard: depend on external_python_site_packages (for 'packaging')
zstandard 0.25.0's `setup.py` does `from packaging.version import Version`. `packaging` is installed
into the deps Python by `external_python_site_packages`, but `external_zstandard`'s add_dependencies
lists only `external_python` and `external_zstd`. Under a parallel build zstandard can run before
`packaging` is installed and fail with `ModuleNotFoundError: No module named 'packaging'`. numpy and
cython (also built as separate externals) already declare this edge; zstandard should too.

### 0009 - Cycles: instanced objects invisible in BVH2 on aarch64 GCC builds  [r2; a real bug fix]
`BVH2::pack_instances` copied each leaf of an instanced object's BVH and patched `.x`/`.y` in place.
`int4` is an sse2neon `__m128i` union on aarch64, and GCC 14.2 (-O2/-O3) compiled that as a 64-bit
`add v.2s` followed by a 128-bit store - the 64-bit-form add zeroes the upper half of the register,
so every merged leaf was stored with visibility = 0 and primitive type = 0. Traversal then matched no
primitive type and silently skipped the triangles: linked duplicates, motion-blurred objects and SSS
objects (all kept instanced) were invisible on CUDA, and on CPU when forced to the BVH2 layout.
Only BVH2 render paths read these leaves (CUDA without OptiX, CPU without Embree, HIP without HIP-RT),
which is why it slipped through. The fix builds the leaf with `make_int4(...)` from explicit lanes.
Compilers, tested with the standalone `verify/gcc_slp_union_check.cpp` (aarch64): GCC 14.2.0 (Ubuntu
24.04's `g++-14`) FAILS at -O2/-O3; GCC 13.3, 14.4, 15.3 and clang 18 are correct. The culprit is GCC's
SLP vectorizer (`-fno-tree-slp-vectorize` avoids it); it needs the union write-ints/read-vector pattern
(a defaulted copy or a plain struct compiles correctly). Independently found and documented at
github.com/aliaholes/gcc14-aarch64-zeroed-lanes, which also reports 14.1 affected and 14.3 fixed. So
with GCC >= 14.3 this patch is not needed, but it is harmless and keeps any GCC 14 build safe.
Proof: `verify/cycles_instancing_test.py` (fails on the first 5.2.2 build, passes with 0009); the Open
Data classroom/junkshop/monster scenes now render on GPU as on CPU.

### 0010 + 0011 - Cycles CUDA: sm_110 launch bounds for the BVH intersect and shade kernels  [r2; perf]
On Thor the BVH intersect kernels are latency-bound with too few warps in flight (ncu: 15% achieved
occupancy vs 33% register-limited). 0010 adds opt-in knobs (unset = stock); 0011 makes the measured
best the sm_110 default: intersect closest/shadow in 64-thread blocks capped at 64 registers,
shade_surface capped at 80 registers. Define `THOR_STOCK_LAUNCH_BOUNDS` to build stock kernels; the
release also ships the stock cubin as `kernel_sm_110.cubin.zst.stock`. Every other architecture is
untouched. Measured on Thor with 0009 applied: Open Data +20/+39/+37% (monster/junkshop/classroom),
fixed-sample renders 1.04-1.35x on 7 scenes (incl. hair, volumes, SSS, motion blur), never slower;
images match stock within stock-vs-stock run-to-run noise.

## Post-build step (r2): jemalloc - recipe/25-jemalloc.sh
Adds `libjemalloc.so.2` as blender's first `DT_NEEDED` (patchelf) and bundles it in `lib/`, so malloc
and new/delete go to jemalloc instead of oneTBB's `libtbbmalloc_proxy`. Why: Cycles' parallel loading
of packed images livelocked inside tbbmalloc on Thor (scene prep stalls of 1-330 s on image-heavy
scenes; 8 of 16 junkshop runs). With jemalloc: 0 of 24 runs stalled, render speed unchanged, peak RSS
about 10% lower. Re-run the script after every rebuild (ninja relinks the binary).

## Packaging step (r2): recipe/40-package.sh + recipe/sanitize_tree.py
A build tree embeds the builder's home directory all over (RUNPATHs, debug info, compiled OSL shaders,
Python sysconfig and bytecode caches, even inside the zstd-compressed Cycles kernels) and `tar` records
the builder's user name. The packager drops `__pycache__`, strips ELF debug info, rewrites the home
prefix to a same-length placeholder (inside compressed files too), sets blender's RUNPATH to
`$ORIGIN/lib`, writes root-owned tar entries, and refuses to pack if the home path or user name is
still found anywhere. The r2 tarball was produced with it.

## Dropped vs the 4.5.13 recipe (obsolete upstream)
- **sqlite autoreconf patch** - sqlite 3.51.x switched to the TCL `autosetup` build system (no
  `configure.ac`), so the 4.5-era `autoreconf -fi` fix both fails and is unnecessary; the stock
  configure works on aarch64.
- **libglu autoreconf patch** - `libglu` was dropped as a bundled dependency in Blender 5.x.

## Configure-flag choices (recipe/20-blender.sh, not patches)
- `-DCYCLES_CUDA_BINARIES_ARCH=sm_110;compute_90` - native Thor cubin + sm_90+ PTX fallback.
- `-DWITH_CYCLES_DEVICE_OPTIX=OFF` - no OptiX runtime on Jetson.
- `-DWITH_VULKAN_BACKEND=ON` - Thor ships a working NVIDIA Vulkan 1.4 driver; EEVEE runs on it
  (verified headless). Additive to the OpenGL default.
- `-DWITH_HARFBUZZ=ON -DWITH_FRIBIDI=ON` - complex-script + bidirectional (RTL) text shaping.
- `-DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14` - Blender 5.2 requires GCC >= 14; Ubuntu
  24.04 defaults to GCC 13. The deps build fine with GCC 13 (ABI-compatible with 14).
