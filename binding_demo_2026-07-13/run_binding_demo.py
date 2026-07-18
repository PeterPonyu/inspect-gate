"""Binding demonstration (M4, the deepest wound): where does a NAIVE fixed
threshold over-promise while the certified gate holds?

THE QUESTION (red-team MAJOR-2 / M4)
------------------------------------
"Show me ONE (backbone, category) cell where a naive fixed threshold would
actually VIOLATE the escaped-defect target alpha_miss=0.10 or the
false-reject target alpha_fr=0.05, and the calibrated gate keeps the same
realized rate within target+tolerance on the SAME eval data."  If such
cells exist, the certificate binds somewhere naive practice fails.  If not,
the paper keeps its honest "not demonstrated" framing -- this script does
NOT manufacture a violation.

CONSTRUCTION (all realized on held-out eval halves; zero new statistics)
-----------------------------------------------------------------------
Per (benchmark, backbone, backbone-seed, repeat):
  * cal, eval = repeated stratified 50/50 split (design 3.2).
  * NAIVE PRACTITIONER = B1: one global best-F1 threshold fit on the POOLED
    calibration half, applied to EVERY eval image with NO deferral
    (score >= thr -> auto-reject, else auto-pass).  Its realized rates,
    per category, on the eval half:
        escaped rate      = #(defective eval images with score <  thr) / #defective
        false-reject rate = #(good      eval images with score >= thr) / #good
    -- exactly the certify.coverage_cell definitions, but with a fixed
    global threshold and no abstention.
  * CERTIFIED GATE = calibrate_gate(pooled cal, mondrian=category), routed
    over the eval half; realized per-category escaped / false-reject rate
    via certify.coverage_cell (deferred images are NOT counted as escaped /
    false-reject -- they go to human review).  The gate pays for its
    guarantee with a disclosed deferral rate, also reported per cell.

A BINDING cell (per the two axes, tier-1 style = mean over R=20 repeats):
  * escaped-axis:  B1 mean escaped rate  >  alpha_miss (0.10)
                   AND gate mean escaped rate <= alpha_miss + tol (0.13)
  * false-reject-axis: B1 mean FR rate   >  alpha_fr  (0.05)
                   AND gate mean FR rate      <= alpha_fr  + tol (0.08)
tol = 0.03 (certify.v1_pass_tier1 default).  Cells are additionally tagged
with the gate's per-axis certification (g1/g2): a CERTIFIED binding cell is
the strongest evidence (the gate makes an explicit claim there and holds).
The repeat-0 single split (the C2/B3 audit's split) is reported too.

LABEL: POST-HOC / EXPLORATORY.  This is not a preregistered confirmatory
arm; it is the M4 illustration the red-team asked for, reported honestly
whichever way it comes out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

IG_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(IG_ROOT.parent.parent))
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import baselines as _baselines
from inspect_gate import certify as _certify
from inspect_gate import gate as _gate
from inspect_gate import splits as _splits
from inspect_gate import io as _io

SEEDS = [0, 1, 2, 3, 4]
N_REPEATS = 20
ALPHA_MISS = 0.10
ALPHA_FR = 0.05
TOL = 0.03  # certify.v1_pass_tier1 default tolerance_pp

MVTEC_CATS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
              "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]

MVTEC_PC = IG_ROOT / "analysis_2026-07-10" / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"
MVTEC_DM = IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
VISA_CANON = IG_ROOT / "visa_results_2026-07-12" / "canonical"


def load_mvtec(backbone, seed):
    if backbone == "patchcore":
        recs = []
        for cat in MVTEC_CATS:
            recs.extend(_io.load_scores(str(MVTEC_PC / f"scores_patchcore_{cat}_seed{seed}.jsonl")))
        return recs
    return _io.load_scores(str(MVTEC_DM / f"scores_dinomaly_seed{seed}.jsonl"))


def load_visa(backbone, seed):
    return _io.load_scores(str(VISA_CANON / f"scores_{backbone}_seed{seed}.jsonl"))


def b1_rates_for_cat(eval_cat, thr):
    """B1 (fixed global threshold, no deferral) realized escaped/FR rates
    for one category's eval subset."""
    defects = [r for r in eval_cat if r["label"] == "defect"]
    goods = [r for r in eval_cat if r["label"] == "good"]
    n_def, n_good = len(defects), len(goods)
    n_escaped = sum(1 for r in defects if r["score"] < thr)   # predicted good -> escaped
    n_fr = sum(1 for r in goods if r["score"] >= thr)         # predicted defect -> false-reject
    return {
        "n_eval_def": n_def, "n_eval_good": n_good,
        "escaped_defect_rate": (n_escaped / n_def) if n_def else float("nan"),
        "false_reject_rate": (n_fr / n_good) if n_good else float("nan"),
    }


def one_repeat(test, backbone, repeat_seed, cats):
    """Return per-category B1 vs gate realized rates for one cal/eval split."""
    cal, ev = _splits.stratified_cal_eval_split(test, repeat_seed=repeat_seed)
    b1 = _baselines.fit_b1_global_threshold(cal)
    thr = b1["threshold"]
    gate = _gate.calibrate_gate(cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                                mondrian="category", backbone=backbone, seed=0)
    routed = _gate.route_gate(gate, ev)
    dec_by_id = {d["image_id"]: d for d in routed["decisions"]}

    out = {}
    for cat in cats:
        ev_cat = [r for r in ev if r["category"] == cat]
        if not ev_cat:
            continue
        b1r = b1_rates_for_cat(ev_cat, thr)
        dec_cat = [dec_by_id[r["image_id"]] for r in ev_cat]
        gcell = _certify.coverage_cell(ev_cat, dec_cat)
        strat = gate["strata"].get(cat, {})
        out[cat] = {
            "b1_escaped": b1r["escaped_defect_rate"],
            "b1_fr": b1r["false_reject_rate"],
            "gate_escaped": gcell["escaped_defect_rate"],
            "gate_fr": gcell["false_reject_rate"],
            "gate_deferral": gcell["deferral_rate"],
            "n_eval_def": gcell["n_eval_def"],
            "n_eval_good": gcell["n_eval_good"],
            "g1_certified": bool(strat.get("g1_certified", False)),
            "g2_certified": bool(strat.get("g2_certified", False)),
        }
    return out, thr


def aggregate(name, loader, cats):
    print(f"\n===== {name} =====", flush=True)
    per = {}  # per[(backbone, seed)] = {repeat: {cat: rates}, thr0}
    for backbone in ("patchcore", "dinomaly"):
        for seed in SEEDS:
            test = [r for r in loader(backbone, seed) if r["split"] == "test"]
            repeats = {}
            for rep in range(N_REPEATS):
                cell, thr = one_repeat(test, backbone, rep, cats)
                repeats[rep] = cell
            per[(backbone, seed)] = repeats

    # aggregate to per (backbone, category), mean over R=20 repeats at seed 0
    # (tier-1 grades per backbone-seed; seed 0 is the canonical audit seed),
    # plus stability across the 5 backbone seeds.
    results = {}
    for backbone in ("patchcore", "dinomaly"):
        for cat in cats:
            # seed-0, R=20 repeats
            rr = per[(backbone, 0)]
            b1_esc = [rr[rep][cat]["b1_escaped"] for rep in range(N_REPEATS) if cat in rr[rep]]
            b1_fr = [rr[rep][cat]["b1_fr"] for rep in range(N_REPEATS) if cat in rr[rep]]
            g_esc = [rr[rep][cat]["gate_escaped"] for rep in range(N_REPEATS) if cat in rr[rep]]
            g_fr = [rr[rep][cat]["gate_fr"] for rep in range(N_REPEATS) if cat in rr[rep]]
            g_def = [rr[rep][cat]["gate_deferral"] for rep in range(N_REPEATS) if cat in rr[rep]]
            g1c = [rr[rep][cat]["g1_certified"] for rep in range(N_REPEATS) if cat in rr[rep]]
            g2c = [rr[rep][cat]["g2_certified"] for rep in range(N_REPEATS) if cat in rr[rep]]
            if not b1_esc:
                continue

            def m(x):
                x = [v for v in x if not (isinstance(v, float) and np.isnan(v))]
                return float(np.mean(x)) if x else float("nan")

            def rng(x):
                x = [v for v in x if not (isinstance(v, float) and np.isnan(v))]
                return [float(min(x)), float(max(x))] if x else [float("nan"), float("nan")]

            # cross-seed mean (mean over R=20 repeats within each seed, then over seeds)
            b1_esc_seeds, g_esc_seeds, b1_fr_seeds, g_fr_seeds = [], [], [], []
            for s in SEEDS:
                rs = per[(backbone, s)]
                be = m([rs[rep][cat]["b1_escaped"] for rep in range(N_REPEATS) if cat in rs[rep]])
                ge = m([rs[rep][cat]["gate_escaped"] for rep in range(N_REPEATS) if cat in rs[rep]])
                bf = m([rs[rep][cat]["b1_fr"] for rep in range(N_REPEATS) if cat in rs[rep]])
                gf = m([rs[rep][cat]["gate_fr"] for rep in range(N_REPEATS) if cat in rs[rep]])
                b1_esc_seeds.append(be); g_esc_seeds.append(ge)
                b1_fr_seeds.append(bf); g_fr_seeds.append(gf)

            rep0 = per[(backbone, 0)][0].get(cat, {})
            key = f"{backbone}:{cat}"
            results[key] = {
                "backbone": backbone, "category": cat,
                "n_eval_def_seed0_rep0": rep0.get("n_eval_def"),
                "n_eval_good_seed0_rep0": rep0.get("n_eval_good"),
                # seed-0 mean over R=20 repeats (tier-1 style)
                "b1_escaped_mean_R20": m(b1_esc), "b1_escaped_range_R20": rng(b1_esc),
                "gate_escaped_mean_R20": m(g_esc), "gate_escaped_range_R20": rng(g_esc),
                "b1_fr_mean_R20": m(b1_fr), "b1_fr_range_R20": rng(b1_fr),
                "gate_fr_mean_R20": m(g_fr), "gate_fr_range_R20": rng(g_fr),
                "gate_deferral_mean_R20": m(g_def),
                "g1_certified_frac_R20": float(np.mean(g1c)) if g1c else 0.0,
                "g2_certified_frac_R20": float(np.mean(g2c)) if g2c else 0.0,
                # repeat-0 single split
                "b1_escaped_rep0": rep0.get("b1_escaped"), "gate_escaped_rep0": rep0.get("gate_escaped"),
                "b1_fr_rep0": rep0.get("b1_fr"), "gate_fr_rep0": rep0.get("gate_fr"),
                # cross-seed means (per-seed R20 means)
                "b1_escaped_per_seed": b1_esc_seeds, "gate_escaped_per_seed": g_esc_seeds,
                "b1_fr_per_seed": b1_fr_seeds, "gate_fr_per_seed": g_fr_seeds,
            }
    return results


def classify(results):
    """Tag binding cells on each axis (seed-0 R=20 mean)."""
    esc_bind, fr_bind = [], []
    for key, c in results.items():
        # escaped axis
        if (not np.isnan(c["b1_escaped_mean_R20"]) and not np.isnan(c["gate_escaped_mean_R20"])
                and c["b1_escaped_mean_R20"] > ALPHA_MISS
                and c["gate_escaped_mean_R20"] <= ALPHA_MISS + TOL):
            esc_bind.append({
                "cell": key, "b1_escaped": c["b1_escaped_mean_R20"],
                "gate_escaped": c["gate_escaped_mean_R20"],
                "gate_deferral": c["gate_deferral_mean_R20"],
                "g1_certified_frac": c["g1_certified_frac_R20"],
                "cross_seed_b1_all_violate": all(x > ALPHA_MISS for x in c["b1_escaped_per_seed"] if not np.isnan(x)),
                "cross_seed_gate_all_hold": all(x <= ALPHA_MISS + TOL for x in c["gate_escaped_per_seed"] if not np.isnan(x)),
            })
        # false-reject axis
        if (not np.isnan(c["b1_fr_mean_R20"]) and not np.isnan(c["gate_fr_mean_R20"])
                and c["b1_fr_mean_R20"] > ALPHA_FR
                and c["gate_fr_mean_R20"] <= ALPHA_FR + TOL):
            fr_bind.append({
                "cell": key, "b1_fr": c["b1_fr_mean_R20"],
                "gate_fr": c["gate_fr_mean_R20"],
                "gate_deferral": c["gate_deferral_mean_R20"],
                "g2_certified_frac": c["g2_certified_frac_R20"],
                "cross_seed_b1_all_violate": all(x > ALPHA_FR for x in c["b1_fr_per_seed"] if not np.isnan(x)),
                "cross_seed_gate_all_hold": all(x <= ALPHA_FR + TOL for x in c["gate_fr_per_seed"] if not np.isnan(x)),
            })
    return esc_bind, fr_bind


def main():
    outdir = IG_ROOT / "binding_demo_2026-07-13"
    outdir.mkdir(exist_ok=True)

    mv = aggregate("MVTec-AD", load_mvtec, MVTEC_CATS)
    va_cats = sorted(set(r["category"] for r in load_visa("patchcore", 0)))
    va = aggregate("VisA", load_visa, va_cats)

    mv_esc, mv_fr = classify(mv)
    va_esc, va_fr = classify(va)

    def certified_stable(cells, cert_key):
        """The strongest subset: the gate is certified on this axis in ALL
        R=20 repeats (cert_frac==1.0) AND the bind is cross-seed stable (B1
        violates and gate holds in every one of the 5 backbone seeds)."""
        return [c for c in cells
                if c[cert_key] == 1.0
                and c["cross_seed_b1_all_violate"] and c["cross_seed_gate_all_hold"]]

    def summarize(esc, fr, label):
        print(f"\n----- {label} binding cells -----", flush=True)
        print(f"  escaped-axis (B1 mean escaped > {ALPHA_MISS} AND gate <= {ALPHA_MISS+TOL}): {len(esc)}", flush=True)
        for e in esc:
            print(f"    {e['cell']}: B1={e['b1_escaped']:.3f} gate={e['gate_escaped']:.3f} "
                  f"defer={e['gate_deferral']:.2f} g1cert_frac={e['g1_certified_frac']:.2f} "
                  f"xseed_all={e['cross_seed_b1_all_violate'] and e['cross_seed_gate_all_hold']}", flush=True)
        print(f"  false-reject-axis (B1 mean FR > {ALPHA_FR} AND gate <= {ALPHA_FR+TOL}): {len(fr)}", flush=True)
        for e in fr:
            print(f"    {e['cell']}: B1={e['b1_fr']:.3f} gate={e['gate_fr']:.3f} "
                  f"defer={e['gate_deferral']:.2f} g2cert_frac={e['g2_certified_frac']:.2f} "
                  f"xseed_all={e['cross_seed_b1_all_violate'] and e['cross_seed_gate_all_hold']}", flush=True)

    summarize(mv_esc, mv_fr, "MVTec-AD")
    summarize(va_esc, va_fr, "VisA")

    mv_esc_cert = certified_stable(mv_esc, "g1_certified_frac")
    mv_fr_cert = certified_stable(mv_fr, "g2_certified_frac")
    va_esc_cert = certified_stable(va_esc, "g1_certified_frac")
    va_fr_cert = certified_stable(va_fr, "g2_certified_frac")
    print("\n===== CERTIFIED + cross-seed-stable binding cells (the headline) =====", flush=True)
    print(f"  MVTec escaped: {[c['cell'] for c in mv_esc_cert]}", flush=True)
    print(f"  MVTec false-reject: {[c['cell'] for c in mv_fr_cert]}", flush=True)
    print(f"  VisA escaped: {[c['cell'] for c in va_esc_cert]}", flush=True)
    print(f"  VisA false-reject: {[c['cell'] for c in va_fr_cert]}", flush=True)

    result = {
        "what": "Binding demonstration: naive fixed-threshold (B1, no deferral) realized escaped/false-reject "
                "rates vs the certified gate, per (backbone, category), on held-out eval halves.",
        "label": "POST-HOC / EXPLORATORY (the M4 illustration; reported honestly either way, not manufactured).",
        "alpha_miss": ALPHA_MISS, "alpha_fr": ALPHA_FR, "tolerance_pp": TOL,
        "n_repeats": N_REPEATS, "seeds": SEEDS,
        "binding_defn": "seed-0 mean over R=20 repeats; B1 axis rate > target AND gate axis rate <= target+tol",
        "MVTec": {"per_cell": mv, "escaped_binding": mv_esc, "fr_binding": mv_fr},
        "VisA": {"per_cell": va, "escaped_binding": va_esc, "fr_binding": va_fr},
        "counts": {
            "mvtec_escaped_binding": len(mv_esc), "mvtec_fr_binding": len(mv_fr),
            "visa_escaped_binding": len(va_esc), "visa_fr_binding": len(va_fr),
        },
        "certified_stable_binding": {
            "note": "gate certified on that axis in ALL R=20 repeats AND bind holds in all 5 backbone seeds "
                    "(B1 violates target, gate within target+tol). The strongest evidence; excludes "
                    "gate-refusal cells (where the gate makes no certified claim on that axis).",
            "mvtec_escaped": mv_esc_cert, "mvtec_fr": mv_fr_cert,
            "visa_escaped": va_esc_cert, "visa_fr": va_fr_cert,
            "counts": {"mvtec_escaped": len(mv_esc_cert), "mvtec_fr": len(mv_fr_cert),
                       "visa_escaped": len(va_esc_cert), "visa_fr": len(va_fr_cert)},
        },
    }
    (outdir / "results.json").write_text(json.dumps(result, indent=2))
    print("\nWROTE binding_demo_2026-07-13/results.json", flush=True)
    print(f"\nCOUNTS: MVTec esc={len(mv_esc)} fr={len(mv_fr)} | VisA esc={len(va_esc)} fr={len(va_fr)}", flush=True)


if __name__ == "__main__":
    main()
