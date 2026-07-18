#!/usr/bin/env python3
"""Verify a staged MPDD tree (native MVTec-AD layout) and freeze its split
manifest -- MPDD's analogue of ``visa_prep.py``, but a VERIFIER, not a
symlinker: MPDD already ships in native MVTec layout (per-category
``train/good/``, ``test/good/``, ``test/<defect_type>/``,
``ground_truth/<defect_type>/``), so ``mvtec_layout.discover_category``
consumes it directly and there is no JPEG-as-PNG symlink dance to do.

What it does (all loud-refuse on mismatch, nonzero exit -- same discipline
as ``visa_prep.py``):
  * discovers all 6 MPDD categories via ``discover_category``;
  * asserts each category has train-good, test-good, and >=1 defect
    subfolder with images (no empty split cell);
  * asserts the frozen official totals (default 888 train-good / 458 test,
    the published MPDD split -- overridable so the synthetic unit-test
    fixtures can assert their own small totals);
  * writes a split manifest JSON (per-category train-good / test-good /
    test-defect counts, the per-defect-type breakdown, AND the full
    ``[[defect_type, stem], ...]`` test roster) that ``mpdd_adapter.py``
    consumes as the ground-truth test split -- exactly the role
    ``1cls.csv`` plays for VisA, except we GENERATE it from the staged
    layout (MPDD has no external split file) and stamp it with the
    archive sha256 for provenance.

The manifest -- not this script, not any doc -- is the source of truth for
the certifiability-floor precompute and the adapter's count-refuse, once a
real staged tree has been verified.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Sequence

_LAYOUT_PATH = Path(__file__).resolve().parent / "mvtec_layout.py"
_spec = importlib.util.spec_from_file_location("mvtec_layout", _LAYOUT_PATH)
mvtec_layout = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mvtec_layout)

MPDD_CATEGORIES = mvtec_layout.MPDD_CATEGORIES

# Published MPDD split (Jezek et al., ICUMT 2021; COMPUTE-PLAN-2026-07-13.md
# §2): 888 train-good, 458 test. Frozen here as the default assertion; the
# real per-category breakdown is written into the manifest at verify time.
DEFAULT_EXPECT_TRAIN_GOOD = 888
DEFAULT_EXPECT_TEST = 458


def refuse(msg: str) -> NoReturn:
    print(f"REFUSE: {msg}", file=sys.stderr)
    sys.exit(1)


def build_manifest(
    mpdd_root: Path,
    categories: Sequence[str] = MPDD_CATEGORIES,
    archive_sha256: str | None = None,
) -> Dict[str, Any]:
    """Discover + structurally validate every category, returning the split
    manifest dict (does NOT enforce the 888/458 totals -- that is
    :func:`verify`'s job, so this function is reusable by the floor-table
    precompute and by tests with arbitrary fixtures)."""
    per_category: Dict[str, Any] = {}
    for cat in categories:
        images = mvtec_layout.discover_category(mpdd_root, cat)  # raises if dir missing
        train_good = [im for im in images if im.split == "train" and im.label == "good"]
        test_good = [im for im in images if im.split == "test" and im.label == "good"]
        test_defect = [im for im in images if im.split == "test" and im.label == "defect"]

        if not train_good:
            refuse(f"{cat}: no train/good images (empty split cell)")
        if not test_good:
            refuse(f"{cat}: no test/good images (empty split cell)")
        if not test_defect:
            refuse(f"{cat}: no test defect images (empty split cell)")

        defect_type_counts: Dict[str, int] = {}
        for im in test_defect:
            defect_type_counts[im.defect_type] = defect_type_counts.get(im.defect_type, 0) + 1

        # (defect_type, stem) roster -- the join key mpdd_adapter.py uses;
        # assert it is collision-free within this category's test split.
        test_split: List[List[str]] = []
        seen = set()
        for im in test_good + test_defect:
            key = (im.defect_type, im.path.stem)
            if key in seen:
                refuse(f"{cat}: duplicate (defect_type, stem) test key {key}")
            seen.add(key)
            test_split.append([im.defect_type, im.path.stem])

        per_category[cat] = {
            "n_train_good": len(train_good),
            "n_test_good": len(test_good),
            "n_test_defect": len(test_defect),
            "n_test_total": len(test_good) + len(test_defect),
            "defect_type_counts": defect_type_counts,
            "test_split": sorted(test_split),
        }

    return {
        "source": "MPDD (Metal Parts Defect Detection), native MVTec-AD layout",
        "mpdd_root": str(mpdd_root),
        "archive_sha256": archive_sha256,
        "categories": list(categories),
        "per_category": per_category,
        "totals": {
            "train_good": sum(c["n_train_good"] for c in per_category.values()),
            "test_good": sum(c["n_test_good"] for c in per_category.values()),
            "test_defect": sum(c["n_test_defect"] for c in per_category.values()),
            "test_total": sum(c["n_test_total"] for c in per_category.values()),
        },
    }


def verify(
    mpdd_root: Path,
    out_manifest: Path,
    expect_train_good: int = DEFAULT_EXPECT_TRAIN_GOOD,
    expect_test: int = DEFAULT_EXPECT_TEST,
    categories: Sequence[str] = MPDD_CATEGORIES,
    archive_sha256: str | None = None,
) -> Dict[str, Any]:
    if len(set(categories)) != len(categories):
        refuse(f"duplicate category in roster {list(categories)}")
    manifest = build_manifest(mpdd_root, categories, archive_sha256)
    n_cat = len(manifest["per_category"])
    if n_cat != len(categories):
        refuse(f"expected {len(categories)} categories, discovered {n_cat}")

    tg = manifest["totals"]["train_good"]
    tt = manifest["totals"]["test_total"]
    if tg != expect_train_good:
        refuse(f"train-good total {tg} != expected {expect_train_good}")
    if tt != expect_test:
        refuse(f"test total {tt} != expected {expect_test}")

    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, indent=2))
    print(f"mpdd_prep: {n_cat} categories, train-good={tg}, test={tt} "
          f"(both match expected {expect_train_good}/{expect_test})")
    for cat in categories:
        c = manifest["per_category"][cat]
        print(f"  {cat}: train/good={c['n_train_good']} test/good={c['n_test_good']} "
              f"test/defect={c['n_test_defect']} defect_types={sorted(c['defect_type_counts'])}")
    print(f"mpdd_prep: manifest -> {out_manifest}")
    print("MPDD_PREP_OK")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mpdd_root", type=Path, help="staged MPDD root (native MVTec layout)")
    ap.add_argument("out_manifest", type=Path, help="output split-manifest JSON path")
    ap.add_argument("--expect-train-good", type=int, default=DEFAULT_EXPECT_TRAIN_GOOD)
    ap.add_argument("--expect-test", type=int, default=DEFAULT_EXPECT_TEST)
    ap.add_argument("--archive-sha256", type=str, default=None,
                    help="sha256 of the source archive, recorded into the manifest")
    args = ap.parse_args(argv)
    verify(
        args.mpdd_root, args.out_manifest,
        expect_train_good=args.expect_train_good, expect_test=args.expect_test,
        archive_sha256=args.archive_sha256,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
