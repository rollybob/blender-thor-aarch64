#!/usr/bin/env python3
"""Helpers for 40-package.sh.

  sanitize_tree.py rewrite <tree> <home_prefix/>   strip ELF debug info; rewrite home_prefix to a same-length
                                                   placeholder in every file, including inside zstd files
  sanitize_tree.py scan <tree> <pattern> [...]     exit 1 if any file (decompressed if zstd) contains a pattern
"""
import os
import subprocess
import sys
import tempfile

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
ELF_MAGIC = b"\x7fELF"


def files(tree):
    for root, _, names in os.walk(tree):
        for name in names:
            path = os.path.join(root, name)
            if os.path.isfile(path) and not os.path.islink(path):
                yield path


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def unzstd(data):
    return subprocess.run(["zstd", "-q", "-dc"], input=data, capture_output=True, check=True).stdout


def rewrite(tree, home):
    home = home.encode()
    # Same length as the home prefix, so offsets inside binaries do not move: "/build" + "_" padding + "/".
    repl = (b"/build" + b"_" * max(0, len(home) - 7) + b"/")[: len(home)]
    assert len(repl) == len(home), (home, repl)
    stripped = changed = 0
    for path in files(tree):
        if read(path)[:4] == ELF_MAGIC:
            if subprocess.run(["strip", "--strip-debug", path], capture_output=True).returncode == 0:
                stripped += 1
        data = read(path)
        if data[:4] == ZSTD_MAGIC:
            # e.g. the Cycles kernels (*.cubin.zst): the path hides inside the compression.
            raw = unzstd(data)
            if home not in raw:
                continue
            # --stream-size records the decompressed size in the frame header: Cycles' kernel loader
            # (path_read_compressed_binary) needs ZSTD_getFrameContentSize, and a piped zstd omits it.
            raw = raw.replace(home, repl)
            new = subprocess.run(["zstd", "-q", "-19", f"--stream-size={len(raw)}", "-c"], input=raw,
                                 capture_output=True, check=True).stdout
            with tempfile.NamedTemporaryFile(suffix=".zst") as tmp:  # zstd --list cannot read stdin
                tmp.write(new)
                tmp.flush()
                info = subprocess.run(["zstd", "-lv", tmp.name], capture_output=True, text=True).stdout
            if f"({len(raw)} B)" not in info:
                sys.exit(f"[sanitize] recompressed {path} lacks the content-size field")
        elif home in data:
            new = data.replace(home, repl)
        else:
            continue
        mode = os.stat(path).st_mode
        with open(path, "wb") as fh:
            fh.write(new)
        os.chmod(path, mode)
        changed += 1
    print(f"[sanitize] stripped debug info from {stripped} ELF files; rewrote {changed} files "
          f"({home.decode()} -> {repl.decode()})")


def scan(tree, patterns):
    patterns = [p.encode() for p in patterns if p]
    bad = []
    for path in files(tree):
        data = read(path)
        if data[:4] == ZSTD_MAGIC:
            data = unzstd(data)
        if any(p in data for p in patterns):
            bad.append(path)
    if bad:
        print(f"[sanitize] REFUSING: {len(bad)} files still contain {[p.decode() for p in patterns]}:")
        print("\n".join(bad[:20]))
        sys.exit(1)
    print(f"[sanitize] scan clean: no {[p.decode() for p in patterns]} in any file (zstd contents included)")


if __name__ == "__main__":
    if sys.argv[1] == "rewrite":
        rewrite(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "scan":
        scan(sys.argv[2], sys.argv[3:])
    else:
        sys.exit(__doc__)
