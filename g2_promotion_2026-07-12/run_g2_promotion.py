#!/usr/bin/env python3
"""G2 train-holdout PROMOTION arm (unlocked by SIGN-OFF-RECORD-2026-07-11;
protocol per ANALYSIS-MEMO gating note + design SS2.3/SS3.2): re-run the
R=20 gate calibration with ``good_cal_holdout`` = the 20%-of-train-good
holdout pool, PatchCore only (Dinomaly has no train-side score dump).

Substrate: holdout_results_2026-07-10/pulled_final -- each (category, seed)
file carries BOTH the holdout run's own re-scored test rows (memory bank =
80% of train-good, so test scores are bank-consistent and deliberately NOT
taken from fullscore_results) and the ``split=="train"`` good holdout rows.

The KS exchangeability gate + audited-not-certified fallback live INSIDE
gate.calibrate_gate (signed condition: a category failing KS reports
``g2_mode="audited-not-certified"``, never a silent promotion).
Comparison target: primary-protocol floors in
analysis_2026-07-10/gate_calibration/v1_patchcore_seed*.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

IG_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons/tools/inspect-gate")
sys.path.insert(0, str(IG_ROOT))
from inspect_gate import io as _io          # noqa: E402
from inspect_gate import gate as _gate      # noqa: E402
from inspect_gate import certify as _certify  # noqa: E402
from inspect_gate import splits as _splits  # noqa: E402

HOLDOUT_DIR = IG_ROOT / "holdout_results_2026-07-10/pulled_final/root/autodl-tmp/ig_scores_holdout"
OUT = IG_ROOT / "g2_promotion_2026-07-12"
CATEGORIES = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor",
              "wood", "zipper"]
SEEDS = [0, 1, 2, 3, 4]
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
N_REPEATS = 20


def load_seed(seed: int):
    test, holdout = [], []
    for cat in CATEGORIES:
        p = HOLDOUT_DIR / f"scores_patchcore_{cat}_seed{seed}.jsonl"
        for r in _io.load_scores(str(p)):
            (test if r["split"] == "test" else holdout).append(r)
    return test, holdout


def main():
    (OUT / "gate_calibration").mkdir(parents=True, exist_ok=True)
    summary = {}
    for seed in SEEDS:
        t0 = time.time()
        test_records, holdout_pool = load_seed(seed)
        reps = _splits.repeated_stratified_splits(test_records, n_repeats=N_REPEATS)

        floors = {}
        cells_by_category = {cat: [] for cat in CATEGORIES}
        for i, (cal, ev) in enumerate(reps):
            good_cal = [r for r in cal if r["label"] == "good"]
            gate = _gate.calibrate_gate(
                cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR, mondrian="category",
                good_cal_holdout=holdout_pool, good_cal_holdout_cal=good_cal,
                backbone="patchcore", seed=i,
            )
            if i == 0:
                for cat in CATEGORIES:
                    s = gate["strata"].get(cat)
                    if s is not None:
                        floors[cat] = {k: s[k] for k in
                                       ("n_cal_defect", "n_cal_good", "alpha_min_g1",
                                        "alpha_min_g2", "g1_certified", "g2_certified",
                                        "g2_mode")}
            routed = _gate.route_gate(gate, ev)
            by_cat_ev = {}
            for r in ev:
                by_cat_ev.setdefault(r["category"], []).append(r)
            for cat, recs in by_cat_ev.items():
                cat_decisions = [d for d in routed["decisions"] if d["category"] == cat]
                cells_by_category[cat].append(_certify.coverage_cell(recs, cat_decisions))

        v1 = _certify.aggregate_v1_cells(cells_by_category, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR)
        per_cell_tier1 = [v["tier1"] for v in v1["per_category"].values()]
        k1 = _certify.coverage_sanity_check_k1(per_cell_tier1, max_violations=5)
        n_g2 = sum(1 for f in floors.values() if f["g2_certified"])
        n_ks_fail = sum(1 for f in floors.values() if f.get("g2_mode") == "audited-not-certified")
        summary[seed] = {"n_g2_certified": n_g2, "n_ks_fallback": n_ks_fail,
                         "k1_tripped": k1["k1_tripped"]}
        payload = {"floors": floors, "v1": v1, "k1": k1}
        (OUT / "gate_calibration" / f"v1_promotion_patchcore_seed{seed}.json").write_text(
            json.dumps(_io.to_jsonable(payload), indent=2))
        print(f"seed {seed}: g2_certified={n_g2}/15 ks_fallback={n_ks_fail} "
              f"k1_tripped={k1['k1_tripped']} [{time.time()-t0:.1f}s]", flush=True)

    # side-by-side vs primary protocol
    compare = {}
    for seed in SEEDS:
        prim_p = IG_ROOT / "analysis_2026-07-10/gate_calibration" / f"v1_patchcore_seed{seed}.json"
        prim = json.loads(prim_p.read_text())["certifiability_floors"]
        promo = json.loads((OUT / "gate_calibration" / f"v1_promotion_patchcore_seed{seed}.json"
                            ).read_text())["floors"]
        compare[seed] = {cat: {"primary_g2": prim.get(cat, {}).get("g2_certified"),
                               "promoted_g2": promo.get(cat, {}).get("g2_certified"),
                               "g2_mode": promo.get(cat, {}).get("g2_mode")}
                         for cat in CATEGORIES}
    json.dump({"summary": summary, "compare": compare},
              open(OUT / "G2-PROMOTION-RESULT.json", "w"), indent=1)
    print("G2_PROMOTION_DONE", json.dumps(summary))


if __name__ == "__main__":
    main()
