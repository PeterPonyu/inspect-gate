#!/usr/bin/env python3
"""Stage KSDD2 (Kolektor Surface-Defect Dataset 2) into the MVTec-AD layout
the inspect-gate pipeline consumes, and freeze its split manifest -- KSDD2's
analogue of ``mpdd_prep.py``, but a CONVERTER + verifier (like ``visa_prep``),
not a pure verifier: KSDD2 does NOT ship in native MVTec layout, so this
script BUILDS the ``{out_root}/kolektor_surface/{train,test}/...`` tree via
symlinks, then freezes + refuses on mismatch.

KSDD2 native layout (Boic et al., KSDD2, ViCoS Lab; confirmed against the
vicoslab/mixed-segdec-net-comind2021 loader -- worth re-confirming against the
actual staged archive at box Phase 0, the same hedge ``mvtec_layout.py`` makes
for MVTec)::

    {ksdd2_root}/train/{part}.png          # e.g. 10000.png
    {ksdd2_root}/train/{part}_GT.png       # paired ground-truth mask
    {ksdd2_root}/test/{part}.png
    {ksdd2_root}/test/{part}_GT.png

An image is DEFECTIVE iff its ``{part}_GT.png`` mask has any nonzero pixel
(all-black mask == non-defective). KSDD2 is a BINARY, single-category dataset:
this script maps it to the single MVTec category ``kolektor_surface`` with the
single defect_type ``bad`` (the pipeline's per-category machinery then treats
it as exactly 1 category).

MVTec target this builds (what ``mvtec_layout.discover_category`` consumes)::

    {out_root}/kolektor_surface/train/good/{part}.png   <- train non-defective
    {out_root}/kolektor_surface/test/good/{part}.png    <- test  non-defective
    {out_root}/kolektor_surface/test/bad/{part}.png     <- test  defective

Split policy (disclosed): the OFFICIAL KSDD2 train/test split is preserved
exactly, so the built test set == KSDD2's official test set (894 good + 110
defective = 1004) and train-good == KSDD2's official 2085 non-defective train
images. KSDD2's 246 DEFECTIVE-train images have no home in the unsupervised
MVTec layout (MVTec ``train/`` is good-only by construction, and folding them
into ``test/`` would corrupt the official test split), so they are EXCLUDED and
their count is recorded in the manifest as ``excluded_train_defect`` -- never
silently dropped.

All loud-refuse on mismatch (nonzero exit), same discipline as ``mpdd_prep.py``:
missing GT mask, unexpected split/label counts, or a duplicate (defect_type,
stem) test key all refuse. The frozen manifest (per-split/label counts, the
per-defect-type breakdown, the full ``[[defect_type, stem], ...]`` test roster,
stamped with the archive sha256) -- not this script, not any doc -- is the
source of truth a future ``ksdd2_adapter.py`` would join box scores against.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Sequence, Tuple

KSDD2_CATEGORY = "kolektor_surface"
KSDD2_DEFECT_TYPE = "bad"

# Official KSDD2 split (ViCoS Lab; https://www.vicos.si/resources/kolektorsdd2/):
# train 2085 negative / 246 positive; test 894 negative / 110 positive. Frozen
# here as the default assertion; overridable so the synthetic unit-test fixtures
# can assert their own small totals.
DEFAULT_EXPECT_TRAIN_GOOD = 2085
DEFAULT_EXPECT_TEST_GOOD = 894
DEFAULT_EXPECT_TEST_DEFECT = 110
DEFAULT_EXPECT_TRAIN_DEFECT_EXCLUDED = 246


def refuse(msg: str) -> NoReturn:
    print(f"REFUSE: {msg}", file=sys.stderr)
    sys.exit(1)


def is_defective(mask_path: Path) -> bool:
    """True iff the ground-truth mask has any nonzero pixel (all-black ->
    non-defective). Refuses loudly if the mask file is missing (a KSDD2 image
    without its paired ``_GT.png`` indicates a corrupt/partial extraction, not
    a valid input)."""
    if not mask_path.exists():
        refuse(f"missing ground-truth mask {mask_path} (corrupt/partial KSDD2 extraction?)")
    import numpy as np
    from PIL import Image
    with Image.open(mask_path) as im:
        arr = np.asarray(im)
    return bool(arr.max() > 0)


def discover_ksdd2(ksdd2_root: Path) -> Dict[str, Dict[str, List[Path]]]:
    """Scan native KSDD2 ``train/`` and ``test/`` flat dirs, returning
    ``{split: {"good": [image Path, ...], "defect": [image Path, ...]}}``.
    Images are ``*.png`` files NOT ending in ``_GT.png``; each is classified by
    its paired ``{stem}_GT.png`` mask. Refuses if a split dir is missing."""
    discovered: Dict[str, Dict[str, List[Path]]] = {}
    for split in ("train", "test"):
        split_dir = ksdd2_root / split
        if not split_dir.is_dir():
            refuse(f"KSDD2 split dir not found: {split_dir} (root={ksdd2_root})")
        good: List[Path] = []
        defect: List[Path] = []
        images = sorted(p for p in split_dir.glob("*.png") if not p.stem.endswith("_GT"))
        if not images:
            refuse(f"{split}: no images (*.png excluding *_GT.png) under {split_dir}")
        for img in images:
            mask = img.with_name(f"{img.stem}_GT.png")
            (defect if is_defective(mask) else good).append(img)
        discovered[split] = {"good": good, "defect": defect}
    return discovered


def _relink(src: Path, dst: Path) -> None:
    """Create/refresh a symlink ``dst -> src`` (idempotent across re-runs)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(src.resolve())


def build_mvtec_tree(
    discovered: Dict[str, Dict[str, List[Path]]],
    out_root: Path,
    category: str = KSDD2_CATEGORY,
    defect_type: str = KSDD2_DEFECT_TYPE,
) -> Dict[str, int]:
    """Symlink the discovered KSDD2 images into the MVTec target tree (see
    module docstring for the mapping). Returns the realized cell counts. The
    246 train-defective images are intentionally NOT linked (excluded, per the
    disclosed split policy) -- their count is returned as
    ``excluded_train_defect``."""
    cat_dir = out_root / category
    linked_train_good = linked_test_good = linked_test_defect = 0
    for img in discovered["train"]["good"]:
        _relink(img, cat_dir / "train" / "good" / img.name)
        linked_train_good += 1
    for img in discovered["test"]["good"]:
        _relink(img, cat_dir / "test" / "good" / img.name)
        linked_test_good += 1
    for img in discovered["test"]["defect"]:
        _relink(img, cat_dir / "test" / defect_type / img.name)
        linked_test_defect += 1
    return {
        "train_good": linked_train_good,
        "test_good": linked_test_good,
        "test_defect": linked_test_defect,
        "excluded_train_defect": len(discovered["train"]["defect"]),
    }


def build_manifest(
    discovered: Dict[str, Dict[str, List[Path]]],
    out_root: Path,
    category: str = KSDD2_CATEGORY,
    defect_type: str = KSDD2_DEFECT_TYPE,
    archive_sha256: str | None = None,
) -> Dict[str, Any]:
    """Build the split-manifest dict from the discovered layout (pure counts +
    roster; does NOT enforce the official totals -- that is :func:`verify`'s
    job, so this is reusable by tests with arbitrary fixtures). Mirrors
    ``mpdd_prep.build_manifest``'s shape so a future ``ksdd2_adapter.py`` can
    consume it exactly as ``mpdd_adapter`` consumes the MPDD manifest."""
    n_train_good = len(discovered["train"]["good"])
    n_test_good = len(discovered["test"]["good"])
    n_test_defect = len(discovered["test"]["defect"])
    n_excluded = len(discovered["train"]["defect"])

    # (defect_type, stem) test roster -- the join key a ksdd2_adapter would use;
    # assert it is collision-free within the test split.
    test_split: List[List[str]] = []
    seen: set[Tuple[str, str]] = set()
    for img in discovered["test"]["good"]:
        key = ("good", img.stem)
        if key in seen:
            refuse(f"duplicate (defect_type, stem) test key {key}")
        seen.add(key)
        test_split.append(["good", img.stem])
    for img in discovered["test"]["defect"]:
        key = (defect_type, img.stem)
        if key in seen:
            refuse(f"duplicate (defect_type, stem) test key {key}")
        seen.add(key)
        test_split.append([defect_type, img.stem])

    per_category = {
        category: {
            "n_train_good": n_train_good,
            "n_test_good": n_test_good,
            "n_test_defect": n_test_defect,
            "n_test_total": n_test_good + n_test_defect,
            "defect_type_counts": {defect_type: n_test_defect} if n_test_defect else {},
            "test_split": sorted(test_split),
        }
    }
    return {
        "source": "KSDD2 (Kolektor Surface-Defect Dataset 2), converted to MVTec-AD layout",
        "out_root": str(out_root),
        "archive_sha256": archive_sha256,
        "categories": [category],
        "defect_type": defect_type,
        "excluded_train_defect": n_excluded,
        "split_policy": (
            "official KSDD2 train/test split preserved; 246 train-defective "
            "images excluded (no home in unsupervised MVTec train), count "
            "recorded as excluded_train_defect."
        ),
        "per_category": per_category,
        "totals": {
            "train_good": n_train_good,
            "test_good": n_test_good,
            "test_defect": n_test_defect,
            "test_total": n_test_good + n_test_defect,
            "excluded_train_defect": n_excluded,
        },
    }


def verify(
    ksdd2_root: Path,
    out_root: Path,
    out_manifest: Path,
    expect_train_good: int = DEFAULT_EXPECT_TRAIN_GOOD,
    expect_test_good: int = DEFAULT_EXPECT_TEST_GOOD,
    expect_test_defect: int = DEFAULT_EXPECT_TEST_DEFECT,
    expect_train_defect_excluded: int = DEFAULT_EXPECT_TRAIN_DEFECT_EXCLUDED,
    category: str = KSDD2_CATEGORY,
    defect_type: str = KSDD2_DEFECT_TYPE,
    archive_sha256: str | None = None,
    build_tree: bool = True,
) -> Dict[str, Any]:
    """Discover native KSDD2, (optionally) build the MVTec tree, assert the
    frozen official counts, write the split manifest, and print the
    ``KSDD2_PREP_OK`` sentinel. Refuses (nonzero exit) on any mismatch."""
    discovered = discover_ksdd2(ksdd2_root)

    if not discovered["train"]["good"]:
        refuse(f"{category}: no train/good images (empty split cell)")
    if not discovered["test"]["good"]:
        refuse(f"{category}: no test/good images (empty split cell)")
    if not discovered["test"]["defect"]:
        refuse(f"{category}: no test defect images (empty split cell)")

    if build_tree:
        linked = build_mvtec_tree(discovered, out_root, category, defect_type)
    else:
        linked = {
            "train_good": len(discovered["train"]["good"]),
            "test_good": len(discovered["test"]["good"]),
            "test_defect": len(discovered["test"]["defect"]),
            "excluded_train_defect": len(discovered["train"]["defect"]),
        }

    tg, teg, ted = linked["train_good"], linked["test_good"], linked["test_defect"]
    exc = linked["excluded_train_defect"]
    if tg != expect_train_good:
        refuse(f"train-good total {tg} != expected {expect_train_good}")
    if teg != expect_test_good:
        refuse(f"test-good total {teg} != expected {expect_test_good}")
    if ted != expect_test_defect:
        refuse(f"test-defect total {ted} != expected {expect_test_defect}")
    if exc != expect_train_defect_excluded:
        refuse(f"excluded train-defect {exc} != expected {expect_train_defect_excluded}")

    manifest = build_manifest(discovered, out_root, category, defect_type, archive_sha256)
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, indent=2))

    print(f"ksdd2_prep: category={category} train/good={tg} test/good={teg} "
          f"test/{defect_type}={ted} (excluded train-defect={exc}) "
          f"-- all match expected {expect_train_good}/{expect_test_good}/"
          f"{expect_test_defect}/{expect_train_defect_excluded}")
    print(f"ksdd2_prep: MVTec tree -> {out_root / category} ({'built' if build_tree else 'not built'})")
    print(f"ksdd2_prep: manifest -> {out_manifest}")
    print("KSDD2_PREP_OK")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ksdd2_root", type=Path, help="native KSDD2 root (holds train/ and test/)")
    ap.add_argument("out_root", type=Path,
                    help="output MVTec-layout root (kolektor_surface/ built under here)")
    ap.add_argument("out_manifest", type=Path, help="output split-manifest JSON path")
    ap.add_argument("--expect-train-good", type=int, default=DEFAULT_EXPECT_TRAIN_GOOD)
    ap.add_argument("--expect-test-good", type=int, default=DEFAULT_EXPECT_TEST_GOOD)
    ap.add_argument("--expect-test-defect", type=int, default=DEFAULT_EXPECT_TEST_DEFECT)
    ap.add_argument("--expect-train-defect-excluded", type=int,
                    default=DEFAULT_EXPECT_TRAIN_DEFECT_EXCLUDED)
    ap.add_argument("--archive-sha256", type=str, default=None,
                    help="sha256 of the source archive, recorded into the manifest")
    ap.add_argument("--no-build-tree", action="store_true",
                    help="verify counts + freeze manifest only; do not (re)create symlinks")
    args = ap.parse_args(argv)
    verify(
        args.ksdd2_root, args.out_root, args.out_manifest,
        expect_train_good=args.expect_train_good,
        expect_test_good=args.expect_test_good,
        expect_test_defect=args.expect_test_defect,
        expect_train_defect_excluded=args.expect_train_defect_excluded,
        archive_sha256=args.archive_sha256,
        build_tree=not args.no_build_tree,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
