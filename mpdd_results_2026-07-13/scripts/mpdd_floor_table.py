#!/usr/bin/env python3
"""MPDD certifiability-floor PRECOMPUTE (zero GPU) -- predicts, before any
box run, how many MPDD categories the gate can G1/G2-certify under the
frozen primary protocol (alpha_miss=0.10, alpha_fr=0.05, good-cal=test).

The certifiability floor is a deterministic function of per-category test
COUNTS only (design §2.3: alpha_min = 1/(n_cal+1)), NOT of score values --
so this does the strongest possible free prediction: it runs the ACTUAL
production code path (``splits.stratified_cal_eval_split`` at repeat 0, then
``gate.calibrate_gate``) on synthetic records that carry MPDD's real
per-category (n_test_good, n_test_defect) counts, and reads the real
``alpha_min_g1``/``alpha_min_g2``/``g1_certified``/``g2_certified`` fields
straight off the calibrated strata. Because floors are count-only, this
equals what the box will compute bit-for-bit -- it is a genuine prediction,
not a re-derivation of the arithmetic by hand.

The headline number is the predicted **G2-certifiable count**, which lands
the paper's "refusal tracks the data" trend on a third point:
MVTec (4/15, stingy good pools) -> MPDD (?) -> VisA (12/12, generous pools).

Counts come from either ``--manifest`` (mpdd_prep.py's split manifest, the
real staged data) or ``--counts`` (a small JSON, for the unit tests and for
a documented preliminary against literature counts).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

IG_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons/tools/inspect-gate")
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons on path
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import gate as _gate  # noqa: E402
from inspect_gate import io as _io  # noqa: E402
from inspect_gate import splits as _splits  # noqa: E402

ALPHA_MISS = 0.10
ALPHA_FR = 0.05


def counts_from_manifest(manifest_path: Path) -> Dict[str, Dict[str, int]]:
    m = json.loads(Path(manifest_path).read_text())
    return {
        cat: {"n_test_good": c["n_test_good"], "n_test_defect": c["n_test_defect"]}
        for cat, c in m["per_category"].items()
    }


def _synth_records(counts: Dict[str, Dict[str, int]]):
    """One synthetic test record per image, correct per-category counts.
    Score VALUES are irrelevant to the floor (alpha_min/certified depend on
    n_cal only); good/defect score ranges are kept disjoint purely so the
    records are well-formed."""
    recs = []
    for cat, c in counts.items():
        for i in range(int(c["n_test_good"])):
            recs.append({"image_id": f"{cat}_test_good_{i:05d}", "category": cat,
                         "split": "test", "score": float(i), "label": "good",
                         "defect_type": "good"})
        for i in range(int(c["n_test_defect"])):
            recs.append({"image_id": f"{cat}_test_defect_{i:05d}", "category": cat,
                         "split": "test", "score": float(1_000_000 + i), "label": "defect",
                         "defect_type": "defect"})
    return recs


def predict_floors(
    counts: Dict[str, Dict[str, int]], alpha_miss: float = ALPHA_MISS, alpha_fr: float = ALPHA_FR
) -> Dict[str, Any]:
    """Run the real repeat-0 split + calibrate_gate; return per-category
    floor fields plus the G1/G2 certifiable counts."""
    recs = _synth_records(counts)
    # repeat 0 is exactly the repeat run_{visa,mpdd}_analysis records floors
    # from (floors are seed/repeat-invariant in COUNT, cross-checked on VisA).
    cal, _ev = _splits.stratified_cal_eval_split(recs, repeat_seed=0)
    g = _gate.calibrate_gate(
        cal, alpha_miss=alpha_miss, alpha_fr=alpha_fr, mondrian="category",
        backbone="floor-precompute", seed=0,
    )
    per_category: Dict[str, Any] = {}
    for cat in counts:
        s = g["strata"][cat]
        per_category[cat] = {
            "n_test_good": int(counts[cat]["n_test_good"]),
            "n_test_defect": int(counts[cat]["n_test_defect"]),
            "n_cal_good": s["n_cal_good"],
            "n_cal_defect": s["n_cal_defect"],
            "alpha_min_g1": s["alpha_min_g1"],
            "alpha_min_g2": s["alpha_min_g2"],
            "g1_certified": s["g1_certified"],
            "g2_certified": s["g2_certified"],
        }
    n_g1 = sum(1 for v in per_category.values() if v["g1_certified"])
    n_g2 = sum(1 for v in per_category.values() if v["g2_certified"])
    return {
        "alpha_miss": alpha_miss,
        "alpha_fr": alpha_fr,
        "protocol": "primary (good-cal=test), Mondrian per-category, repeat-0 split",
        "n_categories": len(per_category),
        "n_g1_certifiable": n_g1,
        "n_g2_certifiable": n_g2,
        "per_category": per_category,
    }


def to_markdown(result: Dict[str, Any]) -> str:
    lines = [
        f"# MPDD certifiability-floor PREDICTION (pre-box, zero GPU)",
        "",
        f"Protocol: {result['protocol']}; alpha_miss={result['alpha_miss']}, "
        f"alpha_fr={result['alpha_fr']}.",
        "",
        f"**Predicted G2-certifiable: {result['n_g2_certifiable']}/{result['n_categories']}** "
        f"(G1-certifiable: {result['n_g1_certifiable']}/{result['n_categories']}).",
        "",
        "| category | n_test_good | n_test_defect | n_cal_good | n_cal_defect | "
        "alpha_min_g1 | alpha_min_g2 | G1 cert | G2 cert |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for cat, v in result["per_category"].items():
        lines.append(
            f"| {cat} | {v['n_test_good']} | {v['n_test_defect']} | {v['n_cal_good']} | "
            f"{v['n_cal_defect']} | {v['alpha_min_g1']:.4f} | {v['alpha_min_g2']:.4f} | "
            f"{'Y' if v['g1_certified'] else 'n'} | {'Y' if v['g2_certified'] else 'n'} |"
        )
    lines += [
        "",
        "Certifiable ⇔ alpha_min ≤ target (G1: n_cal_defect ≥ 9 at 0.10; "
        "G2: n_cal_good ≥ 19 at 0.05). Floors are count-only, so these equal "
        "the box's repeat-0 floors bit-for-bit.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--manifest", type=Path, help="mpdd_prep.py split manifest JSON")
    src.add_argument("--counts", type=Path, help="{cat: {n_test_good, n_test_defect}} JSON")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.manifest:
        counts = counts_from_manifest(args.manifest)
    else:
        counts = json.loads(args.counts.read_text())

    result = predict_floors(counts)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(_io.to_jsonable(result), indent=2))
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(to_markdown(result))
    print(to_markdown(result))
    print(f"PREDICTED_G2_CERTIFIABLE={result['n_g2_certifiable']}/{result['n_categories']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
