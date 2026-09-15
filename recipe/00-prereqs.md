# 00 - Prerequisites & source setup (Jetson Thor / sm_90+ aarch64)

## Target platform (what this recipe is tested on)
- Jetson AGX Thor (Blackwell, compute capability **sm_110**)
- JetPack 7 / L4T R38.4.0, Ubuntu 24.04, aarch64
- CUDA 13.0 (host `nvcc`, `/usr/local/cuda-13`), NVIDIA driver 580.xx
- ~15 GB free disk for the deps build + Blender build; a lot of RAM helps (we have 128 GB)

Other sm_90+ CUDA-13 aarch64 hosts *should* work (the Cycles kernels ship native sm_110 **and**
compute_90 PTX), but only Thor is verified. **Jetson Orin (sm_87) is NOT supported** by this recipe.

## Host build tools (apt)
```
sudo apt install -y build-essential git git-lfs cmake ninja-build meson \
  autoconf automake libtool bison flex yasm nasm tcl python3-mako patchelf \
  pkg-config ccache autopoint gettext texinfo \
  libasound2-dev libpulse-dev libxt-dev libinput-dev libdrm-dev \
  gcc-arm-linux-gnueabihf libc6-dev-armhf-cross \
  libx11-dev libxi-dev libxxf86vm-dev libxfixes-dev libxrender-dev libgl1-mesa-dev
```
(The armhf cross bits are pulled in by some deps' configure checks; libdrm-dev is required by our
DRM/kmsgrab-enabled ffmpeg - see patch 0008.)

## Get the source at tag v4.5.13 and apply the patches
IMPORTANT: Blender's Git-LFS objects (startup.blend, OCIO configs, fonts, assets) are NOT served by
the GitHub mirror - you MUST point LFS at projects.blender.org or the binary segfaults at startup
(WM_init) on 131-byte LFS pointer files.

```
# GIT_LFS_SKIP_SMUDGE=1 stops the clone from smudging EVERY LFS blob on checkout (slow / can hang);
# we pull only what we need next. --single-branch keeps just the v4.5.13 history.
GIT_LFS_SKIP_SMUDGE=1 git clone --branch v4.5.13 --single-branch \
    https://github.com/blender/blender.git
cd blender
git config lfs.url https://projects.blender.org/blender/blender.git/info/lfs
git lfs pull --include="release/datafiles/**"      # required datafiles (fonts/OCIO/startup)

# apply this repo's patch set (choose one):
git am /path/to/blender-thor-aarch64/PATCHES/000*.patch          # preserves per-fix history
#   or:
git apply /path/to/blender-thor-aarch64/PATCHES/thor-aarch64-cuda13-combined.diff
```
(This exact clone+patch+build+verify flow was validated end-to-end from scratch on 2026-09-15 -
 ~55 min with a warm ccache; all four backends verified on the resulting binary.)

Then set BLENDER_SRC to this checkout and run the phase scripts in order:
```
export BLENDER_SRC=$PWD
../blender-thor-aarch64/recipe/10-deps.sh      # Phase 1: dependency stack (the long one)
../blender-thor-aarch64/recipe/20-blender.sh   # Phase 2: Blender itself
../blender-thor-aarch64/recipe/30-assets.sh    # un-stub bundled brush/geometry-node assets
```
Verify with the scripts in ../verify/ (see the top-level README).

## Env knobs honored by the scripts (sane defaults if unset)
- `BLENDER_SRC`   - the patched source checkout (required)
- `LIBDIR`        - harvested deps dir (default `$BLENDER_SRC/lib/linux_arm64`)
- `DEPS_BUILD`    - deps build dir (default `$HOME/blender-build/deps_arm64`)
- `BLENDER_BUILD` - Blender build/install dir (default `$HOME/blender-build/blender_bin`)
- `CUDA`          - CUDA toolkit root (default `/usr/local/cuda-13`)
- `CYCLES_ARCH`   - Cycles CUDA arch (default `sm_110;compute_90`)
