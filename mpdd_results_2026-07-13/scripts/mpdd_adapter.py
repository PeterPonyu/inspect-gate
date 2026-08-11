#!/usr/bin/env python3
"""MPDD score-schema adapter: box outputs -> canonical scores-JSONL.

Clone of ``visa_adapter.py`` with ONE structural difference: MPDD ships in
native MVTec layout and has NO external split file, so the ground-truth
test split is the ``mpdd_split_manifest.json`` that ``mpdd_prep.py`` froze
from the verified staged tree (per-category ``[[defect_type, stem], ...]``)
-- exactly the role ``1cls.csv`` plays for VisA, except we generated it.

Two source schemas from the MPDD box run (same as VisA):
  * Dinomaly (``dinomaly_mpdd_uni`` + Branch-A patch): per-category JSON
    dict ``{"<mpdd_root>/<cat>/test/<defect_type>/<stem>.png": score}`` --
    needs full adaptation (path parse + label join). Unlike VisA, the test
    subfolder is the REAL MPDD defect-type name (native layout), not a
    ``good``/``bad`` symlink bucket, so the path regex captures an
    arbitrary ``<defect_type>`` and label = good iff defect_type == "good".
  * PatchCore (anomalib on the native layout): per-category canonical
    JSONL already in the ``inspect_gate.io`` schema (records built from
    ``discover_category``, so ``defect_type`` is the real MPDD name) --
    validated + count-refused + merged only.

REFUSES loudly (nonzero exit) on any count mismatch, unknown/duplicate
(defect_type, stem) key, or category disagreement. End-to-end validation:
recomputes per-category image-AUROC from the adapted Dinomaly records and
compares against the box's own final ``log.txt`` table (proves label join
AND sign convention in one check). Everything -> ADAPTER-REPORT.json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, NoReturn

import numpy as np


def _portal_commons_root():
    import os
    from pathlib import Path
    for key in ("COMMONS_ROOT", "RELIABILITY_COMMONS"):
        v = os.environ.get(key)
        if v:
            p = Path(v).expanduser().resolve()
            if p.is_dir():
                return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for cand in (parent / "reliability-commons", parent.parent / "reliability-commons"):
            if cand.is_dir():
                return cand
    raise RuntimeError(
        "Set COMMONS_ROOT to the reliability-commons checkout (or place it as a sibling of this repo)."
    )

def _portal_repo_root():
    from pathlib import Path
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        if (p / ".git").exists() or (p / "pyproject.toml").exists() or (p / "README.md").exists():
            return p
    return here

IG_ROOT = _portal_repo_root()
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons on path
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import io as _io  # noqa: E402
from inspect_gate import reproduction as _repro  # noqa: E402

# Overridable so this runs against whatever local path the box tar is
# pulled to (the VisA precedent hard-coded orchestration_2026-07-12; MPDD's
# pull path is only known once the box run lands, so it is an env/CLI knob).
DEFAULT_PULL = os.environ.get(
    "MPDD_PULL",
    "${PORTFOLIO_ROOT}/orchestration_2026-07-13"
    "/mpdd_pull${AUTODL_TMP}/mpdd_brancha")
DEFAULT_MANIFEST = os.environ.get(
    "MPDD_MANIFEST", str(IG_ROOT / "mpdd_staging" / "mpdd_split_manifest.json"))
OUT = IG_ROOT / "mpdd_results_2026-07-13"
CANON = OUT / "canonical"
SEEDS = [0, 1, 2, 3, 4]
CATEGORIES = ["bracket_black", "bracket_brown", "bracket_white", "connector", "metal_plate", "tubes"]
AUROC_XCHECK_TOL = 1e-3  # box log rounds to 4 dp; rank-tie handling may differ slightly

# native layout: /<cat>/test/<defect_type>/<stem>.png (defect_type == "good"
# for the non-defective test images).
DINO_PATH_RE = re.compile(r"/(?P<cat>[^/]+)/test/(?P<dtype>[^/]+)/(?P<stem>[^/]+)\.png$")


def refuse(msg: str) -> NoReturn:
    print(f"REFUSE: {msg}", file=sys.stderr)
    sys.exit(1)


def load_official_test_split(manifest_path: Path) -> Dict[str, set]:
    """{category: {(defect_type, stem), ...}} from the mpdd_prep manifest."""
    manifest = json.loads(Path(manifest_path).read_text())
    if sorted(manifest["categories"]) != sorted(CATEGORIES):
        refuse(f"manifest categories {sorted(manifest['categories'])} != {sorted(CATEGORIES)}")
    split: Dict[str, set] = {}
    for cat in CATEGORIES:
        cell = set()
        for dtype, stem in manifest["per_category"][cat]["test_split"]:
            key = (dtype, stem)
            if key in cell:
                refuse(f"manifest duplicate test entry {cat}/{dtype}/{stem}")
            cell.add(key)
        split[cat] = cell
    return split


def parse_final_log_table(log_path: Path) -> Dict[str, float]:
    """Last-reported per-category I-AUROC from the box's own log.txt."""
    table: Dict[str, float] = {}
    pat = re.compile(r"^(?P<cat>[a-z0-9_]+): I-Auroc:(?P<auroc>[0-9.]+),")
    with open(log_path) as f:
        for line in f:
            m = pat.match(line.strip())
            if m and m.group("cat") in CATEGORIES:
                table[m.group("cat")] = float(m.group("auroc"))  # later lines overwrite
    return table


def adapt_dinomaly(pull: Path, official: Dict[str, set]) -> Dict[int, Any]:
    report: Dict[int, Any] = {}
    for seed in SEEDS:
        run_dir = pull / "dinomaly" / f"seed_{seed}" / "run"
        records = []
        for cat in CATEGORIES:
            scores = json.loads((run_dir / f"scores_{cat}.json").read_text())
            seen = set()
            for raw_path, score in scores.items():
                m = DINO_PATH_RE.search(raw_path)
                if not m:
                    refuse(f"dinomaly seed{seed} {cat}: unparseable path {raw_path!r}")
                if m.group("cat") != cat:
                    refuse(f"dinomaly seed{seed}: path category {m.group('cat')} inside scores_{cat}.json")
                dtype, stem = m.group("dtype"), m.group("stem")
                if (dtype, stem) in seen:
                    refuse(f"dinomaly seed{seed} {cat}: duplicate {dtype}/{stem}")
                seen.add((dtype, stem))
                records.append({
                    "image_id": f"{cat}_test_{dtype}_{stem}",
                    "category": cat,
                    "split": "test",
                    "score": float(score),
                    "label": "good" if dtype == "good" else "defect",
                    "defect_type": dtype,
                })
            if seen != official[cat]:
                missing = official[cat] - seen
                extra = seen - official[cat]
                refuse(f"dinomaly seed{seed} {cat}: split mismatch vs manifest "
                       f"(missing={sorted(missing)[:5]} extra={sorted(extra)[:5]})")
        out_path = CANON / f"scores_dinomaly_seed{seed}.jsonl"
        _io.write_jsonl(out_path, records)
        _io.load_scores(str(out_path))  # full schema validation round-trip

        # end-to-end AUROC cross-check vs the box's own final log table
        log_table = parse_final_log_table(run_dir / "log.txt")
        xcheck = {}
        for cat in CATEGORIES:
            recs = [r for r in records if r["category"] == cat]
            auroc = _repro.image_auroc(
                np.array([r["score"] for r in recs], dtype=float),
                np.array([r["label"] == "defect" for r in recs], dtype=bool),
            )
            logged = log_table.get(cat)
            if logged is None:
                refuse(f"dinomaly seed{seed} {cat}: no I-Auroc line in box log.txt")
            diff = abs(auroc - logged)
            xcheck[cat] = {"recomputed": round(auroc, 6), "box_log": logged,
                           "abs_diff": round(diff, 6)}
            if diff > AUROC_XCHECK_TOL:
                refuse(f"dinomaly seed{seed} {cat}: recomputed AUROC {auroc:.5f} vs "
                       f"box log {logged:.5f} (diff {diff:.5f} > {AUROC_XCHECK_TOL})")
        report[seed] = {"n_records": len(records), "auroc_xcheck": xcheck,
                        "max_abs_diff": max(v["abs_diff"] for v in xcheck.values())}
        print(f"dinomaly seed{seed}: {len(records)} records, "
              f"AUROC xcheck max|diff|={report[seed]['max_abs_diff']:.6f} -> {out_path.name}")
    return report


def adapt_patchcore(pull: Path, official: Dict[str, set]) -> Dict[int, Any]:
    report: Dict[int, Any] = {}
    for seed in SEEDS:
        seed_dir = pull / "patchcore" / f"seed_{seed}"
        records = []
        for cat in CATEGORIES:
            recs = _io.load_scores(str(seed_dir / f"scores_{cat}.jsonl"))
            seen = set()
            for r in recs:
                if r["category"] != cat:
                    refuse(f"patchcore seed{seed}: category {r['category']} inside scores_{cat}.jsonl")
                if r["split"] != "test":
                    refuse(f"patchcore seed{seed} {cat}: unexpected split {r['split']}")
                # native layout: defect_type == "good" iff label good.
                if (r["defect_type"] == "good") != (r["label"] == "good"):
                    refuse(f"patchcore seed{seed} {cat}: defect_type/label disagree for {r['image_id']}")
            # rebuild the (defect_type, stem) set from image_id suffix vs manifest
            got = set()
            for r in recs:
                # image_id == f"{cat}_test_{defect_type}_{stem}"; recover stem as
                # the trailing token, defect_type from the record itself.
                stem = r["image_id"].split(f"{cat}_test_{r['defect_type']}_", 1)[-1]
                got.add((r["defect_type"], stem))
            if got != official[cat]:
                missing = official[cat] - got
                extra = got - official[cat]
                refuse(f"patchcore seed{seed} {cat}: split mismatch vs manifest "
                       f"(missing={sorted(missing)[:5]} extra={sorted(extra)[:5]})")
            records.extend(recs)
        ids = [r["image_id"] for r in records]
        if len(ids) != len(set(ids)):
            refuse(f"patchcore seed{seed}: duplicate image_ids in merged table")
        out_path = CANON / f"scores_patchcore_seed{seed}.jsonl"
        _io.write_jsonl(out_path, records)
        _io.load_scores(str(out_path))
        per_cat_auroc = {}
        for cat in CATEGORIES:
            recs = [r for r in records if r["category"] == cat]
            per_cat_auroc[cat] = round(_repro.image_auroc(
                np.array([r["score"] for r in recs], dtype=float),
                np.array([r["label"] == "defect" for r in recs], dtype=bool)), 6)
        report[seed] = {"n_records": len(records),
                        "per_category_auroc_descriptive": per_cat_auroc}
        print(f"patchcore seed{seed}: {len(records)} records (split vs manifest OK) -> {out_path.name}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pull", type=Path, default=Path(DEFAULT_PULL),
                    help="local path the box MPDD tar was pulled to")
    ap.add_argument("--manifest", type=Path, default=Path(DEFAULT_MANIFEST),
                    help="mpdd_split_manifest.json from mpdd_prep.py")
    args = ap.parse_args()

    CANON.mkdir(parents=True, exist_ok=True)
    official = load_official_test_split(args.manifest)
    n_test = {cat: len(v) for cat, v in official.items()}
    print(f"manifest test split: {sum(n_test.values())} images, {len(n_test)} categories")
    dino = adapt_dinomaly(args.pull, official)
    pc = adapt_patchcore(args.pull, official)
    report = {
        "manifest": str(args.manifest),
        "pull": str(args.pull),
        "official_test_counts": n_test,
        "auroc_xcheck_tolerance": AUROC_XCHECK_TOL,
        "dinomaly": dino,
        "patchcore": pc,
    }
    (OUT / "ADAPTER-REPORT.json").write_text(json.dumps(_io.to_jsonable(report), indent=2))
    print(f"wrote {OUT / 'ADAPTER-REPORT.json'}")
    print("ADAPTER_OK")


if __name__ == "__main__":
    main()
