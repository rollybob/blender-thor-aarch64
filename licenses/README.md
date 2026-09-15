# Licensing of this build

## Blender itself
Blender is licensed **GPL** - GPLv2-or-later overall, with GPLv3-or-later parts (Blender's own
manifest states GPL-3.0-or-later, (c) Blender Foundation). Full text: `Blender-COPYING.txt`.

Because a redistributed **binary** must be accompanied by the **complete corresponding source**, the
source for any binary in this project is upstream Blender tag **v4.5.13** plus the patches in
`../PATCHES/`. Both are published together, satisfying the GPL source requirement.

## Bundled third-party dependencies
`bundled-thirdparty/` is Blender's own generated third-party license bundle (from `make license`),
copied verbatim from the built binary's `bin/license/` directory:
- `license.md` - human-readable roll-up of every bundled dependency and its license.
- `licenses.json` - machine-readable manifest (25 dependencies: OIDN, OSL, OpenVDB, TBB, OpenColorIO,
  USD, Embree/OpenImageIO/etc., fonts, ...).
- `spdx/` - the SPDX license texts (Apache-2.0, BSD-2/3-Clause, MPL, Bitstream-Vera, ...).
- `others/` - non-SPDX texts (LLVM-exception, Arev fonts, ICS, TOST).

These are the same dependency versions this recipe builds, so the bundle applies as-is.

## NVIDIA CUDA
We do **not** redistribute any NVIDIA CUDA libraries. The binary dlopens the system CUDA driver
(`libcuda.so.1`) provided by JetPack on the target. Users must have JetPack 7 / CUDA 13 (driver 580+)
installed. No CUDA redistribution obligation is taken on here.

## This repo's own files
Our recipe scripts, docs, and verify helpers (everything outside `PATCHES/`, which are Blender GPL
source patches, and `licenses/`) are offered under the terms in the top-level `LICENSE` (CC0).

## Pre-publish TODO
- Re-run `make license` on the final build so `license.md`/`licenses.json` exactly match the shipped
  binary if any dep version changes.
- Confirm the fonts and any GPL/LGPL deps are all represented before cutting a public binary Release.
