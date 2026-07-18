#!/usr/bin/env python3
"""Box-side Dinomaly scoring, one category (or all) -> canonical
scores-JSONL (``inspect_gate.io`` schema).

Dinomaly (Guo et al., CVPR 2025, github.com/guojiajeremy/Dinomaly,
Apache-2.0) is NOT vendored here per the task brief -- its reference
implementation is not a pip package and its exact inference CLI/API is
UNVERIFIED against a real checkout at build time (no GPU/repo access in
this environment). Two modes, in decreasing order of how much this
script trusts its own guess about that API:

``dump-ingest`` (default, robust, torch/Dinomaly-repo-FREE)
    Ingests a per-image score dump the Dinomaly repo's OWN evaluation
    script already produced (however Phase-0 ends up invoking it --
    most anomaly-detection reference repos' test/eval scripts write a
    CSV or JSON of ``{image_path: score}`` or a results pickle; this
    mode expects EITHER a 2-column CSV (``image_path,score``, header
    optional) OR a JSON list of ``{"image_path": ..., "score": ...}``
    objects). This mode has NO import of anything beyond the standard
    library + ``inspect_gate``/``mvtec_layout`` -- it is the reliable
    path and the one this package's tests actually exercise.

``direct`` (best-effort, UNVERIFIED, heavily flagged)
    Attempts to import the Dinomaly checkout directly (``--repo-path``,
    added to ``sys.path`` at call time) and run its model against MVTec.
    THE EXACT MODULE/CLASS NAMES BELOW ARE A GUESS based on the common
    shape of DINOv2-reconstruction anomaly-detection reference repos
    (a ``dinomaly`` package exposing a model class with a
    ``.score(image) -> float`` or ``.predict(...)`` method) and MUST be
    confirmed against the real checkout before this mode is trusted --
    it raises :class:`DinomalyDirectModeUnverified` immediately with an
    actionable message rather than silently guessing wrong. Fixing this
    function to match the real repo (once cloned on the box) is a Phase-0
    task, not a build-time one; ``dump-ingest`` mode exists precisely so
    Phase-0 is never blocked on that confirmation.

Score sign convention: dumps must already be HIGHER = more anomalous
(``io.py``'s convention); if the Dinomaly repo's own scores use the
opposite sign, negate them upstream before dumping (documented here, not
silently auto-detected -- a silently-guessed sign flip is exactly the
kind of bug this portfolio's conventions exist to prevent).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR))

from inspect_gate import io as _io  # noqa: E402
from mvtec_layout import MVTEC_CATEGORIES, discover_mvtec  # noqa: E402


class DinomalyDirectModeUnverified(RuntimeError):
    """Raised by ``direct`` mode: the guessed Dinomaly API is unconfirmed."""


def _first_present(row: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[Any]:
    """First value among ``keys`` whose lookup in ``row`` is not ``None``
    -- unlike an ``or``-chain (``row.get(k1) or row.get(k2) or ...``),
    this does NOT skip past a legitimately falsy-but-valid value (e.g. a
    score of ``0.0``, the least-anomalous possible score, or an empty-
    string path) just because it is falsy."""
    for key in keys:
        val = row.get(key)
        if val is not None:
            return val
    return None


def load_score_dump(path: str) -> Dict[str, float]:
    """Parse a Dinomaly-produced score dump (CSV or JSON, see module
    docstring) into ``{image_path_or_stem: score}``. Matching against the
    on-disk MVTec layout tries the full path first, falling back to the
    basename stem (dumps commonly relativize or absolutize paths
    differently than this package's own discovery)."""
    p = Path(path)
    scores: Dict[str, float] = {}
    if p.suffix.lower() == ".json":
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        # A plain {image_path: score} mapping is what the Branch-A patcher's
        # dump_image_scores_branchA writes (2026-07-10); accept it directly.
        if isinstance(data, dict) and data and all(
            isinstance(v, (int, float)) for v in data.values()
        ):
            for image_path, score in data.items():
                scores[str(image_path)] = float(score)
            return scores
        rows = data if isinstance(data, list) else data.get("results", data.get("scores", []))
        for row in rows:
            image_path = _first_present(row, ("image_path", "path", "file"))
            score = _first_present(row, ("score", "pred_score", "anomaly_score"))
            if image_path is not None and score is not None:
                scores[str(image_path)] = float(score)
    else:
        with open(p, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                image_path, raw_score = row[0], row[1]
                try:
                    score = float(raw_score)
                except ValueError:
                    continue  # header row or malformed line, skipped not fatal
                scores[image_path] = score
    return scores


def dump_ingest_category(
    data_root: str, category: str, dump_scores: Dict[str, float]
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Match ``dump_scores`` against the on-disk layout for ``category``,
    returning ``(records, n_scored, n_failed)`` -- images with no matching
    dump entry (by full path or basename stem) are excluded-and-counted."""
    disk_images = discover_mvtec(data_root, [category])[category]
    by_path = {str(im.path): im for im in disk_images}
    by_stem = {im.path.stem: im for im in disk_images}

    records: List[Dict[str, Any]] = []
    n_scored = 0
    matched_image_ids = set()
    for raw_path, score in dump_scores.items():
        im = by_path.get(raw_path) or by_stem.get(Path(raw_path).stem)
        if im is None:
            continue
        matched_image_ids.add(im.image_id)
        records.append({
            "image_id": im.image_id, "category": im.category, "split": im.split,
            "score": float(score), "label": im.label, "defect_type": im.defect_type,
        })
        n_scored += 1

    n_failed = len(disk_images) - len(matched_image_ids)
    return records, n_scored, max(n_failed, 0)


def run_direct_category(repo_path: str, checkpoint: str, data_root: str, category: str, device: str) -> List[Dict[str, Any]]:
    """UNVERIFIED direct-invocation path -- see module docstring. Refuses
    immediately rather than guessing silently."""
    raise DinomalyDirectModeUnverified(
        "score_dinomaly.py --mode direct: the Dinomaly checkout's inference "
        "API has not been confirmed against a real clone (no GPU/repo access "
        "at build time). Before using --mode direct: (1) clone "
        f"github.com/guojiajeremy/Dinomaly to {repo_path!r}, (2) inspect its "
        "test/eval entry point (likely test.py or a script under tools/), "
        "(3) either (a) run that script yourself to produce a score dump "
        "and use --mode dump-ingest instead (the supported, tested path), "
        "or (b) update run_direct_category() here to match the real API "
        "and remove this refusal -- do not skip this confirmation step "
        "(portfolio rule: no guessed API is trusted silently)."
    )


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Score MVTec AD categories with Dinomaly")
    p.add_argument("--mode", default="dump-ingest", choices=["dump-ingest", "direct"])
    p.add_argument("--data-root", required=True, help="MVTec AD root (contains per-category dirs)")
    p.add_argument("--category", default=None, help="comma-separated categories (default: all 15)")
    p.add_argument("--scores-dump", default=None, help="dump-ingest mode: CSV or JSON score dump path")
    p.add_argument("--repo-path", default=None, help="direct mode: path to a Dinomaly checkout")
    p.add_argument("--checkpoint", default=None, help="direct mode: official Dinomaly checkpoint path")
    p.add_argument("--device", default="cuda")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    categories = args.category.split(",") if args.category else list(MVTEC_CATEGORIES)

    if args.mode == "direct":
        try:
            run_direct_category(args.repo_path, args.checkpoint, args.data_root, categories[0], args.device)
        except DinomalyDirectModeUnverified as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    if not args.scores_dump:
        print("error: --mode dump-ingest requires --scores-dump", file=sys.stderr)
        return 1
    dump_scores = load_score_dump(args.scores_dump)

    all_records: List[Dict[str, Any]] = []
    total_scored = 0
    total_failed = 0
    for cat in categories:
        try:
            records, n_scored, n_failed = dump_ingest_category(args.data_root, cat, dump_scores)
        except FileNotFoundError as e:
            print(f"score_dinomaly: category={cat} SKIPPED (staging error: {e})", file=sys.stderr)
            continue
        all_records.extend(records)
        total_scored += n_scored
        total_failed += n_failed
        print(f"score_dinomaly: category={cat} n_scored={n_scored} n_failed={n_failed}")

    if all_records:
        validated = _io.validate_scores(all_records)
        _io.write_jsonl(args.out, validated)
    print(f"score_dinomaly: DONE n_scored={total_scored} n_failed={total_failed} -> {args.out}")
    return 0 if total_scored > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
