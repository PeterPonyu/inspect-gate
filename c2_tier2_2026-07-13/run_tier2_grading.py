"""V1 tier-2 grading under the frozen amendments A1 / A2 / A3.

These amendments (PREREG-DRAFT-2026-07-10 §9) redefine how the cached
per-cell tier-2 blocks (analysis_2026-07-10/gate_calibration/v1_*.json and
visa_results_2026-07-12/gate_calibration/v1_*.json) are GRADED.  We do not
recompute the gate; we re-grade the cached blocks per the amendments.

A1 -- power floor is PER-REPEAT, not pooled.  The cached block's
``underpowered_*`` flags use the pooled-over-R totals (n_eval_def_total,
n_eval_good_total), which A1/D8 call anticonservative (correlated
resamples of one fixed eval set manufacture power).  We OVERRIDE them:
  per_repeat_n_eval_def  = n_eval_def_total  / n_repeats
  per_repeat_n_eval_good = n_eval_good_total / n_repeats
  escaped powered  iff per_repeat_n_eval_def  >= 22
  false-rej powered iff per_repeat_n_eval_good >= 36
A1 further pins: report tier-2 ESCAPED using the per-repeat floor; report
tier-2 FALSE-REJECT as structurally underpowered on this dataset.  The
pooled interval is a labelled SECONDARY readout, never the verdict -- so
for powered escaped cells we recompute a per-repeat-faithful one-sided 95%
Clopper-Pearson UB at n = per_repeat_n_eval_def, k = round(rate * n), using
the codebase's own clopper_pearson_upper, and grade on THAT (the pooled UB
is retained alongside, labelled).

A2 -- keep the +3pp tolerance (escaped threshold 0.13, false-reject 0.08).
Tier-2 is a stringent check a correctly-calibrated gate is EXPECTED to fail
near the target; a fail is evidence about estimator variance, not about the
certificate (whose test is tier-1).  We attach that interpretation, we do
not widen the tolerance.

A3 -- false-reject axis is graded ONLY over G2-certified cells.  Non-
G2-certified cells are reported ``G2-REFUSED`` and EXCLUDED from every
pass/fail count (never counted as passes).  Combined with A1, the eligible
G2-certified cells are still per-repeat-underpowered for false-reject, so
the false-reject axis yields zero graded cells (structurally underpowered).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

IG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(IG_ROOT.parent.parent))
sys.path.insert(0, str(IG_ROOT))

from inspect_gate.certify import clopper_pearson_upper

MIN_N_DEF = 22   # per-repeat escaped power floor (PREREG A1)
MIN_N_GOOD = 36  # per-repeat false-reject power floor (PREREG A1)
ESCAPED_THRESH = 0.13   # alpha_miss 0.10 + tol 0.03
FR_THRESH = 0.08        # alpha_fr 0.05 + tol 0.03
CONF = 0.95

MVTEC_DIR = IG_ROOT / "analysis_2026-07-10" / "gate_calibration"
VISA_DIR = IG_ROOT / "visa_results_2026-07-12" / "gate_calibration"
SEEDS = [0, 1, 2, 3, 4]
BACKBONES = ["patchcore", "dinomaly"]


def grade_cell(cat, cell, floors):
    """Grade ONE (category, seed, backbone) cell per A1/A2/A3."""
    t2 = cell["tier2"]
    n_rep = cell["n_repeats"]
    ndef_pr = t2["n_eval_def_total"] / n_rep
    ngood_pr = t2["n_eval_good_total"] / n_rep
    g2_cert = bool(floors.get(cat, {}).get("g2_certified", False))

    # ---- ESCAPED axis (A1 power + A2 interval/interpretation) ----
    esc_powered = ndef_pr >= MIN_N_DEF
    esc = {"per_repeat_n_eval_def": ndef_pr, "powered": esc_powered}
    if not esc_powered:
        esc["verdict"] = "underpowered-excluded"
    else:
        rate = t2["pooled_escaped_rate"]
        n_pr = int(round(ndef_pr))
        k_pr = int(round(rate * n_pr))
        ub_perrepeat = clopper_pearson_upper(k_pr, n_pr, CONF)
        esc["pooled_escaped_rate"] = rate
        esc["per_repeat_k"] = k_pr
        esc["ub_1sided_perrepeat_PRIMARY"] = ub_perrepeat
        esc["ub_1sided_pooled_SECONDARY"] = t2["escaped_ub_1sided"]
        esc["threshold"] = ESCAPED_THRESH
        esc["verdict"] = "pass" if ub_perrepeat <= ESCAPED_THRESH else "fail"

    # ---- FALSE-REJECT axis (A3 G2-restriction + A1 power) ----
    fr = {"per_repeat_n_eval_good": ngood_pr, "g2_certified": g2_cert}
    if not g2_cert:
        fr["verdict"] = "G2-REFUSED-excluded"   # A3: not eligible, not a pass
    else:
        fr_powered = ngood_pr >= MIN_N_GOOD
        fr["powered"] = fr_powered
        if not fr_powered:
            fr["verdict"] = "underpowered-excluded"   # A1
        else:
            rate = t2["pooled_false_reject_rate"]
            n_pr = int(round(ngood_pr))
            k_pr = int(round(rate * n_pr))
            ub_perrepeat = clopper_pearson_upper(k_pr, n_pr, CONF)
            fr["ub_1sided_perrepeat_PRIMARY"] = ub_perrepeat
            fr["ub_1sided_pooled_SECONDARY"] = t2["false_reject_ub_1sided"]
            fr["threshold"] = FR_THRESH
            fr["verdict"] = "pass" if ub_perrepeat <= FR_THRESH else "fail"

    return {"escaped": esc, "false_reject": fr}


def grade_benchmark(name, gcdir):
    cells = {}
    for backbone in BACKBONES:
        for seed in SEEDS:
            p = gcdir / f"v1_{backbone}_seed{seed}.json"
            d = json.loads(p.read_text())
            floors = d["certifiability_floors"]
            for cat, cell in d["v1"]["per_category"].items():
                cells[f"{backbone}|{cat}|seed{seed}"] = grade_cell(cat, cell, floors)

    # ---- tally per axis ----
    def tally(axis):
        buckets = {}
        for k, v in cells.items():
            verdict = v[axis]["verdict"]
            buckets.setdefault(verdict, []).append(k)
        return {b: {"count": len(ks), "cells": sorted(ks)} for b, ks in buckets.items()}

    return {
        "benchmark": name,
        "n_cells_total": len(cells),
        "escaped_axis": tally("escaped"),
        "false_reject_axis": tally("false_reject"),
        "per_cell": cells,
    }


def main():
    outdir = IG_ROOT / "c2_tier2_2026-07-13"
    for name, gcdir, fn in (("MVTec-AD", MVTEC_DIR, "tier2_mvtec.json"),
                            ("VisA", VISA_DIR, "tier2_visa.json")):
        res = grade_benchmark(name, gcdir)
        (outdir / fn).write_text(json.dumps(res, indent=2))
        print(f"\n===== {name} tier-2 grading =====")
        print("ESCAPED axis:")
        for b, info in sorted(res["escaped_axis"].items()):
            print(f"  {b}: {info['count']}")
        print("FALSE-REJECT axis:")
        for b, info in sorted(res["false_reject_axis"].items()):
            print(f"  {b}: {info['count']}")
        print(f"  wrote {fn}")


if __name__ == "__main__":
    main()
