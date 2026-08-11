#!/usr/bin/env python3
"""MPDD train-holdout G2 rescue arm -- the constructive counter-story to the
primary-protocol floor (FLOOR-PREDICTION.md SS"Constructive counter-story: the
train-holdout arm"). Mirrors g2_promotion_2026-07-12/run_g2_promotion.py (the
signed MVTec train-holdout PROMOTION arm) stage-for-stage on the MPDD holdout
substrate, so every number is directly comparable with the primary MPDD pass
(run_mpdd_analysis.py) and the MVTec promotion table.

MPDD is POST-FREEZE EXPLORATORY (identical status to VisA; run_mpdd_analysis.py
docstring), and the train-holdout arm is additionally a FLAG-GATED,
PREREG-NEUTRAL protocol variant (--good-cal train-holdout; design SS3.2): it is
never in the confirmatory Holm family and never re-freezes anything. PatchCore
only (Dinomaly has no train-side score dump), exactly as the MVTec promotion arm.

What changes vs the primary pass, ALL disclosed here:
  * G2's calibration pool = the 20%-of-train-good HOLDOUT pool
    (--holdout-frac 0.2 --holdout-seed 0; holdout rows carry split=="train",
    ids match the .holdout_provenance.json sidecar) instead of the tiny
    test-good calibration half. G1 is UNAFFECTED (design SS2.3).
  * The KS exchangeability gate (design SS2.3) + audited-not-certified
    fallback live INSIDE gate.calibrate_gate and are reused VERBATIM: a
    category whose holdout-good scores KS-differ (BH alpha=0.05) from the
    calibration-half good scores reports g2_mode="audited-not-certified"
    and is NOT promoted. The only change from the primary calibrate call is
    the two holdout keyword args -- everything else is byte-identical.
  * Sanity (no gate): the holdout arm re-scores the test rows with a memory
    bank fit on 80% of train-good, so its test scores are NOT identical to
    the primary (100%-bank) arm -- per-category Spearman + image-AUROC deltas
    are reported to show they are nonetheless the same ranking, not a
    different model.
Comparison target: primary-protocol floors in
mpdd_results_2026-07-13/gate_calibration/v1_patchcore_seed*.json (G2 0/6)."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import ks_2samp, spearmanr

IG_ROOT = _portal_repo_root()
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons on path
sys.path.insert(0, str(IG_ROOT))
from inspect_gate import io as _io            # noqa: E402
from inspect_gate import gate as _gate        # noqa: E402
from inspect_gate import certify as _certify  # noqa: E402
from inspect_gate import splits as _splits    # noqa: E402
from inspect_gate import reproduction as _repro  # noqa: E402

HOLDOUT_DIR = IG_ROOT / "mpdd_pulled_2026-07-14" / "patchcore_holdout"
PRIMARY_CANON = IG_ROOT / "mpdd_results_2026-07-13" / "canonical"
OUT = IG_ROOT / "mpdd_results_2026-07-13"
CATEGORIES = ["bracket_black", "bracket_brown", "bracket_white", "connector", "metal_plate", "tubes"]
SEEDS = [0, 1, 2, 3, 4]
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
N_REPEATS = 20
# Scaled kill-gates: identical to the primary MPDD pass (design ratios over
# n_cat=6; see run_mpdd_analysis.py docstring).
N_CAT = len(CATEGORIES)
K1_MAX_VIOLATIONS = math.ceil(N_CAT * 5 / 15)   # = 2
# Floor at alpha_fr=0.05: certifiability_floor(n)=1/(n+1) <= 0.05  <=>  n >= 19.
G2_FLOOR_MIN_N = 19


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_seed(seed: int):
    """Test rows (split=='test') and train-good holdout pool (split=='train')
    for one seed, merged across categories -- mirrors g2_promotion.load_seed."""
    test, holdout = [], []
    for cat in CATEGORIES:
        p = HOLDOUT_DIR / f"seed_{seed}" / f"scores_{cat}.jsonl"
        for r in _io.load_scores(str(p)):
            (test if r["split"] == "test" else holdout).append(r)
    return test, holdout


def floor_reason(cat, stratum, ks_entry):
    """Human-readable reason the category is / isn't G2-certifiable under the
    train-holdout arm. Count-and-KS only, so seed-invariant in the count part."""
    n_good = stratum["n_cal_good"]
    mode = stratum["g2_mode"]
    if mode == "audited-not-certified":
        return (f"KS exchangeability gate FAILED (train-holdout good vs test-good, "
                f"BH alpha=0.05): p_bh={ks_entry.get('p_bh'):.4g}; "
                f"g2_mode=audited-not-certified (no promotion), n_holdout_good={n_good}")
    # g2_mode == "train-holdout": KS passed, G2 pool = holdout pool.
    if not stratum["g2_certified"]:
        return (f"KS PASSED but holdout pool too small: n_holdout_good={n_good} "
                f"< {G2_FLOOR_MIN_N} (floor 1/(n+1)={1.0/(n_good+1):.4g} > alpha_fr={ALPHA_FR})")
    return (f"CERTIFIED: KS PASSED and n_holdout_good={n_good} >= {G2_FLOOR_MIN_N} "
            f"(floor 1/(n+1)={1.0/(n_good+1):.4g} <= alpha_fr={ALPHA_FR})")


def run_gate_calibration():
    log(f"Stage 1: train-holdout G2 gate calibration (patchcore, R={N_REPEATS})")
    (OUT / "gate_calibration").mkdir(parents=True, exist_ok=True)
    per_seed = {}
    for seed in SEEDS:
        t0 = time.time()
        test_records, holdout_pool = load_seed(seed)
        reps = _splits.repeated_stratified_splits(test_records, n_repeats=N_REPEATS)

        floors = {}
        ks_at_floor = {}
        cells_by_category = {cat: [] for cat in CATEGORIES}
        for i, (cal, ev) in enumerate(reps):
            good_cal = [r for r in cal if r["label"] == "good"]
            # VERBATIM the primary calibrate call except the two holdout kwargs.
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
                ks_at_floor = {cat: gate["ks_gate"].get(cat, {}) for cat in CATEGORIES}
            routed = _gate.route_gate(gate, ev)
            by_cat_ev = {}
            for r in ev:
                by_cat_ev.setdefault(r["category"], []).append(r)
            for cat, recs in by_cat_ev.items():
                cat_decisions = [d for d in routed["decisions"] if d["category"] == cat]
                cells_by_category[cat].append(_certify.coverage_cell(recs, cat_decisions))

        v1 = _certify.aggregate_v1_cells(cells_by_category, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR)
        per_cell_tier1 = [v["tier1"] for v in v1["per_category"].values()]
        k1 = _certify.coverage_sanity_check_k1(per_cell_tier1, max_violations=K1_MAX_VIOLATIONS)

        reasons = {cat: floor_reason(cat, floors[cat], ks_at_floor.get(cat, {}))
                   for cat in CATEGORIES}
        n_g2 = sum(1 for f in floors.values() if f["g2_certified"])
        n_ks_fail = sum(1 for f in floors.values() if f.get("g2_mode") == "audited-not-certified")
        n_floor_short = sum(1 for f in floors.values()
                            if f["g2_mode"] == "train-holdout" and not f["g2_certified"])
        per_seed[seed] = {
            "floors": floors,
            "ks_gate": ks_at_floor,
            "ks_alpha": _gate.DEFAULT_KS_ALPHA,
            "floor_reasons": reasons,
            "v1": v1,
            "k1": k1,
            "n_g2_certified": n_g2,
            "n_ks_fallback": n_ks_fail,
            "n_floor_short": n_floor_short,
        }
        (OUT / "gate_calibration" / f"v1_holdout_patchcore_seed{seed}.json").write_text(
            json.dumps(_io.to_jsonable(per_seed[seed]), indent=2))
        log(f"  seed {seed}: g2_certified={n_g2}/6 ks_fallback={n_ks_fail} "
            f"floor_short={n_floor_short} k1_tripped={k1['k1_tripped']} [{time.time()-t0:.1f}s]")
    return per_seed


def run_consistency_sanity():
    """No gate: per-category Spearman + image-AUROC delta between the holdout
    arm's test rows (80%-bank) and the primary arm's test rows (100%-bank)."""
    log("Stage 2: test-row consistency vs primary arm (Spearman + AUROC delta, no gate)")
    out = {}
    for seed in SEEDS:
        primary = {r["image_id"]: r for r in
                   _io.load_scores(str(PRIMARY_CANON / f"scores_patchcore_seed{seed}.jsonl"))
                   if r["split"] == "test"}
        test_records, _ = load_seed(seed)
        holdout_test = {r["image_id"]: r for r in test_records}
        per_cat = {}
        for cat in CATEGORIES:
            ids = sorted(k for k in holdout_test
                         if holdout_test[k]["category"] == cat and k in primary)
            hs = np.array([holdout_test[k]["score"] for k in ids], dtype=float)
            ps = np.array([primary[k]["score"] for k in ids], dtype=float)
            labels = np.array([holdout_test[k]["label"] == "defect" for k in ids], dtype=bool)
            rho, _ = spearmanr(hs, ps)
            auroc_h = _repro.image_auroc(hs, labels)
            auroc_p = _repro.image_auroc(ps, labels)
            per_cat[cat] = {
                "n_matched": len(ids),
                "spearman_rho": float(rho),
                "auroc_holdout_arm": float(auroc_h),
                "auroc_primary_arm": float(auroc_p),
                "auroc_delta": float(auroc_h - auroc_p),
            }
        out[seed] = per_cat
        rhos = [per_cat[c]["spearman_rho"] for c in CATEGORIES]
        dmax = max(abs(per_cat[c]["auroc_delta"]) for c in CATEGORIES)
        log(f"  seed {seed}: min Spearman={min(rhos):.4f} max|AUROC delta|={dmax:.4f}")
    return out


def main():
    gate = run_gate_calibration()
    consistency = run_consistency_sanity()

    # Cross-seed invariance of the count part of the floor (n_holdout_good is
    # seed-invariant; only the re-scored values move, so counts must match).
    mismatches = []
    for seed in SEEDS:
        for other in SEEDS:
            for cat in CATEGORIES:
                if gate[seed]["floors"][cat]["n_cal_good"] != gate[other]["floors"][cat]["n_cal_good"]:
                    mismatches.append((seed, other, cat))

    # Headline count. g2_certified = (KS pass) AND (n_holdout_good >= 19).
    # Report per seed and the modal/consensus value.
    g2_by_seed = {seed: gate[seed]["n_g2_certified"] for seed in SEEDS}
    ks_fallback_by_seed = {seed: gate[seed]["n_ks_fallback"] for seed in SEEDS}
    # Floor-only prediction (KS-AGNOSTIC, pool-size only): categories whose RAW
    # train-holdout good pool clears the floor (>=19). This is the number
    # FLOOR-PREDICTION.md reports (5/6); it is seed-invariant. NOTE this must be
    # read from the raw holdout pool, NOT floors[cat]["n_cal_good"], because a
    # KS-failed category falls back to the (smaller) test-good cal half there.
    _, holdout_pool0 = load_seed(0)
    holdout_pool_sizes = {cat: sum(1 for r in holdout_pool0
                                   if r["category"] == cat and r["label"] == "good")
                          for cat in CATEGORIES}
    floor_only = sum(1 for cat in CATEGORIES if holdout_pool_sizes[cat] >= G2_FLOOR_MIN_N)

    summary = {
        "arm": "train-holdout (--good-cal train-holdout, --holdout-frac 0.2 --holdout-seed 0)",
        "backbone": "patchcore",
        "status": "post-freeze exploratory; flag-gated prereg-NEUTRAL protocol variant; "
                  "never in the confirmatory Holm family",
        "alpha_fr": ALPHA_FR,
        "alpha_miss": ALPHA_MISS,
        "n_repeats": N_REPEATS,
        "ks_alpha": _gate.DEFAULT_KS_ALPHA,
        "g2_floor_min_n_holdout_good": G2_FLOOR_MIN_N,
        "g2_certified_by_seed": g2_by_seed,
        "ks_fallback_by_seed": ks_fallback_by_seed,
        "holdout_pool_good_sizes": holdout_pool_sizes,
        "g2_certified_floor_only_prediction": floor_only,
        "primary_g2_certified": 0,
        "n_cal_count_mismatches_across_seeds": len(mismatches),
        "per_seed_floor_reasons_seed0": gate[0]["floor_reasons"],
        "consistency_min_spearman": min(
            consistency[s][c]["spearman_rho"] for s in SEEDS for c in CATEGORIES),
        "consistency_max_abs_auroc_delta": max(
            abs(consistency[s][c]["auroc_delta"]) for s in SEEDS for c in CATEGORIES),
    }

    payload = {
        "summary": summary,
        "gate_calibration": {seed: {k: gate[seed][k] for k in
                                    ("floors", "ks_gate", "ks_alpha", "floor_reasons",
                                     "k1", "n_g2_certified", "n_ks_fallback", "n_floor_short")}
                             for seed in SEEDS},
        "consistency_sanity": consistency,
        "kill_gate_thresholds": {"k1_max_violations": K1_MAX_VIOLATIONS, "n_categories": N_CAT},
    }
    (OUT / "HOLDOUT-RESULTS.json").write_text(json.dumps(_io.to_jsonable(payload), indent=2))
    log(f"wrote {OUT / 'HOLDOUT-RESULTS.json'}")
    log(f"HEADLINE: G2 certifiable with train-holdout = {g2_by_seed} / 6 "
        f"(vs 0/6 primary; floor-only predicts {floor_only}/6)")
    log(f"n_cal count mismatches across seeds: {len(mismatches)}")
    log("ALL STAGES COMPLETE")


if __name__ == "__main__":
    main()
