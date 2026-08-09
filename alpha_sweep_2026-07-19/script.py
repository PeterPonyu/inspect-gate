#!/usr/bin/env python3
"""Alpha-frontier sweep (POST-FREEZE EXPLORATORY, prereg F4 slot) — 2026-07-19.

Re-runs the FROZEN gate-calibration protocol (analysis_2026-07-10 /
visa_results_2026-07-12 / mpdd_results_2026-07-13 run_*_analysis.py Stage 3:
same splits.repeated_stratified_splits R=20, same calibrate_gate/route_gate
code path) across a grid of operating points:

    alpha_miss in {0.20, 0.10, 0.05, 0.02, 0.01}
    alpha_fr   in {0.10, 0.05, 0.02}

for all 3 benchmarks x 2 backbones x 5 seeds. Edits NO frozen result.

Verification: at the paper's operating point (0.10, 0.05) the script
reproduces the frozen v1_*_seed0.json per-category tier1 mean rates and
median deferral within 1e-9 (asserted, per benchmark x backbone).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons")
IG_ROOT = REPO_ROOT / "tools" / "inspect-gate"
sys.path.insert(0, str(IG_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from inspect_gate import io as _io
from inspect_gate import gate as _gate
from inspect_gate import certify as _certify
from inspect_gate import splits as _splits

OUT = IG_ROOT / "alpha_sweep_2026-07-19"

GRID_MISS = [0.20, 0.10, 0.05, 0.02, 0.01]
GRID_FR = [0.10, 0.05, 0.02]
SEEDS = [0, 1, 2, 3, 4]
N_REPEATS = 20

BENCH = {
    "mvtec": {
        "categories": ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut",
                       "leather", "metal_nut", "pill", "screw", "tile", "toothbrush",
                       "transistor", "wood", "zipper"],
        "frozen_dir": IG_ROOT / "analysis_2026-07-10" / "gate_calibration",
        "loaders": {
            "patchcore": lambda seed: [r for cat in BENCH["mvtec"]["categories"]
                                       for r in _io.load_scores(str(
                                           IG_ROOT / "analysis_2026-07-10" / "extracted" / "root"
                                           / "autodl-tmp" / "ig_scores_full"
                                           / f"scores_patchcore_{cat}_seed{seed}.jsonl"))],
            "dinomaly": lambda seed: _io.load_scores(str(
                IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
                / f"scores_dinomaly_seed{seed}.jsonl")),
        },
    },
    "visa": {
        "categories": ["candle", "capsules", "cashew", "chewinggum", "fryum",
                       "macaroni1", "macaroni2", "pcb1", "pcb2", "pcb3", "pcb4",
                       "pipe_fryum"],
        "frozen_dir": IG_ROOT / "visa_results_2026-07-12" / "gate_calibration",
        "loaders": {
            bb: (lambda bb: lambda seed: _io.load_scores(str(
                IG_ROOT / "visa_results_2026-07-12" / "canonical"
                / f"scores_{bb}_seed{seed}.jsonl")))(bb)
            for bb in ("patchcore", "dinomaly")
        },
    },
    "mpdd": {
        "categories": ["bracket_black", "bracket_brown", "bracket_white",
                       "connector", "metal_plate", "tubes"],
        "frozen_dir": IG_ROOT / "mpdd_results_2026-07-13" / "gate_calibration",
        "loaders": {
            bb: (lambda bb: lambda seed: _io.load_scores(str(
                IG_ROOT / "mpdd_results_2026-07-13" / "canonical"
                / f"scores_{bb}_seed{seed}.jsonl")))(bb)
            for bb in ("patchcore", "dinomaly")
        },
    },
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sweep_cell(test_records, categories, alpha_miss, alpha_fr):
    """One (benchmark, backbone, seed, grid-point): R=20 calibrate+route,
    aggregated per category. Returns per-category dict + pooled summary."""
    reps = _splits.repeated_stratified_splits(test_records, n_repeats=N_REPEATS)
    cells_by_category = {cat: [] for cat in categories}
    cert_counts = {"g1": [], "g2": [], "both": [], "refused": []}
    for i, (cal, ev) in enumerate(reps):
        gate = _gate.calibrate_gate(
            cal, alpha_miss=alpha_miss, alpha_fr=alpha_fr, mondrian="category",
            good_cal_holdout=None, good_cal_holdout_cal=None,
            backbone=None, seed=i,
        )
        n_g1 = sum(1 for s in gate["strata"].values() if s["g1_certified"])
        n_g2 = sum(1 for s in gate["strata"].values() if s["g2_certified"])
        n_both = sum(1 for s in gate["strata"].values()
                     if s["g1_certified"] and s["g2_certified"])
        cert_counts["g1"].append(n_g1)
        cert_counts["g2"].append(n_g2)
        cert_counts["both"].append(n_both)
        cert_counts["refused"].append(
            sum(1 for s in gate["strata"].values()
                if not s["g1_certified"] and not s["g2_certified"]))
        routed = _gate.route_gate(gate, ev)
        by_cat_ev = {}
        for r in ev:
            by_cat_ev.setdefault(r["category"], []).append(r)
        for cat, recs in by_cat_ev.items():
            cat_decisions = [d for d in routed["decisions"] if d["category"] == cat]
            cells_by_category[cat].append(_certify.coverage_cell(recs, cat_decisions))

    per_cat = {}
    for cat, cells in cells_by_category.items():
        if not cells:
            continue
        per_cat[cat] = {
            "mean_escaped": float(np.nanmean([c["escaped_defect_rate"] for c in cells])),
            "mean_fr": float(np.nanmean([c["false_reject_rate"] for c in cells])),
            "median_deferral": float(np.nanmedian([c["deferral_rate"] for c in cells])),
            "mean_deferral": float(np.nanmean([c["deferral_rate"] for c in cells])),
        }
    overall_deferral = float(np.nanmean([v["mean_deferral"] for v in per_cat.values()])) \
        if per_cat else float("nan")
    return {
        "per_category": per_cat,
        "certification_counts_per_repeat": cert_counts,
        "n_categories": len(per_cat),
        "overall_mean_deferral": overall_deferral,
    }


def main():
    t_start = time.time()
    results = {}
    verification = {}
    for bench, spec in BENCH.items():
        results[bench] = {}
        verification[bench] = {}
        for backbone, loader in spec["loaders"].items():
            log(f"{bench}/{backbone}: loading seeds")
            seed_records = {seed: [r for r in loader(seed) if r["split"] == "test"]
                            for seed in SEEDS}
            grid_out = {}
            for am in GRID_MISS:
                for af in GRID_FR:
                    t0 = time.time()
                    key = f"am{am}_af{af}"
                    per_seed = {}
                    for seed in SEEDS:
                        per_seed[seed] = sweep_cell(
                            seed_records[seed], spec["categories"], am, af)
                    grid_out[key] = {"alpha_miss": am, "alpha_fr": af,
                                     "per_seed": per_seed}
                    log(f"  {key} done [{time.time()-t0:.1f}s]")
            results[bench][backbone] = grid_out

            # ---- verification vs frozen artifact at (0.10, 0.05) ----
            frozen = json.load(open(spec["frozen_dir"] / f"v1_{backbone}_seed0.json"))
            mine = grid_out["am0.1_af0.05"]["per_seed"][0]
            max_d_esc = max_d_def = 0.0
            for cat, f in frozen["v1"]["per_category"].items():
                m = mine["per_category"][cat]
                max_d_esc = max(max_d_esc,
                                abs(f["tier1"]["mean_escaped_defect_rate"] - m["mean_escaped"]))
                max_d_def = max(max_d_def,
                                abs(frozen["median_deferral_by_category"][cat]
                                    - m["median_deferral"]))
            ok = max_d_esc < 1e-9 and max_d_def < 1e-9
            verification[bench][backbone] = {
                "max_abs_diff_mean_escaped": max_d_esc,
                "max_abs_diff_median_deferral": max_d_def,
                "reproduces_frozen_at_operating_point": bool(ok),
            }
            log(f"  VERIFY {bench}/{backbone}: max_d_esc={max_d_esc:.2e} "
                f"max_d_def={max_d_def:.2e} -> {'PASS' if ok else 'FAIL'}")

    results["verification"] = verification
    results["meta"] = {
        "grid_alpha_miss": GRID_MISS, "grid_alpha_fr": GRID_FR,
        "n_repeats": N_REPEATS, "seeds": SEEDS,
        "protocol": "identical to frozen run_*_analysis.py Stage 3 "
                    "(splits.repeated_stratified_splits R=20, calibrate_gate/route_gate)",
        "status": "post-freeze exploratory (prereg F4 slot); edits no frozen result",
        "date": "2026-07-19",
    }
    out_path = OUT / "results.json"
    out_path.write_text(json.dumps(_io.to_jsonable(results), indent=2))
    log(f"wrote {out_path}  [total {time.time()-t_start:.0f}s]")
    bad = [(b, bb) for b in verification for bb in verification[b]
           if not verification[b][bb]["reproduces_frozen_at_operating_point"]]
    if bad:
        log(f"VERIFICATION FAILURES: {bad}")
        sys.exit(1)
    log("all verification checks PASS")


if __name__ == "__main__":
    main()
