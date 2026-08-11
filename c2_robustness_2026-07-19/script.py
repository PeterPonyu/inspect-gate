#!/usr/bin/env python3
"""L6a + L6b — C2 robustness across all R=20 repeats, and the K4 oracle-
deferral headroom kill gate (POST-FREEZE EXPLORATORY hardening analyses).

L6a — C2 robustness
-------------------
The confirmatory C2 pooled audit (four-member per-seed Holm family
{fixed, tuned} x {patchcore, dinomaly} on MVTec, frozen in
c2_tier2_2026-07-13/) rests on the repeat-0 cal/eval split only -- an
AUTHORED (minor) choice per that analysis's own frozen-vs-authored table
("Split: audit uses the repeat-0 50/50 stratified cal/eval split ...
Not independently pinned in prereg text"). This script runs the SAME frozen
construction, byte-for-byte the same code path (splits.stratified_cal_eval_split
-> gate.calibrate_gate -> gate.route_gate -> audit.run_audit, fixed+tuned,
n_perm=2000, Holm alpha=0.05), across ALL 20 repeats of the frozen R=20
protocol (split-seed = repeat index, splits.py), and reports the per-seed
4-member Holm verdict per repeat x seed. A replication check asserts the
repeat-0 rerun reproduces the frozen c2_mvtec.json values exactly.

L6b — K4 oracle headroom
------------------------
Design 01-APP-mvtec-triage §4 K4 (preregistered in PREREG-DRAFT-2026-07-10
§7 step 8 / §7.1, never implemented -- the paper's Limitations admits this):

    "oracle-deferral excess-AURC headroom < 0.02 in >= 12/15 categories ->
    the audit cannot discriminate anything (backbone saturation); reframe
    C2 as a saturation finding"

AMBIGUITY (documented per the task brief; most literal reading implemented):
the prereg names the statistic but not its inputs. Resolved choices, stated
once, no tuning:
  (K4-a) LOSSES: the audited practice's realized 0/1 errors on the eval
         half -- the only loss vector in the confirmatory construction
         (audit.py's own _practice_predictions_and_conf, used verbatim).
         The family has two practices, so headroom is reported PER
         (practice, backbone, seed); fixed/tuned induce different loss
         vectors.
  (K4-b) SPLIT: repeat-0, mirroring the authored C2 split choice (the only
         frozen precedent).
  (K4-c) ORACLE: the error-last confidence ordering (conf = 1 - loss), the
         maximum excess-AURC ANY deferral ordering can achieve on those
         losses, computed by relmetrics.aurc.excess_aurc_gain itself. For
         0/1 losses this is EXACT and tie-order-independent (within the
         correct-prefix all losses are 0, within the error-suffix all are
         1, so the Riemann sum cannot depend on within-group order).
         Cross-checked against the closed-form continuous limit
         -(1-e) ln(1-e) for per-category error rate e.
  (K4-d) TRIP RULE (verbatim prereg): headroom < 0.02 in >= 12/15
         categories. MVTec only; VisA (12 cats) and MPDD (6 cats) carry no
         preregistered K4 semantics -- their headroom counts are reported
         EXPLORATORY-only.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np


def _portal_commons_root():
    import os
    from pathlib import Path
    for key in ("COMMONS_ROOT", "RELIABILITY_COMMONS"):
        v = os.environ.get(key)
        if v:
            p = Path(v).expanduser().resolve()
            if p.is_dir():
                return p
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        for cand in (parent / "reliability-commons", parent.parent / "reliability-commons"):
            if cand.is_dir():
                return cand
    raise RuntimeError(
        "Set COMMONS_ROOT to the reliability-commons checkout (or place it as a sibling of this repo)."
    )

def _portal_repo_root():
    from pathlib import Path
    here = Path(__file__).resolve().parent
    for p in [here, *here.parents]:
        if (p / ".git").exists() or (p / "pyproject.toml").exists() or (p / "README.md").exists():
            return p
    return here

IG_ROOT = _portal_repo_root()
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons root (relmetrics)
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import audit as _audit          # noqa: E402
from inspect_gate import baselines as _baselines  # noqa: E402
from inspect_gate import gate as _gate            # noqa: E402
from inspect_gate import io as _io                # noqa: E402
from inspect_gate import splits as _splits        # noqa: E402
from relmetrics import aurc as _aurc              # noqa: E402
from relmetrics import multiplicity as _multiplicity  # noqa: E402

SEEDS = [0, 1, 2, 3, 4]
N_REPEATS = 20
N_PERM = 2000
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
AUDIT_ALPHA = 0.05
PRACTICES = ["fixed", "tuned"]
K4_HEADROOM_MIN = 0.02
K4_TRIP_COUNT = 12  # >= 12/15 categories below headroom -> K4 trips

MVTEC_PC = IG_ROOT / "analysis_2026-07-10" / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"
MVTEC_DM = IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
VISA_CANON = IG_ROOT / "visa_results_2026-07-12" / "canonical"
MPDD_CANON = IG_ROOT / "mpdd_results_2026-07-13" / "canonical"
FROZEN_C2 = IG_ROOT / "c2_tier2_2026-07-13" / "c2_mvtec.json"

MVTEC_CATS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]


def load_mvtec(backbone: str, seed: int):
    if backbone == "patchcore":
        recs = []
        for cat in MVTEC_CATS:
            recs.extend(_io.load_scores(str(MVTEC_PC / f"scores_patchcore_{cat}_seed{seed}.jsonl")))
        return recs
    return _io.load_scores(str(MVTEC_DM / f"scores_dinomaly_seed{seed}.jsonl"))


def load_canonical(canon_dir: Path, backbone: str, seed: int):
    return _io.load_scores(str(canon_dir / f"scores_{backbone}_seed{seed}.jsonl"))


# ---------------------------------------------------------------------------
# L6a
# ---------------------------------------------------------------------------

def c2_one_cell(test_records, backbone, seed, repeat):
    """The FROZEN confirmatory construction for ONE (backbone, seed, repeat):
    identical to c2_tier2_2026-07-13/run_c2_pooled_audit.py with repeat_seed
    generalized from 0 to `repeat`. Returns raw per-practice results."""
    cal, ev = _splits.stratified_cal_eval_split(test_records, repeat_seed=repeat)
    gate = _gate.calibrate_gate(cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                                mondrian="category", backbone=backbone, seed=0)
    routed = _gate.route_gate(gate, ev)
    target_deferral = routed["n_defer"] / routed["n"] if routed["n"] else 0.0
    res = _audit.run_audit(
        cal, ev, None, target_deferral_rate=target_deferral,
        practices=PRACTICES, backbone=backbone, n_perm=N_PERM,
        alpha=AUDIT_ALPHA, seed=seed,
    )
    out = {"target_deferral_rate": target_deferral, "n_eval": len(ev), "practices": {}}
    for r in res["results"]:
        out["practices"][r["practice"]] = {
            "excess_aurc": r["excess_aurc"],
            "excess_aurc_ci": r["excess_aurc_ci"],
            "p_value": r["p_value"],
            "abstention_fraction": r["abstention_fraction"],
            "band_width": r["band_width"],
        }
    return out


def run_l6a() -> dict:
    print("===== L6a: C2 across all 20 repeats (MVTec) =====", flush=True)
    family = [(b, p) for b in ("patchcore", "dinomaly") for p in PRACTICES]  # 4 members
    # raw[(backbone, seed)][repeat] = cell
    raw = {}
    for backbone in ("patchcore", "dinomaly"):
        for seed in SEEDS:
            t0 = time.time()
            test = [r for r in load_mvtec(backbone, seed) if r["split"] == "test"]
            cells = [c2_one_cell(test, backbone, seed, rep) for rep in range(N_REPEATS)]
            raw[(backbone, seed)] = cells
            print(f"  {backbone} seed{seed}: 20 repeats audited [{time.time()-t0:.1f}s]",
                  flush=True)

    # --- replication check: repeat 0 must equal the frozen c2_mvtec.json ---
    frozen = json.loads(FROZEN_C2.read_text())["per_seed_raw"]
    max_diff_excess = 0.0
    max_diff_p = 0.0
    for backbone in ("patchcore", "dinomaly"):
        for seed in SEEDS:
            fz = frozen[f"{backbone}_seed{seed}"]["practices"]
            mine = raw[(backbone, seed)][0]["practices"]
            for prac in PRACTICES:
                max_diff_excess = max(max_diff_excess,
                                      abs(fz[prac]["excess_aurc"] - mine[prac]["excess_aurc"]))
                max_diff_p = max(max_diff_p, abs(fz[prac]["p_value"] - mine[prac]["p_value"]))
    replication = {"max_abs_diff_excess_aurc": max_diff_excess,
                   "max_abs_diff_p_value": max_diff_p,
                   "repeat0_reproduces_frozen": bool(max_diff_excess < 1e-12 and max_diff_p < 1e-12)}
    print(f"  replication check: max|dExcess|={max_diff_excess:.3e} "
          f"max|dp|={max_diff_p:.3e} -> {replication['repeat0_reproduces_frozen']}", flush=True)

    # --- per (repeat, seed) frozen 4-member Holm verdict ---
    per_repeat_seed = {}
    for rep in range(N_REPEATS):
        for seed in SEEDS:
            pvals = [raw[(b, seed)][rep]["practices"][p]["p_value"] for (b, p) in family]
            holm = _multiplicity.holm_bonferroni(pvals, alpha=AUDIT_ALPHA)
            per_repeat_seed[f"repeat{rep}_seed{seed}"] = {
                "family": [f"{b}:{p}" for (b, p) in family],
                "p_raw": pvals,
                "p_holm": [float(x) for x in holm["adjusted_p"]],
                "reject_holm": [bool(x) for x in holm["reject"]],
                "all4_reject": bool(all(holm["reject"])),
                "excess_aurc": [raw[(b, seed)][rep]["practices"][p]["excess_aurc"]
                                for (b, p) in family],
                "target_deferral_rate": {
                    b: raw[(b, seed)][rep]["target_deferral_rate"]
                    for b in ("patchcore", "dinomaly")
                },
            }

    # --- per repeat: does the confirmatory verdict hold in ALL 5 seeds? ---
    per_repeat = {}
    for rep in range(N_REPEATS):
        seeds_all4 = {s: per_repeat_seed[f"repeat{rep}_seed{s}"]["all4_reject"] for s in SEEDS}
        # authored cross-seed reduction (seed-max-p), mirroring the frozen analysis
        pvals_reduced = []
        for (b, p) in family:
            ps = [raw[(b, s)][rep]["practices"][p]["p_value"] for s in SEEDS]
            pvals_reduced.append(float(np.max(ps)))
        holm = _multiplicity.holm_bonferroni(pvals_reduced, alpha=AUDIT_ALPHA)
        per_repeat[f"repeat{rep}"] = {
            "all4_reject_per_seed": seeds_all4,
            "verdict_all_5_seeds_reject": bool(all(seeds_all4.values())),
            "seed_max_p": pvals_reduced,
            "seed_max_p_holm": [float(x) for x in holm["adjusted_p"]],
            "seed_max_p_reject_holm": [bool(x) for x in holm["reject"]],
            "min_excess_aurc_over_family_seeds": float(min(
                raw[(b, s)][rep]["practices"][p]["excess_aurc"]
                for (b, p) in family for s in SEEDS)),
        }

    n_holds = sum(1 for v in per_repeat.values() if v["verdict_all_5_seeds_reject"])
    flips = [k for k, v in per_repeat.items() if not v["verdict_all_5_seeds_reject"]]
    # per-member worst case across everything
    member_worst = {}
    for (b, p) in family:
        ps = [raw[(b, s)][rep]["practices"][p]["p_value"] for s in SEEDS for rep in range(N_REPEATS)]
        es = [raw[(b, s)][rep]["practices"][p]["excess_aurc"] for s in SEEDS for rep in range(N_REPEATS)]
        member_worst[f"{b}:{p}"] = {"max_p_over_repeats_seeds": float(max(ps)),
                                    "min_excess_aurc_over_repeats_seeds": float(min(es))}
    summary = {
        "n_repeats": N_REPEATS,
        "n_repeats_verdict_holds_all5seeds": n_holds,
        "repeats_where_verdict_flips": flips,
        "n_seed_max_p_reject_holm_all4": sum(
            1 for v in per_repeat.values() if all(v["seed_max_p_reject_holm"])),
        "member_worst_case": member_worst,
        "global_min_excess_aurc": float(min(v["min_excess_aurc_over_family_seeds"]
                                            for v in per_repeat.values())),
    }
    print(f"  VERDICT: stable in {n_holds}/{N_REPEATS} repeats; flips: {flips}", flush=True)
    return {"replication_check": replication, "per_repeat_seed": per_repeat_seed,
            "per_repeat": per_repeat, "summary": summary}


# ---------------------------------------------------------------------------
# L6b (K4)
# ---------------------------------------------------------------------------

def k4_one_cell(test_records, backbone, seed, practice):
    """Per-category oracle-deferral excess-AURC headroom for ONE
    (backbone, seed, practice) on the repeat-0 split. The practice's losses
    are constructed by audit.py's own helper (verbatim audit semantics)."""
    cal, ev = _splits.stratified_cal_eval_split(test_records, repeat_seed=0)
    if practice == "fixed":
        baseline = _baselines.fit_b1_global_threshold(cal)
    else:
        baseline = _baselines.fit_b2_per_category_threshold(cal)
    losses, conf = _audit._practice_predictions_and_conf(ev, baseline)
    finite = np.isfinite(conf)
    losses = losses[finite]
    cats = np.array([r["category"] for r in ev])[finite]
    per_category = {}
    for cat in sorted(set(cats.tolist())):
        l = losses[cats == cat]
        e = float(l.mean())
        oracle_conf = 1.0 - l  # errors accepted LAST; exact for 0/1 losses
        headroom = _aurc.excess_aurc_gain(l, oracle_conf)
        closed_form = -(1.0 - e) * math.log(1.0 - e) if e < 1.0 else 0.0
        per_category[cat] = {
            "n_eval": int(l.size),
            "error_rate": e,
            "oracle_headroom": float(headroom),
            "closed_form_check": float(closed_form),
            "headroom_ge_0.02": bool(headroom >= K4_HEADROOM_MIN),
        }
    return per_category


def run_k4_benchmark(name, loader, n_categories_expected):
    out = {}
    for backbone in ("patchcore", "dinomaly"):
        for practice in PRACTICES:
            per_seed = {}
            for seed in SEEDS:
                test = [r for r in loader(backbone, seed) if r["split"] == "test"]
                pc = k4_one_cell(test, backbone, seed, practice)
                n_ge = sum(1 for v in pc.values() if v["headroom_ge_0.02"])
                per_seed[str(seed)] = {
                    "per_category": pc,
                    "n_categories": len(pc),
                    "n_headroom_ge_0.02": n_ge,
                    "n_below": len(pc) - n_ge,
                }
            counts = [per_seed[str(s)]["n_headroom_ge_0.02"] for s in SEEDS]
            out[f"{backbone}:{practice}"] = {
                "per_seed": per_seed,
                "n_headroom_ge_0.02_across_seeds": counts,
                "min_n_ge": min(counts),
                "max_n_ge": max(counts),
            }
    return out


def run_l6b() -> dict:
    print("===== L6b: K4 oracle-deferral headroom =====", flush=True)
    benchmarks = {}
    for name, loader, ncats in (
        ("MVTec-AD", load_mvtec, 15),
        ("VisA", lambda b, s: load_canonical(VISA_CANON, b, s), 12),
        ("MPDD", lambda b, s: load_canonical(MPDD_CANON, b, s), 6),
    ):
        benchmarks[name] = run_k4_benchmark(name, loader, ncats)
        print(f"  {name} done", flush=True)

    # MVTec K4 verdict per prereg (verbatim rule: < 0.02 in >= 12/15 -> trip)
    mvtec_verdict = {}
    for cell, block in benchmarks["MVTec-AD"].items():
        trips_per_seed = {s: (ps["n_below"] >= K4_TRIP_COUNT)
                          for s, ps in block["per_seed"].items()}
        mvtec_verdict[cell] = {
            "k4_trips_per_seed": trips_per_seed,
            "k4_trips_all_seeds": bool(all(trips_per_seed.values())),
            "k4_trips_any_seed": bool(any(trips_per_seed.values())),
        }
    return {
        "spec": {
            "statistic": "oracle-deferral excess-AURC headroom per category "
                         "(max excess-AURC achievable by ANY deferral ordering on the "
                         "practice's realized eval-half 0/1 losses; error-last ordering, "
                         "exact for 0/1 losses)",
            "trip_rule": "headroom < 0.02 in >= 12/15 categories -> K4 trips "
                         "(design 01-APP-mvtec-triage SS4 K4; PREREG SS7 step 8 / SS7.1)",
            "ambiguities_resolved": {
                "losses": "audited practice's realized eval-half errors (audit.py "
                          "_practice_predictions_and_conf verbatim), per (practice, backbone)",
                "split": "repeat-0 (mirrors the authored C2 split choice)",
                "oracle": "conf = 1 - loss via relmetrics.aurc.excess_aurc_gain; "
                          "cross-checked vs closed form -(1-e)ln(1-e)",
                "scope": "MVTec trip semantics only; VisA/MPDD exploratory counts",
            },
        },
        "benchmarks": benchmarks,
        "mvtec_k4_verdict": mvtec_verdict,
    }


def main() -> None:
    out_dir = IG_ROOT / "c2_robustness_2026-07-19"
    l6a = run_l6a()
    l6b = run_l6b()
    result = {
        "analysis": "L6a C2 robustness across R=20 repeats + L6b K4 oracle headroom "
                    "(POST-FREEZE EXPLORATORY hardening)",
        "date": "2026-07-19",
        "l6a_c2_robustness": l6a,
        "l6b_k4_oracle": l6b,
    }
    (out_dir / "results.json").write_text(json.dumps(_io.to_jsonable(result), indent=2))
    print("WROTE", out_dir / "results.json", flush=True)


if __name__ == "__main__":
    main()
