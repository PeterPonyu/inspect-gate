#!/usr/bin/env python3
"""Phase 0 (design §7): untar the staged MVTec AD tarball, freeze
per-category counts (T1/F6 deliverable), checksum the tarball, and run
the binding reproduction gate (SOTA-REPRODUCTION-PLAN-2026-07-10.md §3)
against a scored backbone's output before any gate-calibration work.

Untar, configurable source (never hardcoded, per the task brief's
no-hardcoding rule)
--------------------------------------------------------------------------
Default source path matches the task brief's stated staging location:
``/root/autodl-pub/mvtec_anomaly_detection.tar.xz`` (override via
``--autodl-pub-path`` or ``AUTODL_PUB_MVTEC_PATH``); default extraction
target ``/root/autodl-tmp/mvtec_anomaly_detection`` (override via
``--data-root`` or ``INSPECT_GATE_DATA_ROOT``) -- the data disk, never
the system disk, per this portfolio's standing HF_HOME/data-on-data-disk
rule.

No torch/anomalib import anywhere in this module -- staging + counting +
the AUROC reproduction check (``inspect_gate.reproduction``) are all
CPU/stdlib-only, so this script's ``--counts-only``/``--reproduction-only``
paths are fully testable with no GPU.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR))

from inspect_gate import io as _io  # noqa: E402
from inspect_gate import reproduction as _repro  # noqa: E402
from mvtec_layout import MVTEC_CATEGORIES, discover_mvtec  # noqa: E402

DEFAULT_AUTODL_PUB_PATH = os.environ.get(
    "AUTODL_PUB_MVTEC_PATH", "/root/autodl-pub/mvtec_anomaly_detection.tar.xz"
)
# /root/autodl-tmp/mvtec_ad is what the staged box actually uses (verified
# on-box 2026-07-10); this is THE named default across every script in this
# package that needs a data root (mirrored in next_boot_inspect_gate.sh's
# DATA_ROOT and ig_fullscore.sh's DATA_ROOT) -- still env-overridable.
DEFAULT_DATA_ROOT = os.environ.get("INSPECT_GATE_DATA_ROOT", "/root/autodl-tmp/mvtec_ad")


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stage_tarball(tarball_path: str, data_root: str) -> Dict[str, Any]:
    """Untar ``tarball_path`` into ``data_root`` (idempotent: skips
    extraction if ``data_root`` already has per-category subdirectories
    matching :data:`MVTEC_CATEGORIES`). Returns a staging record with the
    tarball's checksum (design addendum: "checksum recorded at Phase 0")."""
    tarball_path_p = Path(tarball_path)
    data_root_p = Path(data_root)
    if not tarball_path_p.exists():
        raise FileNotFoundError(f"stage_tarball: tarball not found: {tarball_path_p}")

    data_root_p.mkdir(parents=True, exist_ok=True)
    already_staged = any((data_root_p / cat).exists() for cat in MVTEC_CATEGORIES)
    if not already_staged:
        with tarfile.open(tarball_path_p, "r:*") as tf:
            # "data" filter (Python >=3.12): strips unsafe metadata from a
            # trusted local staging tarball without changing extraction
            # behavior; older Pythons lack the kwarg entirely.
            extract_kwargs = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
            tf.extractall(path=data_root_p, **extract_kwargs)  # nosec - trusted local staging tarball

    checksum = sha256_of_file(str(tarball_path_p))
    return {
        "tarball_path": str(tarball_path_p),
        "data_root": str(data_root_p),
        "already_staged": already_staged,
        "tarball_sha256": checksum,
    }


def freeze_category_counts(data_root: str, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """Enumerate every category's train/test/good/defect counts from the
    STAGED tarball (design §3.2: "exact per-category test-set compositions
    ... are a Phase-0 deliverable, enumerated from the local tarball and
    frozen into the prereg -- no per-category count appears in this
    design as fact")."""
    discovered = discover_mvtec(data_root, categories)
    counts: Dict[str, Any] = {}
    for cat, images in discovered.items():
        n_train_good = sum(1 for im in images if im.split == "train")
        test_images = [im for im in images if im.split == "test"]
        n_test_good = sum(1 for im in test_images if im.label == "good")
        n_test_defect = sum(1 for im in test_images if im.label == "defect")
        defect_type_counts: Dict[str, int] = {}
        for im in test_images:
            if im.label == "defect":
                defect_type_counts[im.defect_type] = defect_type_counts.get(im.defect_type, 0) + 1
        counts[cat] = {
            "n_train_good": n_train_good,
            "n_test_good": n_test_good,
            "n_test_defect": n_test_defect,
            "n_defect_types": len(defect_type_counts),
            "defect_type_counts": defect_type_counts,
        }
    return counts


def run_reproduction_gate(scores_path: str, backbone: str, tolerance: float) -> Dict[str, Any]:
    """Load a scored backbone's canonical scores-JSONL and run the binding
    image-AUROC reproduction gate (SOTA-REPRODUCTION-PLAN §3)."""
    records = _io.load_scores(scores_path)
    return _repro.reproduction_gate(records, backbone=backbone, tolerance=tolerance)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Phase 0: stage MVTec AD, freeze counts, run the reproduction gate")
    p.add_argument("--autodl-pub-path", default=DEFAULT_AUTODL_PUB_PATH)
    p.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    p.add_argument("--category", default=None, help="comma-separated categories (default: all 15)")
    p.add_argument("--counts-only", action="store_true", help="skip staging (assume already extracted) and just freeze counts")
    p.add_argument("--skip-staging", action="store_true", help="assume data_root is already populated; skip untar")
    p.add_argument("--patchcore-scores", default=None, help="scored PatchCore output for the reproduction gate")
    p.add_argument("--dinomaly-scores", default=None, help="scored Dinomaly output for the reproduction gate")
    p.add_argument("--auroc-tolerance", type=float, default=_repro.DEFAULT_AUROC_TOLERANCE)
    p.add_argument(
        "--skip-reproduction-gate", action="store_true",
        help="declare upfront that this invocation is staging/counting-only "
             "and does not intend to run the reproduction gate at all (e.g. "
             "Phase-0 staging before any backbone has been scored yet); "
             "without this flag, an invocation that ends up grading ZERO "
             "backbones (no --patchcore-scores/--dinomaly-scores given, or "
             "given but ungradable, e.g. an unset target) is treated as a "
             "vacuous, non-passing reproduction gate rather than silently "
             "reported as OK.",
    )
    p.add_argument("-o", "--out", required=True, help="output phase0.json")
    args = p.parse_args(argv)

    categories = args.category.split(",") if args.category else None

    result: Dict[str, Any] = {"data_root": args.data_root}

    if not args.counts_only and not args.skip_staging:
        result["staging"] = stage_tarball(args.autodl_pub_path, args.data_root)
    else:
        result["staging"] = {"skipped": True}

    result["category_counts"] = freeze_category_counts(args.data_root, categories)

    reproduction: Dict[str, Any] = {}
    if args.patchcore_scores:
        reproduction["patchcore"] = run_reproduction_gate(args.patchcore_scores, "patchcore", args.auroc_tolerance)
    if args.dinomaly_scores:
        reproduction["dinomaly"] = run_reproduction_gate(args.dinomaly_scores, "dinomaly", args.auroc_tolerance)
    result["reproduction"] = reproduction

    all_pass = [r["pass"] for r in reproduction.values() if r["pass"] is not None]
    if args.skip_reproduction_gate:
        result["reproduction_gate_pass"] = None
    elif not all_pass:
        # Vacuous-pass guard: an empty `reproduction` dict (no scores
        # supplied) or one where every supplied backbone came back
        # ungradable (e.g. Dinomaly's target unset) must NOT be reported
        # as a silent pass -- that hides a chain where scoring upstream
        # produced nothing to grade at all.
        result["reproduction_gate_pass"] = False
        result["reproduction_gate_reason"] = (
            "zero backbones graded (reproduction dict empty or all supplied "
            "backbones' pass came back None); pass --skip-reproduction-gate "
            "if this invocation genuinely does not intend to run the "
            "reproduction gate"
        )
    else:
        result["reproduction_gate_pass"] = all(all_pass)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(_io.to_jsonable(result), f, indent=2, ensure_ascii=False)

    n_cats = len(result["category_counts"])
    print(f"phase0: categories={n_cats} reproduction_gate_pass={result['reproduction_gate_pass']} -> {args.out}")
    if result["reproduction_gate_pass"] is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
