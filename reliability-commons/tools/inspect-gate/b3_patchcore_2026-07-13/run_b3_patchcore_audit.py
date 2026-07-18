"""B3 (train-good quantile) post-hoc completion of the C2 confirmatory
family's FEASIBLE half, for PatchCore x 5 seeds (M1 repair).

WHY THIS EXISTS
---------------
The frozen 2026-07-13 C2 pass ran the 4-member family {fixed, tuned} x
{patchcore, dinomaly} and SKIPPED B3/quantile because that pass loaded no
train-good records (ig_scores_full carries test scores only).  The prereg
names the full family as 6 = {fixed, tuned, quantile} x {patchcore,
dinomaly}; B3 was preregistered as degrading out when no held-out
train-good pool is loaded (PREREG s4).

A held-out train-good pool DOES exist for PatchCore -- the 2026-07-10
holdout run (ig_scores_holdout/scores_patchcore_<cat>_seed<n>.jsonl)
re-scored every MVTec test image AND scored the per-category train-good
images in one inference pass.  So B3-PatchCore is FEASIBLE and is completed
here, post-hoc.  B3-Dinomaly remains impossible: the Dinomaly branch has no
train-side score dump at all.

FROZEN-VS-AUTHORED
------------------
* The frozen 4-member per-seed Holm verdict (c2_tier2_2026-07-13) stays THE
  confirmatory result.  This B3-PatchCore arm is reported POST-HOC; it is
  NOT re-labelled confirmatory and does not alter the frozen verdict.
* The per-(practice) audit construction is identical to the frozen C2
  machinery: pooled-category excess-AURC vs the analytic random-deferral
  null, matched-abstention permutation p (n_perm=2000, strata=category),
  category-blocked bootstrap CI, deferral band matched to the conformal
  gate's realized pooled rate.

SUBSTRATE CHOICE (stated once, no tuning; the ONE authored knob)
----------------------------------------------------------------
B3's threshold is the per-category 0.95-quantile of train-good scores; the
audit then applies that threshold to the EVAL (test) scores.  Train-good
scores exist ONLY in the holdout inference run, and that run's test scores
differ slightly from ig_scores_full's (the frozen C2 source): the holdout
run scores the same test images ~0.011 lower on average (a separate
inference pass of the same frozen checkpoints).  To keep B3 free of any
cross-run score-scale artifact, this run computes ALL THREE practices
(fixed, tuned, quantile) end-to-end ON THE HOLDOUT RUN -- train-good and
eval-test share one inference pass.  The frozen fixed/tuned numbers (on
ig_scores_full) remain the confirmatory anchor; the holdout-run fixed/tuned
here are an in-run reference so B3 sits beside siblings on identical
substrate.  A cross-run sensitivity arm (B3 threshold from the holdout
train-good, eval on the ig_scores_full test half -- exactly the frozen eval
half) is also computed to show the B3 verdict does not depend on the
substrate choice.
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
B3_QUANTILE = 0.95
PRACTICES = ["fixed", "tuned", "quantile"]  # full 3-practice roster (B3 feasible here)

MVTEC_CATS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]

HOLDOUT = IG_ROOT / "holdout_results_2026-07-10" / "pulled_final" / "root" / "autodl-tmp" / "ig_scores_holdout"
FROZEN_FULL = IG_ROOT / "analysis_2026-07-10" / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"


def load_holdout(seed):
    """All holdout records for PatchCore at this seed, pooled over categories."""
    recs = []
    for cat in MVTEC_CATS:
        recs.extend(_io.load_scores(str(HOLDOUT / f"scores_patchcore_{cat}_seed{seed}.jsonl")))
    return recs


def load_frozen_full_test(seed):
    recs = []
    for cat in MVTEC_CATS:
        recs.extend(_io.load_scores(str(FROZEN_FULL / f"scores_patchcore_{cat}_seed{seed}.jsonl")))
    return [r for r in recs if r["split"] == "test"]


def audit_one(seed, eval_source):
    """Run the frozen audit machinery for ALL THREE practices on ONE seed.

    eval_source: 'holdout' (self-consistent primary) or 'frozen_full'
    (cross-run sensitivity: B3 threshold from holdout train-good, eval on
    the ig_scores_full test half).  cal/eval split, gate calibration, and
    the gate-matched deferral target all come from `eval_source`.
    """
    hold = load_holdout(seed)
    train_good = [r for r in hold if r["split"] == "train" and r["label"] == "good"]

    if eval_source == "holdout":
        test = [r for r in hold if r["split"] == "test"]
    elif eval_source == "frozen_full":
        test = load_frozen_full_test(seed)
    else:
        raise ValueError(eval_source)

    cal0, ev0 = _splits.stratified_cal_eval_split(test, repeat_seed=0)
    gate = _gate.calibrate_gate(cal0, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                                mondrian="category", backbone="patchcore", seed=0)
    routed = _gate.route_gate(gate, ev0)
    target_deferral = routed["n_defer"] / routed["n"] if routed["n"] else 0.0

    res = _audit.run_audit(
        cal0, ev0, train_good, target_deferral_rate=target_deferral,
        practices=PRACTICES, backbone="patchcore", b3_quantile=B3_QUANTILE,
        n_perm=N_PERM, alpha=AUDIT_ALPHA, seed=seed,
    )
    out = {"seed": seed, "eval_source": eval_source,
           "target_deferral_rate": target_deferral, "n_eval": len(ev0),
           "n_train_good": len(train_good), "skipped": res["skipped"],
           "practices": {}}
    for r in res["results"]:
        out["practices"][r["practice"]] = {
            "excess_aurc": r["excess_aurc"],
            "excess_aurc_ci": r["excess_aurc_ci"],
            "aurc_method": r["aurc_method"],
            "aurc_random": r["aurc_random"],
            "p_value": r["p_value"],
            "p_holm_in_3family": r.get("p_holm"),
            "reject_holm_in_3family": r.get("reject_holm"),
            "abstention_fraction": r["abstention_fraction"],
            "band_width": r["band_width"],
            "n": r["n"],
        }
    return out


def summarize_b3(per_seed):
    """Cross-seed rollup of the B3/quantile arm using the SAME reductions as
    the frozen C2 pass (seed-max primary, seed-min/median reported)."""
    ps = [per_seed[s]["practices"]["quantile"]["p_value"] for s in SEEDS]
    excess = [per_seed[s]["practices"]["quantile"]["excess_aurc"] for s in SEEDS]
    cis = [per_seed[s]["practices"]["quantile"]["excess_aurc_ci"] for s in SEEDS]
    return {
        "per_seed_p": ps,
        "per_seed_excess_aurc": excess,
        "per_seed_excess_ci": cis,
        "seed_max_p": float(np.max(ps)),
        "seed_min_p": float(np.min(ps)),
        "seed_median_p": float(np.median(ps)),
        "all_ci_exclude_zero": all(lo > 0 for lo, hi in cis),
        "excess_aurc_range": [float(min(excess)), float(max(excess))],
    }


def combined_holm_with_frozen(per_seed_holdout, frozen_mvtec_path):
    """Post-hoc: add B3-PatchCore to the frozen 4-member per-seed family to
    form a 5-member family, using the frozen 4 members' own p-values (from
    c2_mvtec.json) and B3-PatchCore's holdout-run p-value.  Reported ONLY to
    show the 4-member confirmatory verdict is unchanged by the extra member;
    the substrates differ (frozen 4 on ig_scores_full, B3 on holdout), so
    this is a robustness readout, NOT a new confirmatory family."""
    frozen = json.loads(Path(frozen_mvtec_path).read_text())
    fam4 = frozen["family"]  # e.g. ['patchcore:fixed', ...]
    out = {}
    for seed in SEEDS:
        p4 = frozen["per_seed_holm_CONFIRMATORY"][str(seed)]["p_raw"]
        p_b3 = per_seed_holdout[seed]["practices"]["quantile"]["p_value"]
        pvals = list(p4) + [p_b3]
        members = list(fam4) + ["patchcore:quantile(B3,post-hoc)"]
        holm = _multiplicity.holm_bonferroni(pvals, alpha=AUDIT_ALPHA)
        out[seed] = {
            "members": members,
            "p_raw": pvals,
            "p_holm": [float(x) for x in holm["adjusted_p"]],
            "reject_holm": [bool(x) for x in holm["reject"]],
            "family_size": len(members),
        }
    return out


def main():
    outdir = IG_ROOT / "b3_patchcore_2026-07-13"
    outdir.mkdir(exist_ok=True)

    print("===== B3-PatchCore PRIMARY (self-consistent, holdout run) =====", flush=True)
    primary = {}
    for seed in SEEDS:
        primary[seed] = audit_one(seed, "holdout")
        pc = primary[seed]["practices"]
        print(f"  seed{seed} target_defer={primary[seed]['target_deferral_rate']:.3f} "
              f"n_eval={primary[seed]['n_eval']} n_train_good={primary[seed]['n_train_good']}",
              flush=True)
        for prac in PRACTICES:
            if prac in pc:
                print(f"    {prac:9s}: excess={pc[prac]['excess_aurc']:.6f} "
                      f"ci={[round(x,5) for x in pc[prac]['excess_aurc_ci']]} "
                      f"p={pc[prac]['p_value']:.5f}", flush=True)

    print("\n===== B3-PatchCore SENSITIVITY (cross-run: eval on ig_scores_full) =====", flush=True)
    sensitivity = {}
    for seed in SEEDS:
        sensitivity[seed] = audit_one(seed, "frozen_full")
        pc = sensitivity[seed]["practices"]
        if "quantile" in pc:
            print(f"  seed{seed} quantile: excess={pc['quantile']['excess_aurc']:.6f} "
                  f"ci={[round(x,5) for x in pc['quantile']['excess_aurc_ci']]} "
                  f"p={pc['quantile']['p_value']:.5f}", flush=True)

    b3_primary_summary = summarize_b3(primary)
    b3_sensitivity_summary = summarize_b3(sensitivity)
    combined = combined_holm_with_frozen(
        primary, IG_ROOT / "c2_tier2_2026-07-13" / "c2_mvtec.json")

    result = {
        "what": "B3 (train-good quantile) post-hoc completion of the C2 family's feasible half, PatchCore x 5 seeds",
        "label": "POST-HOC (exploratory completion). Frozen 4-member per-seed Holm verdict "
                 "(c2_tier2_2026-07-13) remains THE confirmatory result; B3-Dinomaly impossible "
                 "(no train-side score dump).",
        "b3_quantile": B3_QUANTILE,
        "n_perm": N_PERM,
        "audit_alpha": AUDIT_ALPHA,
        "alpha_miss": ALPHA_MISS,
        "alpha_fr": ALPHA_FR,
        "primary_substrate": "holdout run (train-good + eval-test share one inference pass; self-consistent)",
        "sensitivity_substrate": "cross-run (B3 threshold from holdout train-good; eval on ig_scores_full, the frozen eval half)",
        "per_seed_primary": {str(s): primary[s] for s in SEEDS},
        "per_seed_sensitivity": {str(s): sensitivity[s] for s in SEEDS},
        "b3_primary_summary": b3_primary_summary,
        "b3_sensitivity_summary": b3_sensitivity_summary,
        "combined_5member_holm_with_frozen4_POSTHOC": {str(s): combined[s] for s in SEEDS},
    }
    (outdir / "results.json").write_text(json.dumps(result, indent=2))
    print("\nWROTE b3_patchcore_2026-07-13/results.json", flush=True)
    print(f"\nB3 primary seed-max p = {b3_primary_summary['seed_max_p']:.5f}; "
          f"excess-AURC range {b3_primary_summary['excess_aurc_range']}; "
          f"all CIs exclude 0: {b3_primary_summary['all_ci_exclude_zero']}", flush=True)


if __name__ == "__main__":
    main()
