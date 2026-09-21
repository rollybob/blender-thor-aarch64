# What we changed vs upstream Blender v5.2.2, and why

The source delta is small (8 patches; see `PATCHES/`). Each fix corresponds to a concrete wall hit
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
