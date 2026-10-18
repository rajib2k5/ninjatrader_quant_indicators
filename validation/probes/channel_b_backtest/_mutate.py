"""Make ONE targeted mutant: copy a source tree (no __pycache__) to DEST and replace OLD by NEW in
FILE exactly once. Prints sha256 of the original file (before and after copying) and of the mutant.

Usage: python -I -B _mutate.py SRC_DIR DEST_DIR REL_FILE OLD NEW
(SRC_DIR is copied to DEST_DIR/<basename(SRC_DIR)>; the original tree is only read.)
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys

src, dest, rel, old, new = sys.argv[1:6]
old = old.encode().decode("unicode_escape")
new = new.encode().decode("unicode_escape")


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


orig_file = os.path.join(src, rel)
h0 = sha(orig_file)
target_root = os.path.join(dest, os.path.basename(os.path.normpath(src)))
if os.path.exists(target_root):
    shutil.rmtree(target_root)
shutil.copytree(src, target_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
mf = os.path.join(target_root, rel)
text = open(mf, encoding="utf-8").read()
n = text.count(old)
if n != 1:
    print("MUTATION ERROR: %r occurs %d times in %s" % (old, n, mf))
    sys.exit(2)
open(mf, "w", encoding="utf-8", newline="").write(text.replace(old, new))
print("mutant: %s" % mf)
print("  - %s" % old.strip())
print("  + %s" % new.strip())
print("sha256 original %s before %s" % (rel, h0))
print("sha256 original %s after  %s" % (rel, sha(orig_file)))
print("sha256 mutant   %s        %s" % (rel, sha(mf)))
sys.exit(0 if sha(orig_file) == h0 else 3)
