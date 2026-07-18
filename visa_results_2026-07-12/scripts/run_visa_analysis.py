#!/usr/bin/env python3
"""VisA cross-benchmark analysis pass — mirrors analysis_2026-07-10/scripts/
run_analysis.py stage-for-stage (same alphas, R=20 frozen split protocol,
same K1/K2 parameters, same exploratory audit setup) on the VisA canonical
scores produced by visa_adapter.py, so every number is directly comparable
with the MVTec table.

Deviations from the MVTec pass, all disclosed here:
  * CATEGORIES: VisA's 12 (vs MVTec's 15); K1 max_violations stays 5 and
    K2 min_categories stays 8 (same absolute thresholds; n_cells drops
    from 300 to 240 per (backbone, seed)).
  * Dinomaly reproduction target: 0.987 — Dinomaly's published VisA mean
    image-AUROC (Guo et al., CVPR 2025, arXiv:2405.14325), confirmed in
    analysis_2026-07-10/K6-CITATION-RESCAN.md item 11. NOTE the published
    figure is the multi-class (uni) setting, which is exactly what the box
    ran (dinomaly_visa_uni, one model per seed for all 12 categories).
  * PatchCore reproduction target: None. PatchCore (Roth et al., CVPR
    2022) predates VisA-wide benchmarking and the portfolio has NO
    repo-confirmed published PatchCore-on-VisA figure (K6 rescan covered
    MVTec only). Per reproduction.py's own rule ("never silently graded
    against a guessed number"), its VisA gate is DESCRIPTIVE: per-category
    and mean AUROC reported, pass=None.
  * Dinomaly is multi-class on VisA (one model, all categories) while the
    MVTec Branch-A run was the same repo's uni setting as well — but
    PatchCore remains per-category memory banks on both; unchanged.
Everything else (splits, gate, certify, audit code paths) is byte-identical
library code."""
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
sys.path.insert(0, str(IG_ROOT))

# Dinomaly published VisA figure (K6-CITATION-RESCAN item 11) — must be in
# the environment BEFORE inspect_gate.reproduction is imported.
DINOMALY_VISA_PUBLISHED_MEAN_IAUROC = 0.987
os.environ["INSPECT_GATE_DINOMALY_TARGET_AUROC"] = str(DINOMALY_VISA_PUBLISHED_MEAN_IAUROC)

from inspect_gate import io as _io  # noqa: E402
from inspect_gate import gate as _gate  # noqa: E402
from inspect_gate import certify as _certify  # noqa: E402
from inspect_gate import splits as _splits  # noqa: E402
from inspect_gate import audit as _audit  # noqa: E402
from inspect_gate import reproduction as _repro  # noqa: E402

OUT = IG_ROOT / "visa_results_2026-07-12"
CANON = OUT / "canonical"
CATEGORIES = ["candle", "capsules", "cashew", "chewinggum", "fryum", "macaroni1",
              "macaroni2", "pcb1", "pcb2", "pcb3", "pcb4", "pipe_fryum"]
SEEDS = [0, 1, 2, 3, 4]
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
N_REPEATS = 20
N_PERM = 2000
AUDIT_ALPHA = 0.05


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_seed(backbone: str, seed: int):
    return _io.load_scores(str(CANON / f"scores_{backbone}_seed{seed}.jsonl"))


# --------------------------------------------------------------------------- #
# 1. Reproduction gate, per backbone x seed
# --------------------------------------------------------------------------- #
def descriptive_reproduction(records):
    """reproduction_gate-shaped result with target=None (see module
    docstring: no repo-confirmed PatchCore-on-VisA published figure)."""
    by_cat = {}
    for r in records:
        if r["split"] == "test":
            by_cat.setdefault(r["category"], []).append(r)
    per_category = {}
    for cat, recs in sorted(by_cat.items()):
        per_category[cat] = _repro.image_auroc(
            np.array([r["score"] for r in recs], dtype=float),
            np.array([r["label"] == "defect" for r in recs], dtype=bool),
        )
    aurocs = list(per_category.values())
    return {
        "backbone": "patchcore", "target": None,
        "tolerance": _repro.DEFAULT_AUROC_TOLERANCE,
        "per_category": per_category,
        "mean_auroc": float(np.mean(aurocs)), "min_auroc": float(np.min(aurocs)),
        "n_categories": len(per_category), "pass": None,
        "note": "descriptive only: no repo-confirmed published PatchCore-on-VisA "
                "image-AUROC (K6 rescan covers MVTec only); per reproduction.py's "
                "no-guessed-target rule the gate does not grade this backbone.",
    }


def run_reproduction():
    log("Stage 1: reproduction gate (per backbone x seed)")
    assert _repro.DINOMALY_TARGET_AUROC == DINOMALY_VISA_PUBLISHED_MEAN_IAUROC, \
        "env override for the Dinomaly VisA target did not take effect"
    results = {"patchcore": {}, "dinomaly": {}}
    for seed in SEEDS:
        results["patchcore"][seed] = descriptive_reproduction(load_seed("patchcore", seed))
        results["dinomaly"][seed] = _repro.reproduction_gate(load_seed("dinomaly", seed), "dinomaly")
        log(f"  seed {seed}: dinomaly mean={results['dinomaly'][seed]['mean_auroc']:.4f} "
            f"pass={results['dinomaly'][seed]['pass']} | patchcore mean="
            f"{results['patchcore'][seed]['mean_auroc']:.4f} (descriptive)")
    out_path = OUT / "reproduction" / "reproduction_gate.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_io.to_jsonable(results), indent=2))
    log(f"  wrote {out_path}")
    return results


# --------------------------------------------------------------------------- #
# 2. Cross-seed stability
# --------------------------------------------------------------------------- #
def run_seed_stability(repro_results):
    log("Stage 2: cross-seed stability")
    out = {"patchcore": {}, "dinomaly": {}}

    # PatchCore: bit-identical check (per category, seed0 vs seed n)
    pc_by_seed = {}
    for seed in SEEDS:
        pc_by_seed[seed] = {r["image_id"]: r["score"] for r in load_seed("patchcore", seed)}
    out["patchcore"]["per_seed_per_category_auroc"] = {
        seed: repro_results["patchcore"][seed]["per_category"] for seed in SEEDS}
    identical_pairs = {}
    for cat in CATEGORIES:
        s0 = {k: v for k, v in pc_by_seed[0].items() if k.startswith(f"{cat}_test_")}
        for seed in SEEDS[1:]:
            s_n = {k: v for k, v in pc_by_seed[seed].items() if k.startswith(f"{cat}_test_")}
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_io.to_jsonable(out), indent=2))
    log(f"  wrote {out_path}  (patchcore bit-identical pairs: {n_identical}/{len(identical_pairs)})")
    return out


# --------------------------------------------------------------------------- #
# 3. G1(+G2 primary) gate calibration, R=20 repeats, per (backbone, seed)
# --------------------------------------------------------------------------- #
def run_gate_calibration(backbone_name):
    log(f"Stage 3: gate calibration ({backbone_name}, R={N_REPEATS}, primary protocol)")
    per_seed_results = {}
    for seed in SEEDS:
        t0 = time.time()
        scores = load_seed(backbone_name, seed)
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
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(_io.to_jsonable(per_seed_results[seed]), indent=2))
        log(f"  seed {seed}: k1_tripped={k1['k1_tripped']} ({k1['n_violations']}/{k1['n_cells']}) "
            f"k2_tripped={k2['k2_tripped']} ({k2['n_vacuous_categories']}/{k2['n_categories']}) "
            f"[{time.time()-t0:.1f}s]")
    return per_seed_results


# --------------------------------------------------------------------------- #
# 4. Exploratory per-cell audit (fixed, tuned; no B3 -- no train-good data),
#    repeat-0 halves, per (backbone, seed, category)
# --------------------------------------------------------------------------- #
def run_audit_pass(backbone_name):
    log(f"Stage 4: exploratory per-cell audit ({backbone_name}, n_perm={N_PERM})")
    per_seed_results = {}
    for seed in SEEDS:
        t0 = time.time()
        scores = load_seed(backbone_name, seed)
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
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(_io.to_jsonable(per_cat), indent=2))
        log(f"  seed {seed} done [{time.time()-t0:.1f}s]")
    return per_seed_results


# --------------------------------------------------------------------------- #
def main():
    repro = run_reproduction()
    seed_stab = run_seed_stability(repro)

    pc_gate = run_gate_calibration("patchcore")
    dm_gate = run_gate_calibration("dinomaly")

    pc_audit = run_audit_pass("patchcore")
    dm_audit = run_audit_pass("dinomaly")

    log("Cross-check: certifiability floors invariant across seeds (within backbone)")
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
