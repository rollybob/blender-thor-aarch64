#!/usr/bin/env bash
# Un-stub the bundled asset .blend files (essentials brushes + geometry-node assets like
# smooth_by_angle / procedural_hair). They are git-LFS-tracked; a blob:none / partial clone leaves
# ~130-byte LFS POINTER stubs, which Blender reports as "Unrecognized file format" and the brushes
# / geometry-node asset libraries are missing from the UI. Fetch the real objects, then reinstall.
set -euo pipefail

: "${BLENDER_SRC:?set BLENDER_SRC to your patched blender v4.5.13 checkout}"
BLENDER_BUILD="${BLENDER_BUILD:-$HOME/blender-build/blender_bin}"

cd "$BLENDER_SRC"
# LFS endpoint must be projects.blender.org (the GitHub mirror 404s on Blender's LFS objects).
git config lfs.url >/dev/null 2>&1 || git config lfs.url https://projects.blender.org/blender/blender.git/info/lfs
git lfs pull --include="assets/**"

# Re-run install so cmake copies the now-real assets into datafiles/assets.
ninja -C "$BLENDER_BUILD" install

echo "[30-assets] done. Verify none are stubs:"
find "$BLENDER_BUILD"/bin/*/datafiles/assets -name '*.blend' -printf '%s\n' 2>/dev/null \
  | awk '$1<1000{stub++} $1>=1000{real++} END{print "  real="real" stub="(stub+0)" (want stub=0)"}'
