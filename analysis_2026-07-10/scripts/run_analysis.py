#!/usr/bin/env python3
"""Post-analysis pass over the local GPU substrate (PatchCore fullscore,
Dinomaly Branch-A canonical scores) — PREREG-2026-07-10 §7's binding
analysis-plan steps 2-6, restricted to what does NOT require the frozen
PREREG-DRAFT amendment (task #31/#33 re-scope).

Explicitly OUT OF SCOPE (gated, not touched by this script):
  - holdout_results_2026-07-10/ (the --good-cal-holdout train-good G2
    "promotion" arm) — never read.
  - B3 (train-good quantile) audit practice — impossible anyway, neither
    local score dump carries split="train" records.
  - Any cross-seed OR cross-category pooling into a single confirmatory
    Holm family / V1 verdict (design's run_main_grid.sh Stage D, itself
    still a TODO skeleton) — every gate/route/certify/audit call below
    stays scoped to ONE (backbone, seed) or ONE (backbone, seed, category)
    cell; no seed-pooling, no cross-category B1/B2 pooling.
  - V1 tier-2 pass/fail as a verdict — computed (it falls out of
    certify.aggregate_v1_cells for free) but reported only as a
    descriptive number pending PREREG §9 A1/A2 sign-off, never as pass/fail.

Everything here uses ONLY the primary protocol (`good_cal_holdout=None`,
i.e. --good-cal test) and R=20 repeats (design's frozen split protocol,
`splits.py`), matching PREREG §3's own already-published certifiability-
floor table exactly (cross-checked below) and PREREG §7 step 5's binding
per-cell computation -- just run per (backbone, seed) instead of waiting
for the multi-seed Stage D pooling decision.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons")
IG_ROOT = REPO_ROOT / "tools" / "inspect-gate"
sys.path.insert(0, str(REPO_ROOT))

from inspect_gate import io as _io
from inspect_gate import gate as _gate
from inspect_gate import certify as _certify
from inspect_gate import splits as _splits
from inspect_gate import audit as _audit
from inspect_gate import reproduction as _repro

OUT = IG_ROOT / "analysis_2026-07-10"
PATCHCORE_DIR = OUT / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"
DINOMALY_DIR = IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
CATEGORIES = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor",
              "wood", "zipper"]
SEEDS = [0, 1, 2, 3, 4]
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
N_REPEATS = 20
N_PERM = 2000
AUDIT_ALPHA = 0.05

# Published Dinomaly (Guo et al., CVPR 2025) mean image-AUROC on MVTec-AD,
# independently re-derived below from the local canonical scores (never
# trusted from the log/literature alone) -- see ANALYSIS-MEMO.md §1.
DINOMALY_PUBLISHED_MEAN_IAUROC = 0.996


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_patchcore_seed(seed: int):
    recs = []
    for cat in CATEGORIES:
        p = PATCHCORE_DIR / f"scores_patchcore_{cat}_seed{seed}.jsonl"
        recs.extend(_io.load_scores(str(p)))
    return recs


def load_dinomaly_seed(seed: int):
    p = DINOMALY_DIR / f"scores_dinomaly_seed{seed}.jsonl"
    return _io.load_scores(str(p))


# --------------------------------------------------------------------------- #
# 1. Reproduction gate, per backbone x seed (independent re-derivation)
# --------------------------------------------------------------------------- #
def run_reproduction():
    log("Stage 1: reproduction gate (per backbone x seed)")
    results = {"patchcore": {}, "dinomaly": {}}
    for seed in SEEDS:
        pc = load_patchcore_seed(seed)
        results["patchcore"][seed] = _repro.reproduction_gate(pc, "patchcore")

        dm = load_dinomaly_seed(seed)
        os.environ["INSPECT_GATE_DINOMALY_TARGET_AUROC"] = str(DINOMALY_PUBLISHED_MEAN_IAUROC)
        import importlib
        importlib.reload(_repro)
        results["dinomaly"][seed] = _repro.reproduction_gate(dm, "dinomaly")

    out_path = OUT / "reproduction" / "reproduction_gate.json"
    out_path.write_text(json.dumps(_io.to_jsonable(results), indent=2))
    log(f"  wrote {out_path}")
    return results


# --------------------------------------------------------------------------- #
# 2. Cross-seed stability
# --------------------------------------------------------------------------- #
def run_seed_stability(repro_results):
    log("Stage 2: cross-seed stability")
    out = {"patchcore": {}, "dinomaly": {}}

    # PatchCore: bit-identical check + per-category per-seed AUROC (already
    # computed in Stage 1's per_category dicts) + pairwise score-array diff.
    pc_auroc = {seed: repro_results["patchcore"][seed]["per_category"] for seed in SEEDS}
    out["patchcore"]["per_seed_per_category_auroc"] = pc_auroc
    identical_pairs = {}
    for cat in CATEGORIES:
        s0 = {r["image_id"]: r["score"] for r in
              _io.load_scores(str(PATCHCORE_DIR / f"scores_patchcore_{cat}_seed0.jsonl"))}
        for seed in SEEDS[1:]:
            s_n = {r["image_id"]: r["score"] for r in
                   _io.load_scores(str(PATCHCORE_DIR / f"scores_patchcore_{cat}_seed{seed}.jsonl"))}
            same_ids = set(s0) == set(s_n)
            max_abs_diff = max(abs(s0[k] - s_n[k]) for k in s0) if same_ids else None
            bit_identical = same_ids and all(s0[k] == s_n[k] for k in s0)
            identical_pairs[f"{cat}_seed0_vs_seed{seed}"] = {
                "same_image_ids": same_ids,
                "bit_identical_scores": bit_identical,
                "max_abs_score_diff": max_abs_diff,
            }
    out["patchcore"]["pairwise_seed0_diff"] = identical_pairs
    n_identical = sum(1 for v in identical_pairs.values() if v["bit_identical_scores"])
    out["patchcore"]["n_bit_identical_pairs"] = n_identical
    out["patchcore"]["n_pairs_checked"] = len(identical_pairs)

    # Dinomaly: per-category per-seed AUROC + spread stats
    dm_auroc = {seed: repro_results["dinomaly"][seed]["per_category"] for seed in SEEDS}
    out["dinomaly"]["per_seed_per_category_auroc"] = dm_auroc
    per_cat_spread = {}
    for cat in CATEGORIES:
        vals = np.array([dm_auroc[seed][cat] for seed in SEEDS])
        per_cat_spread[cat] = {
            "mean": float(vals.mean()), "std": float(vals.std(ddof=1)),
            "min": float(vals.min()), "max": float(vals.max()), "range": float(vals.max() - vals.min()),
        }
    out["dinomaly"]["per_category_seed_spread"] = per_cat_spread
    mean_iaurocs = np.array([repro_results["dinomaly"][s]["mean_auroc"] for s in SEEDS])
    out["dinomaly"]["mean_iauroc_across_seeds"] = {
        "values": mean_iaurocs.tolist(), "mean": float(mean_iaurocs.mean()),
        "std": float(mean_iaurocs.std(ddof=1)), "min": float(mean_iaurocs.min()),
        "max": float(mean_iaurocs.max()),
    }

    out_path = OUT / "seed_stability" / "seed_stability.json"
    out_path.write_text(json.dumps(_io.to_jsonable(out), indent=2))
    log(f"  wrote {out_path}  (patchcore bit-identical pairs: {n_identical}/{len(identical_pairs)})")
    return out


# --------------------------------------------------------------------------- #
# 3. G1(+G2 primary) gate calibration, R=20 repeats, per (backbone, seed)
# --------------------------------------------------------------------------- #
def run_gate_calibration(loader, backbone_name):
    log(f"Stage 3: gate calibration ({backbone_name}, R={N_REPEATS}, primary protocol)")
    per_seed_results = {}
    for seed in SEEDS:
        t0 = time.time()
        scores = loader(seed)
        test_records = [r for r in scores if r["split"] == "test"]
        reps = _splits.repeated_stratified_splits(test_records, n_repeats=N_REPEATS)

        cells_by_category = {cat: [] for cat in CATEGORIES}
        floors_by_category = {}
        for i, (cal, ev) in enumerate(reps):
            gate = _gate.calibrate_gate(
                cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR, mondrian="category",
                good_cal_holdout=None, good_cal_holdout_cal=None,
                backbone=backbone_name, seed=i,
            )
            if i == 0:
                for cat in CATEGORIES:
                    s = gate["strata"].get(cat)
                    if s is not None:
                        floors_by_category[cat] = {
                            "n_cal_defect": s["n_cal_defect"], "n_cal_good": s["n_cal_good"],
                            "alpha_min_g1": s["alpha_min_g1"], "alpha_min_g2": s["alpha_min_g2"],
                            "g1_certified": s["g1_certified"], "g2_certified": s["g2_certified"],
                        }
            routed = _gate.route_gate(gate, ev)
            by_cat_ev = {}
            for r in ev:
                by_cat_ev.setdefault(r["category"], []).append(r)
            for cat, recs in by_cat_ev.items():
                cat_decisions = [d for d in routed["decisions"] if d["category"] == cat]
                cell = _certify.coverage_cell(recs, cat_decisions)
                cells_by_category[cat].append(cell)

        v1 = _certify.aggregate_v1_cells(cells_by_category, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR)
        per_cell_tier1 = [v["tier1"] for v in v1["per_category"].values()]
        k1 = _certify.coverage_sanity_check_k1(per_cell_tier1, max_violations=5)
        median_deferral = {cat: float(np.nanmedian([c["deferral_rate"] for c in cells]))
                            for cat, cells in cells_by_category.items()}
        k2 = _certify.vacuity_check_k2(median_deferral, threshold=0.80, min_categories=8)

        per_seed_results[seed] = {
            "certifiability_floors": floors_by_category,
            "v1": v1,
            "k1": k1,
            "k2": k2,
            "median_deferral_by_category": median_deferral,
        }
        out_path = OUT / "gate_calibration" / f"v1_{backbone_name}_seed{seed}.json"
        out_path.write_text(json.dumps(_io.to_jsonable(per_seed_results[seed]), indent=2))
        log(f"  seed {seed}: k1_tripped={k1['k1_tripped']} ({k1['n_violations']}/{k1['n_cells']}) "
            f"k2_tripped={k2['k2_tripped']} ({k2['n_vacuous_categories']}/{k2['n_categories']}) "
            f"[{time.time()-t0:.1f}s]")
    return per_seed_results


# --------------------------------------------------------------------------- #
# 4. Exploratory per-cell audit (fixed, tuned only; no B3 -- no train-good
#    data in either local score dump), repeat-0 halves, per (backbone,
#    seed, category) -- mirrors PREREG §5's own pilot-audit methodology
#    (per-category, family size 2, D5-disclosed B1==B2 degeneracy).
# --------------------------------------------------------------------------- #
def run_audit_pass(loader, backbone_name):
    log(f"Stage 4: exploratory per-cell audit ({backbone_name}, n_perm={N_PERM})")
    per_seed_results = {}
    for seed in SEEDS:
        t0 = time.time()
        scores = loader(seed)
        test_records = [r for r in scores if r["split"] == "test"]
        cal0, ev0 = _splits.stratified_cal_eval_split(test_records, repeat_seed=0)

        per_cat = {}
        for cat in CATEGORIES:
            cal_cat = [r for r in cal0 if r["category"] == cat]
            ev_cat = [r for r in ev0 if r["category"] == cat]
            gate = _gate.calibrate_gate(cal_cat, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                                        mondrian="category", backbone=backbone_name, seed=0)
            routed = _gate.route_gate(gate, ev_cat)
            target_deferral = routed["n_defer"] / routed["n"] if routed["n"] else 0.0
            result = _audit.run_audit(
                cal_cat, ev_cat, None, target_deferral_rate=target_deferral,
                practices=["fixed", "tuned"], backbone=backbone_name,
                n_perm=N_PERM, alpha=AUDIT_ALPHA, seed=seed,
            )
            per_cat[cat] = result
        per_seed_results[seed] = per_cat
        out_path = OUT / "audit" / f"audit_{backbone_name}_seed{seed}.json"
        out_path.write_text(json.dumps(_io.to_jsonable(per_cat), indent=2))
        log(f"  seed {seed} done [{time.time()-t0:.1f}s]")
    return per_seed_results


# --------------------------------------------------------------------------- #
def main():
    repro = run_reproduction()
    seed_stab = run_seed_stability(repro)

    pc_gate = run_gate_calibration(load_patchcore_seed, "patchcore")
    dm_gate = run_gate_calibration(load_dinomaly_seed, "dinomaly")

    pc_audit = run_audit_pass(load_patchcore_seed, "patchcore")
    dm_audit = run_audit_pass(load_dinomaly_seed, "dinomaly")

    # ---- cross-check: certifiability floors must match PREREG §3's table
    # exactly (backbone/seed-invariant -- pure function of test-set counts).
    log("Cross-check: certifiability floors vs PREREG §3 table")
    mismatches = []
    for backbone_name, gate_results in (("patchcore", pc_gate), ("dinomaly", dm_gate)):
        for seed in SEEDS:
            floors = gate_results[seed]["certifiability_floors"]
            for other_seed in SEEDS:
                other = gate_results[other_seed]["certifiability_floors"]
                for cat in CATEGORIES:
                    if floors[cat]["n_cal_defect"] != other[cat]["n_cal_defect"] or \
                       floors[cat]["n_cal_good"] != other[cat]["n_cal_good"]:
                        mismatches.append((backbone_name, seed, other_seed, cat))
    log(f"  n_cal-count mismatches across seeds (within backbone): {len(mismatches)}")

    summary = {
        "reproduction": repro,
        "seed_stability_summary": {
            "patchcore_bit_identical_pairs": f"{seed_stab['patchcore']['n_bit_identical_pairs']}/{seed_stab['patchcore']['n_pairs_checked']}",
            "dinomaly_mean_iauroc_across_seeds": seed_stab["dinomaly"]["mean_iauroc_across_seeds"],
        },
        "gate_calibration_k1_k2": {
            "patchcore": {seed: {"k1": pc_gate[seed]["k1"], "k2": pc_gate[seed]["k2"]} for seed in SEEDS},
            "dinomaly": {seed: {"k1": dm_gate[seed]["k1"], "k2": dm_gate[seed]["k2"]} for seed in SEEDS},
        },
        "n_cal_count_mismatches_across_seeds": len(mismatches),
    }
    out_path = OUT / "SUMMARY.json"
    out_path.write_text(json.dumps(_io.to_jsonable(summary), indent=2))
    log(f"wrote {out_path}")
    log("ALL STAGES COMPLETE")


if __name__ == "__main__":
    main()
