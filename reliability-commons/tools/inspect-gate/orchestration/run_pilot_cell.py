#!/usr/bin/env python3
"""Run the full calibrate -> route -> certify -> audit loop for ONE
(backbone, seed, category) pilot cell (design §7 Phase 1: "fit backbone
-> cache scores -> calibrate gate -> certify (V1 cells) -> run audit vs
null -- regenerate F1/F2/F3 from result JSONs end-to-end").

Pure ``inspect_gate`` (no torch/anomalib) -- consumes an already-scored
canonical scores-JSONL (from ``score_patchcore.py``/``score_dinomaly.py``)
for one backbone+seed, covering the requested category (and, for the
optional train-holdout arm, that category's train-good images too).

R repeated stratified calibration/evaluation splits (design §3.2/§3.3,
``--n-repeats``, default 20; the pilot chain passes a smaller number to
keep the loop cheap -- see ``next_boot_inspect_gate.sh``) each produce
one gate + one V1 coverage cell; all R gates+cells are written out, plus
the aggregated V1 table. The excess-AURC audit (design §2.2/§3.4-3.5) is
run once, on repeat 0's calibration/evaluation halves (matching the
gate's realized deferral rate on that same repeat) -- auditing every
repeat separately is future work the main-grid run can add without
changing this script's shape.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from inspect_gate import audit as _audit  # noqa: E402
from inspect_gate import certify as _certify  # noqa: E402
from inspect_gate import gate as _gate  # noqa: E402
from inspect_gate import io as _io  # noqa: E402
from inspect_gate import splits as _splits  # noqa: E402


def run_pilot_cell(
    scores: List[Dict[str, Any]],
    category: str,
    alpha_miss: float,
    alpha_fr: float,
    n_repeats: int,
    mondrian: str,
    good_cal_holdout_frac: Optional[float],
    backbone: Optional[str],
    n_perm: int,
    audit_alpha: float,
) -> Dict[str, Any]:
    cat_records = [r for r in scores if r["category"] == category]
    if not cat_records:
        raise ValueError(f"run_pilot_cell: no records for category={category!r}")
    test_records = [r for r in cat_records if r["split"] == "test"]
    train_records = [r for r in cat_records if r["split"] == "train"]

    good_cal_holdout_pool = None
    if good_cal_holdout_frac is not None and train_records:
        _, good_cal_holdout_pool = _splits.train_good_holdout_split(
            train_records, holdout_frac=good_cal_holdout_frac, seed=0
        )

    reps = _splits.repeated_stratified_splits(test_records, n_repeats=n_repeats)

    cells = []
    gates = []
    for i, (cal, ev) in enumerate(reps):
        gate = _gate.calibrate_gate(
            cal, alpha_miss=alpha_miss, alpha_fr=alpha_fr, mondrian=mondrian,
            good_cal_holdout=good_cal_holdout_pool,
            good_cal_holdout_cal=(cal if good_cal_holdout_pool is not None else None),
            backbone=backbone, seed=i,
        )
        routed = _gate.route_gate(gate, ev)
        cell = _certify.coverage_cell(ev, routed["decisions"])
        cells.append(cell)
        gates.append(gate)
        if i == 0:
            first_repeat_gate = gate
            first_repeat_cal, first_repeat_ev = cal, ev

    v1 = _certify.aggregate_v1_cells({category: cells}, alpha_miss=alpha_miss, alpha_fr=alpha_fr)

    routed0 = _gate.route_gate(first_repeat_gate, first_repeat_ev)
    target_deferral_rate = routed0["n_defer"] / routed0["n"] if routed0["n"] else 0.0
    # B3 (train-good quantile) only needs SOME held-out-from-calibration
    # train-good pool -- the full train split works regardless of whether
    # the (separate) --good-cal-holdout-frac G2 calibration-efficiency arm
    # was requested; don't couple B3's audit availability to that arm.
    audit_result = _audit.run_audit(
        first_repeat_cal, first_repeat_ev, (train_records or None),
        target_deferral_rate=target_deferral_rate, backbone=backbone,
        n_perm=n_perm, alpha=audit_alpha, seed=0,
    )

    return {
        "category": category,
        "backbone": backbone,
        "n_repeats": n_repeats,
        "v1": v1,
        "audit": audit_result,
        "gate_repeat0": first_repeat_gate,
    }


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Run one (backbone, seed, category) pilot cell")
    p.add_argument("--scores", required=True, help="canonical scores-JSONL for one backbone+seed")
    p.add_argument("--category", required=True)
    p.add_argument("--alpha-miss", type=float, default=0.10, dest="alpha_miss")
    p.add_argument("--alpha-fr", type=float, default=0.05, dest="alpha_fr")
    p.add_argument("--n-repeats", type=int, default=20, dest="n_repeats")
    p.add_argument("--mondrian", default="category")
    p.add_argument("--good-cal-holdout-frac", type=float, default=None, dest="good_cal_holdout_frac")
    p.add_argument("--backbone", default=None)
    p.add_argument("--n-perm", type=int, default=2000, dest="n_perm")
    p.add_argument("--audit-alpha", type=float, default=0.05, dest="audit_alpha")
    p.add_argument("-o", "--out", required=True)
    args = p.parse_args(argv)

    scores = _io.load_scores(args.scores)
    result = run_pilot_cell(
        scores, args.category, args.alpha_miss, args.alpha_fr, args.n_repeats,
        args.mondrian, args.good_cal_holdout_frac, args.backbone, args.n_perm, args.audit_alpha,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(_io.to_jsonable(result), f, indent=2, ensure_ascii=False)

    pass_tier1 = result["v1"]["per_category"][args.category]["tier1"]["pass_tier1"]
    print(f"run_pilot_cell: category={args.category} backbone={args.backbone} "
          f"pass_tier1={pass_tier1} holm_family_size={result['audit']['holm_family_size']} -> {args.out}")
    return 0 if pass_tier1 else 1


if __name__ == "__main__":
    sys.exit(main())
