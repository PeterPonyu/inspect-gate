"""C2 pooled cross-category / cross-seed confirmatory audit verdict.

WHAT IS FROZEN (implemented verbatim; confirmatory-grade)
---------------------------------------------------------
Per PREREG-DRAFT-2026-07-10 §7 step 7, §5 D5, and design 01-APP-mvtec-triage
§3.5, the confirmatory C2 test PER (practice, backbone) is:
  * B1/B2 fit on the POOLED 15-category calibration half (D5: "B1 must be
    tuned on the pooled 15-category calibration half"),
  * excess-AURC vs the analytic random-deferral null (relmetrics.aurc,
    closed form, never Monte-Carlo'd),
  * matched-abstention permutation p-value, n_perm=2000, strata=category,
    on the POOLED eval half (design §3.5 "computed within category" ==
    stratified permutation over pooled records),
  * category-blocked bootstrap CI on the pooled excess-AURC,
  * deferral band matched to the conformal gate's REALIZED pooled rate.
Family = {fixed, tuned} x {patchcore, dinomaly}.  B3/quantile is SKIPPED --
no held-out train-good pool exists (canonical dumps carry test scores only),
which PREREG §4 preregisters explicitly as the family degradation
3 practices -> 2 practices, so |family| = 2 x 2 = 4.  Holm alpha = 0.05.
This 4-member Holm-corrected verdict, computed PER SEED, is the frozen
confirmatory construction.

WHAT IS AUTHORED POST-FREEZE (one-shot; NOT confirmatory-grade)
---------------------------------------------------------------
The frozen family names NO seed dimension (it is {practice x backbone} = 4;
Stage D of run_main_grid.sh that would combine seeds is an unfilled TODO).
The rule to reduce the 5 backbone seeds (0-4) to one confirmatory verdict is
GENUINELY UNWRITTEN.  Choices, stated explicitly, made ONCE, no tuning:
  (S1) split repeat: the audit's 50/50 cal/eval split uses repeat_seed=0,
       mirroring the shipped Stage-4 exploratory audit's own choice (the
       only frozen precedent).  Not independently pinned in prereg text.
  (S2) seed reduction: the confirmatory p-value for each (practice,backbone)
       is the SEED-MAX (least-significant seed) of the 5 per-seed pooled
       permutation p-values -- i.e. a rejection is required to survive in
       the WORST seed.  Rationale: the design treats the 5 backbone seeds as
       a robustness dimension (design §3.3), not a family dimension, and the
       paper's own A1/D8 stance forbids pooling correlated resamples (here:
       the 5 seeds share the test images), so pooling seed-records is barred;
       max-p is the simplest conservative "effect is present in every seed"
       reduction.  min-p and median-p are also reported so the reader sees
       whether the verdict depends on this choice at all.
Per-cell (per-category, per-seed) results were ALREADY KNOWN when this
reduction rule was written; therefore the cross-seed verdict is labelled
one-shot, NOT confirmatory-grade.  The per-seed 4-member Holm verdict IS
confirmatory-grade on its own terms.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

IG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons root
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import audit as _audit
from inspect_gate import gate as _gate
from inspect_gate import splits as _splits
from inspect_gate import io as _io
from relmetrics import multiplicity as _multiplicity

SEEDS = [0, 1, 2, 3, 4]
N_PERM = 2000
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
AUDIT_ALPHA = 0.05
PRACTICES = ["fixed", "tuned"]  # B3 skipped: no train-good pool (PREREG §4 degradation)

MVTEC_PC = IG_ROOT / "analysis_2026-07-10" / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"
MVTEC_DM = IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
VISA_CANON = IG_ROOT / "visa_results_2026-07-12" / "canonical"

MVTEC_CATS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]


def load_mvtec(backbone, seed):
    if backbone == "patchcore":
        recs = []
        for cat in MVTEC_CATS:
            recs.extend(_io.load_scores(str(MVTEC_PC / f"scores_patchcore_{cat}_seed{seed}.jsonl")))
        return recs
    return _io.load_scores(str(MVTEC_DM / f"scores_dinomaly_seed{seed}.jsonl"))


def load_visa(backbone, seed):
    return _io.load_scores(str(VISA_CANON / f"scores_{backbone}_seed{seed}.jsonl"))


def pooled_audit_one(backbone, seed, loader):
    """The FROZEN confirmatory construction for ONE (backbone, seed):
    pooled-category audit of {fixed, tuned}. Returns raw per-practice
    p-values / effect sizes (no Holm here -- Holm is applied later across
    the realized 4-member family)."""
    scores = loader(backbone, seed)
    test = [r for r in scores if r["split"] == "test"]
    cal0, ev0 = _splits.stratified_cal_eval_split(test, repeat_seed=0)
    # realized pooled deferral rate of the actual conformal gate
    gate = _gate.calibrate_gate(cal0, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                                mondrian="category", backbone=backbone, seed=0)
    routed = _gate.route_gate(gate, ev0)
    target_deferral = routed["n_defer"] / routed["n"] if routed["n"] else 0.0
    res = _audit.run_audit(
        cal0, ev0, None, target_deferral_rate=target_deferral,
        practices=PRACTICES, backbone=backbone, n_perm=N_PERM,
        alpha=AUDIT_ALPHA, seed=seed,
    )
    out = {"backbone": backbone, "seed": seed, "target_deferral_rate": target_deferral,
           "n_eval": len(ev0), "practices": {}}
    for r in res["results"]:
        out["practices"][r["practice"]] = {
            "excess_aurc": r["excess_aurc"],
            "excess_aurc_ci": r["excess_aurc_ci"],
            "aurc_method": r["aurc_method"],
            "aurc_random": r["aurc_random"],
            "p_value": r["p_value"],
            "abstention_fraction": r["abstention_fraction"],
            "band_width": r["band_width"],
            "n": r["n"],
        }
    return out


def run_benchmark(name, loader, cats_note):
    print(f"\n===== {name} pooled confirmatory audit =====", flush=True)
    per_seed = {}
    for backbone in ("patchcore", "dinomaly"):
        for seed in SEEDS:
            key = f"{backbone}_seed{seed}"
            per_seed[key] = pooled_audit_one(backbone, seed, loader)
            for prac in PRACTICES:
                pc = per_seed[key]["practices"][prac]
                print(f"  {backbone} seed{seed} {prac}: excess={pc['excess_aurc']:.6f} "
                      f"ci={[round(x,5) for x in pc['excess_aurc_ci']]} p={pc['p_value']:.5f}",
                      flush=True)

    # ----- per-seed frozen 4-member Holm verdict -----
    family = [(b, p) for b in ("patchcore", "dinomaly") for p in PRACTICES]  # 4 members
    per_seed_holm = {}
    for seed in SEEDS:
        pvals = [per_seed[f"{b}_seed{seed}"]["practices"][p]["p_value"] for (b, p) in family]
        holm = _multiplicity.holm_bonferroni(pvals, alpha=AUDIT_ALPHA)
        per_seed_holm[seed] = {
            "family": [f"{b}:{p}" for (b, p) in family],
            "p_raw": pvals,
            "p_holm": [float(x) for x in holm["adjusted_p"]],
            "reject_holm": [bool(x) for x in holm["reject"]],
            "family_size": len(family),
        }

    # ----- authored cross-seed reduction (max-p / min-p / median-p) -----
    reductions = {}
    for reducer_name, reducer in (("seed_max_p", np.max),
                                  ("seed_min_p", np.min),
                                  ("seed_median_p", np.median)):
        pvals_reduced = []
        detail = []
        for (b, p) in family:
            ps = [per_seed[f"{b}_seed{s}"]["practices"][p]["p_value"] for s in SEEDS]
            red = float(reducer(ps))
            pvals_reduced.append(red)
            detail.append({"member": f"{b}:{p}", "per_seed_p": ps, "reduced_p": red})
        holm = _multiplicity.holm_bonferroni(pvals_reduced, alpha=AUDIT_ALPHA)
        reductions[reducer_name] = {
            "detail": detail,
            "p_holm": [float(x) for x in holm["adjusted_p"]],
            "reject_holm": [bool(x) for x in holm["reject"]],
            "family_size": len(family),
        }

    out = {
        "benchmark": name,
        "cats_note": cats_note,
        "family": [f"{b}:{p}" for (b, p) in family],
        "family_size_frozen_rule": "3 practices x 2 backbones = 6; B3 skipped (no train-good) "
                                    "-> 2 x 2 = 4 (PREREG §4 preregistered degradation)",
        "per_seed_raw": per_seed,
        "per_seed_holm_CONFIRMATORY": per_seed_holm,
        "cross_seed_reductions_AUTHORED": reductions,
        "authored_primary_reduction": "seed_max_p",
    }
    return out


def main():
    outdir = IG_ROOT / "c2_tier2_2026-07-13"
    mv = run_benchmark("MVTec-AD", load_mvtec, "15 categories, IN-PREREG (confirmatory family)")
    (outdir / "c2_mvtec.json").write_text(json.dumps(mv, indent=2))
    va = run_benchmark("VisA", load_visa, "12 categories, POST-FREEZE exploratory (NOT confirmatory)")
    (outdir / "c2_visa.json").write_text(json.dumps(va, indent=2))
    print("\nWROTE c2_mvtec.json, c2_visa.json", flush=True)


if __name__ == "__main__":
    main()
