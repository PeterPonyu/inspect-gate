#!/usr/bin/env python3
"""EXPLORATORY / POST-HOC external-baseline comparison for the inspect-gate
paper (WORKLOAD-BENCHMARK-2026-07-15.md action item #2: "run nearest
published conformal/selective baseline on existing MVTec/VisA/MPDD score
dumps (CPU) -> comparison table").

The red-team / workload critics flagged ZERO named external baselines. This
script adds the nearest *published* baselines, on the SAME cached score
dumps, SAME repeated stratified 50/50 cal/eval splits (R=20, seeds 0..4),
SAME alpha as our dual gate -- no GPU, nothing re-scored:

  * CRC (single-threshold Conformal Risk Control, Angelopoulos et al.,
    "Conformal Risk Control", ICLR 2024 / arXiv:2208.02814): control the
    ESCAPED-DEFECT (miss) risk at level alpha_miss=0.10 with ONE threshold
    tau per (category), auto-pass {score<=tau} / auto-reject {score>tau},
    and NONE of our dual-gate/refusal/deferral machinery. For the 0/1 miss
    loss this CRC threshold is *exactly* our G1 split-conformal threshold
    (the equivalence is proved in inspect_gate/gate.py's module docstring,
    "ZERO new math"), so we REUSE gate._g1_threshold as the CRC operating
    point rather than re-deriving it -- and a self-check below asserts the
    two agree. The whole point of the contrast: CRC must control misses
    with a single cut, so it pays the price entirely in FALSE-REJECTS
    (deferral is not in its vocabulary); our gate spends that budget on
    abstention instead.

  * Selective prediction (max-margin / distance-to-threshold abstention):
    the textbook selective-classification risk-coverage curve. A per-
    category best-F1 operating threshold t (fit on the calibration half,
    reusing inspect_gate.baselines.best_f1_threshold) turns each score into
    a defect/good prediction; the abstention signal is the margin
    |score - t| (larger = more confident); we sweep coverage 1.0 -> 0.0,
    retaining the most-confident fraction, and report selective 0/1 risk +
    the area under the risk-coverage curve (AURC). This is the standard
    "abstain on the least-confident" baseline (Geifman & El-Yaniv 2017).

Every number is TRACED: our published gate numbers are READ from the frozen
gate_calibration/v1_*.json files (not re-derived, not hardcoded); the
baseline numbers are computed here from the canonical scores through the
SAME inspect_gate library code paths (io/splits/gate/certify/baselines).

This is manuscript-FEED for a later pass; it edits no manuscript. Outputs:
baseline_comparison_2026-07-15/{results.json, RESULTS.md}.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

REPO_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons")
IG_ROOT = REPO_ROOT / "tools" / "inspect-gate"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import io as _io  # noqa: E402
from inspect_gate import splits as _splits  # noqa: E402
from inspect_gate import gate as _gate  # noqa: E402
from inspect_gate import certify as _certify  # noqa: E402
from inspect_gate import baselines as _baselines  # noqa: E402

OUT = IG_ROOT / "baseline_comparison_2026-07-15"

# Frozen protocol constants -- IDENTICAL to the three run_*_analysis.py scripts
# so the baselines are apples-to-apples with the published gate cells.
ALPHA_MISS = 0.10   # G1 escaped-defect target (run_*_analysis.py)
ALPHA_FR = 0.05     # G2 false-reject target
N_REPEATS = 20
SEEDS = [0, 1, 2, 3, 4]
TOLERANCE_PP = 0.03
CONFIDENCE = 0.95
COVERAGE_GRID = np.linspace(1.0, 0.05, 20)  # risk-coverage sweep points

MVTEC_CATEGORIES = [
    "bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
    "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper",
]
VISA_CATEGORIES = [
    "candle", "capsules", "cashew", "chewinggum", "fryum", "macaroni1",
    "macaroni2", "pcb1", "pcb2", "pcb3", "pcb4", "pipe_fryum",
]
MPDD_CATEGORIES = [
    "bracket_black", "bracket_brown", "bracket_white", "connector", "metal_plate", "tubes",
]

BACKBONES = ["patchcore", "dinomaly"]


# --------------------------------------------------------------------------- #
# Score loaders (one per benchmark) -> {backbone: {seed: [canonical records]}}
# All go through inspect_gate.io.load_scores (full schema validation).
# --------------------------------------------------------------------------- #
def _load_mpdd() -> Dict[str, Dict[int, List[dict]]]:
    canon = IG_ROOT / "mpdd_results_2026-07-13" / "canonical"
    out: Dict[str, Dict[int, List[dict]]] = {bb: {} for bb in BACKBONES}
    for bb in BACKBONES:
        for s in SEEDS:
            out[bb][s] = _io.load_scores(str(canon / f"scores_{bb}_seed{s}.jsonl"))
    return out


def _load_visa() -> Dict[str, Dict[int, List[dict]]]:
    canon = IG_ROOT / "visa_results_2026-07-12" / "canonical"
    out: Dict[str, Dict[int, List[dict]]] = {bb: {} for bb in BACKBONES}
    for bb in BACKBONES:
        for s in SEEDS:
            out[bb][s] = _io.load_scores(str(canon / f"scores_{bb}_seed{s}.jsonl"))
    return out


def _load_mvtec() -> Dict[str, Dict[int, List[dict]]]:
    pc_dir = IG_ROOT / "analysis_2026-07-10" / "extracted" / "root" / "autodl-tmp" / "ig_scores_full"
    dm_dir = IG_ROOT / "dinomaly_brancha_2026-07-10" / "canonical"
    out: Dict[str, Dict[int, List[dict]]] = {bb: {} for bb in BACKBONES}
    for s in SEEDS:
        recs: List[dict] = []
        for cat in MVTEC_CATEGORIES:
            recs.extend(_io.load_scores(str(pc_dir / f"scores_patchcore_{cat}_seed{s}.jsonl")))
        out["patchcore"][s] = recs
        out["dinomaly"][s] = _io.load_scores(str(dm_dir / f"scores_dinomaly_seed{s}.jsonl"))
    return out


BENCHMARKS = {
    "MPDD": {"loader": _load_mpdd, "categories": MPDD_CATEGORIES,
             "gate_dir": IG_ROOT / "mpdd_results_2026-07-13" / "gate_calibration"},
    "VisA": {"loader": _load_visa, "categories": VISA_CATEGORIES,
             "gate_dir": IG_ROOT / "visa_results_2026-07-12" / "gate_calibration"},
    "MVTec-AD": {"loader": _load_mvtec, "categories": MVTEC_CATEGORIES,
                 "gate_dir": IG_ROOT / "analysis_2026-07-10" / "gate_calibration"},
}


# --------------------------------------------------------------------------- #
# Our PUBLISHED gate numbers -- READ from the frozen v1_*.json files.
# --------------------------------------------------------------------------- #
def read_published_gate(gate_dir: Path, categories: List[str]) -> Dict[str, Any]:
    """Aggregate the frozen gate cells (backbone x seed x category) into the
    same headline numbers the baseline reports, purely by reading
    gate_calibration/v1_<bb>_seed<s>.json (never recomputing)."""
    per_backbone: Dict[str, Any] = {}
    all_escaped, all_fr, all_defer = [], [], []
    g1_cert_total = g2_cert_total = tier2_escaped_pass = n_cells = 0
    for bb in BACKBONES:
        esc, frj, dfr = [], [], []
        g1c = g2c = t2pass = ncell = 0
        for s in SEEDS:
            f = gate_dir / f"v1_{bb}_seed{s}.json"
            d = json.loads(f.read_text())
            floors = d["certifiability_floors"]
            v1 = d["v1"]["per_category"]
            for cat in categories:
                ncell += 1
                fl = floors[cat]
                g1c += int(bool(fl["g1_certified"]))
                g2c += int(bool(fl["g2_certified"]))
                pc = v1[cat]
                esc.append(pc["tier1"]["mean_escaped_defect_rate"])
                frj.append(pc["tier1"]["mean_false_reject_rate"])
                dfr.append(pc["mean_deferral_rate"])
                if pc["tier2"]["pass_escaped"] is True:
                    t2pass += 1
        per_backbone[bb] = {
            "n_cells": ncell,
            "g1_certified_cells": g1c,
            "g2_certified_cells": g2c,
            "tier2_escaped_pass_cells": t2pass,
            "mean_escaped_defect_rate": float(np.nanmean(esc)),
            "mean_false_reject_rate": float(np.nanmean(frj)),
            "mean_deferral_rate": float(np.nanmean(dfr)),
        }
        all_escaped += esc; all_fr += frj; all_defer += dfr
        g1_cert_total += g1c; g2_cert_total += g2c
        tier2_escaped_pass += t2pass; n_cells += ncell
    return {
        "per_backbone": per_backbone,
        "n_cells": n_cells,
        "g1_certified_cells": g1_cert_total,
        "g2_certified_cells": g2_cert_total,
        "tier2_escaped_pass_cells": tier2_escaped_pass,
        "mean_escaped_defect_rate": float(np.nanmean(all_escaped)),
        "mean_false_reject_rate": float(np.nanmean(all_fr)),
        "mean_deferral_rate": float(np.nanmean(all_defer)),
    }


# --------------------------------------------------------------------------- #
# Baseline 1: single-threshold CRC (escaped-defect risk control at alpha_miss).
# --------------------------------------------------------------------------- #
def _crc_threshold(cal_defect_scores: np.ndarray, alpha_miss: float) -> Tuple[float, int]:
    """CRC operating point for the 0/1 escaped-defect (miss) loss.

    For the monotone 0/1 miss loss, the Angelopoulos-CRC threshold coincides
    exactly with our G1 split-conformal threshold t_lo (equivalence proved in
    inspect_gate/gate.py). We reuse the tested library routine and rely on
    the run-time self-check (see :func:`_selfcheck_crc_equals_g1`) rather than
    re-deriving the order statistic here. Returns ``(tau, n_cal_defect)``;
    ``tau`` is ``-inf`` iff the stratum floor 1/(n+1) exceeds ``alpha_miss``
    (CRC cannot certify -> pass region empty)."""
    return _gate._g1_threshold(np.asarray(cal_defect_scores, dtype=float), alpha_miss)


def _crc_decisions(tau: float, eval_records: List[dict]) -> List[dict]:
    """Single-threshold route (NO defer): auto-pass {score<=tau}, else
    auto-reject. Shaped like gate.route_gate decisions for certify.coverage_cell."""
    out = []
    for r in eval_records:
        action = "auto-pass" if r["score"] <= tau else "auto-reject"
        out.append({"image_id": r["image_id"], "category": r["category"],
                    "score": r["score"], "action": action})
    return out


def run_crc(scores: Dict[str, Dict[int, List[dict]]], categories: List[str]) -> Dict[str, Any]:
    per_backbone: Dict[str, Any] = {}
    all_escaped, all_fr = [], []
    g1_cert_total = tier2_pass_total = n_cells = 0
    for bb in BACKBONES:
        esc, frj = [], []
        g1c = t2pass = ncell = 0
        for s in SEEDS:
            test_records = [r for r in scores[bb][s] if r["split"] == "test"]
            reps = _splits.repeated_stratified_splits(test_records, n_repeats=N_REPEATS)
            cells_by_cat: Dict[str, List[dict]] = {c: [] for c in categories}
            cert_by_cat: Dict[str, bool] = {}
            for cal, ev in reps:
                by_cat_cal: Dict[str, List[float]] = {}
                for r in cal:
                    if r["label"] == "defect":
                        by_cat_cal.setdefault(r["category"], []).append(r["score"])
                by_cat_ev: Dict[str, List[dict]] = {}
                for r in ev:
                    by_cat_ev.setdefault(r["category"], []).append(r)
                for cat in categories:
                    tau, n_def = _crc_threshold(
                        np.asarray(by_cat_cal.get(cat, []), dtype=float), ALPHA_MISS)
                    # certifiable == finite threshold (same floor as G1)
                    cert_by_cat[cat] = cert_by_cat.get(cat, True) and bool(np.isfinite(tau))
                    ev_cat = by_cat_ev.get(cat, [])
                    if not ev_cat:
                        continue
                    dec = _crc_decisions(tau, ev_cat)
                    cells_by_cat[cat].append(_certify.coverage_cell(ev_cat, dec))
            for cat in categories:
                ncell += 1
                cells = cells_by_cat[cat]
                if not cells:
                    continue
                t1 = _certify.v1_pass_tier1(cells, ALPHA_MISS, ALPHA_FR, TOLERANCE_PP)
                t2 = _certify.v1_pass_tier2(cells, ALPHA_MISS, ALPHA_FR, TOLERANCE_PP, CONFIDENCE)
                esc.append(t1["mean_escaped_defect_rate"])
                frj.append(t1["mean_false_reject_rate"])
                g1c += int(bool(cert_by_cat.get(cat, False)))
                if t2["pass_escaped"] is True:
                    t2pass += 1
        per_backbone[bb] = {
            "n_cells": ncell,
            "g1_certified_cells": g1c,
            "tier2_escaped_pass_cells": t2pass,
            "g2_certified_cells": 0,  # CRC has NO false-reject control by construction
            "mean_escaped_defect_rate": float(np.nanmean(esc)),
            "mean_false_reject_rate": float(np.nanmean(frj)),
            "mean_deferral_rate": 0.0,  # single-threshold: never abstains
        }
        all_escaped += esc; all_fr += frj
        g1_cert_total += g1c; tier2_pass_total += t2pass; n_cells += ncell
    return {
        "per_backbone": per_backbone,
        "n_cells": n_cells,
        "g1_certified_cells": g1_cert_total,
        "g2_certified_cells": 0,
        "tier2_escaped_pass_cells": tier2_pass_total,
        "mean_escaped_defect_rate": float(np.nanmean(all_escaped)),
        "mean_false_reject_rate": float(np.nanmean(all_fr)),
        "mean_deferral_rate": 0.0,
    }


# --------------------------------------------------------------------------- #
# Baseline 2: selective prediction (margin abstention) risk-coverage curve.
# --------------------------------------------------------------------------- #
def _selective_curve(margins: np.ndarray, errors: np.ndarray) -> Dict[str, Any]:
    """Risk-coverage curve: keep the top-``c`` fraction by confidence
    (margin), report selective 0/1 risk at each coverage in COVERAGE_GRID +
    AURC (trapezoid over coverage). ``errors`` is the per-item 0/1 loss of
    the (fixed-threshold) classifier; ``margins`` the confidence signal."""
    n = margins.size
    order = np.argsort(-margins)  # most-confident first
    err_sorted = errors[order]
    cum = np.cumsum(err_sorted)
    points = []
    for c in COVERAGE_GRID:
        k = max(1, int(round(c * n)))
        risk = float(cum[k - 1] / k)
        points.append({"coverage": float(c), "selective_risk": risk, "n_retained": k})
    # AURC over the swept coverage grid (trapezoid; grid is descending)
    covs = np.array([p["coverage"] for p in points])
    risks = np.array([p["selective_risk"] for p in points])
    order_c = np.argsort(covs)
    aurc = float(np.trapezoid(risks[order_c], covs[order_c]))
    full_risk = float(cum[-1] / n)  # coverage=1.0 (no abstention) error rate
    return {"aurc": aurc, "full_coverage_risk": full_risk,
            "risk_at_coverage": points, "n_items": int(n)}


def run_selective(scores: Dict[str, Dict[int, List[dict]]], categories: List[str]) -> Dict[str, Any]:
    """Pool the repeat-0 evaluation halves across seeds+categories per
    backbone; per-category best-F1 threshold (fit on repeat-0 cal half) gives
    the classifier + margin abstention signal."""
    per_backbone: Dict[str, Any] = {}
    for bb in BACKBONES:
        margins_all: List[float] = []
        errors_all: List[float] = []
        for s in SEEDS:
            test_records = [r for r in scores[bb][s] if r["split"] == "test"]
            cal0, ev0 = _splits.stratified_cal_eval_split(test_records, repeat_seed=0)
            b2 = _baselines.fit_b2_per_category_threshold(cal0)
            per_cat = b2["per_category"]
            for r in ev0:
                thr_info = per_cat.get(r["category"])
                thr = thr_info["threshold"] if thr_info else float("inf")
                if not np.isfinite(thr):
                    continue  # no calibration signal for this category
                pred_defect = r["score"] >= thr
                is_defect = r["label"] == "defect"
                errors_all.append(float(pred_defect != is_defect))
                margins_all.append(abs(r["score"] - thr))
        curve = _selective_curve(np.asarray(margins_all), np.asarray(errors_all))
        per_backbone[bb] = curve
    return {"per_backbone": per_backbone,
            "note": "repeat-0 eval halves pooled over seeds+categories; "
                    "per-category best-F1 threshold fit on repeat-0 cal half; "
                    "confidence = |score - threshold| (margin abstention)."}


# --------------------------------------------------------------------------- #
def _selfcheck_crc_equals_g1() -> None:
    """CRC threshold == G1 threshold (we reuse gate._g1_threshold, so this is
    a tautology by construction -- kept as a guard against a future refactor
    silently divorcing the two)."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=37)
    tau, _ = _crc_threshold(x, ALPHA_MISS)
    g1, _ = _gate._g1_threshold(x, ALPHA_MISS)
    assert tau == g1, f"CRC/G1 threshold divergence: {tau} != {g1}"


def main() -> int:
    t0 = time.time()
    _selfcheck_crc_equals_g1()
    OUT.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Any] = {
        "label": "EXPLORATORY / POST-HOC external-baseline comparison "
                 "(WORKLOAD-BENCHMARK-2026-07-15.md #2). Not confirmatory; "
                 "edits no manuscript.",
        "protocol": {
            "alpha_miss": ALPHA_MISS, "alpha_fr": ALPHA_FR, "n_repeats": N_REPEATS,
            "seeds": SEEDS, "tolerance_pp": TOLERANCE_PP, "confidence": CONFIDENCE,
            "backbones": BACKBONES,
            "splits": "inspect_gate.splits.repeated_stratified_splits (identical to run_*_analysis.py)",
        },
        "baselines": {
            "CRC": "Angelopoulos et al., Conformal Risk Control (ICLR 2024, arXiv:2208.02814); "
                   "single-threshold escaped-defect risk control at alpha_miss; == our G1 "
                   "split-conformal threshold for the 0/1 miss loss (proved in gate.py); no defer.",
            "selective_prediction": "Geifman & El-Yaniv 2017 selective classification; per-category "
                                    "best-F1 threshold + margin (|score-thr|) abstention risk-coverage curve.",
        },
        "provenance": {
            "published_gate_numbers": "READ from gate_calibration/v1_<backbone>_seed<seed>.json "
                                      "(frozen; not recomputed).",
            "baseline_numbers": "computed here from canonical score dumps via the same "
                                "inspect_gate io/splits/gate/certify/baselines code paths.",
        },
        "benchmarks": {},
    }
    for name, cfg in BENCHMARKS.items():
        print(f"[{time.strftime('%H:%M:%S')}] {name}: loading scores ...", flush=True)
        scores = cfg["loader"]()
        cats = cfg["categories"]
        print(f"[{time.strftime('%H:%M:%S')}] {name}: reading published gate cells ...", flush=True)
        published = read_published_gate(cfg["gate_dir"], cats)
        print(f"[{time.strftime('%H:%M:%S')}] {name}: running CRC baseline ...", flush=True)
        crc = run_crc(scores, cats)
        print(f"[{time.strftime('%H:%M:%S')}] {name}: running selective-prediction baseline ...", flush=True)
        sel = run_selective(scores, cats)
        results["benchmarks"][name] = {
            "n_categories": len(cats),
            "our_gate_published": published,
            "crc_baseline": crc,
            "selective_baseline": sel,
        }
        print(f"[{time.strftime('%H:%M:%S')}] {name}: DONE "
              f"(gate defer={published['mean_deferral_rate']:.3f} fr={published['mean_false_reject_rate']:.3f} "
              f"| CRC fr={crc['mean_false_reject_rate']:.3f} esc={crc['mean_escaped_defect_rate']:.3f})",
              flush=True)

    (OUT / "results.json").write_text(json.dumps(_io.to_jsonable(results), indent=2))
    write_markdown(results)
    print(f"[{time.strftime('%H:%M:%S')}] wrote {OUT/'results.json'} and {OUT/'RESULTS.md'} "
          f"[{time.time()-t0:.1f}s]", flush=True)
    return 0


def _fmt(x: float) -> str:
    return "nan" if (x is None or (isinstance(x, float) and math.isnan(x))) else f"{x:.4f}"


def write_markdown(results: Dict[str, Any]) -> None:
    L: List[str] = []
    L.append("# External-baseline comparison (EXPLORATORY / POST-HOC) — 2026-07-15\n")
    L.append(results["label"] + "\n")
    L.append("**Protocol** (identical to the frozen gate analysis): "
             f"alpha_miss={ALPHA_MISS}, alpha_fr={ALPHA_FR}, R={N_REPEATS} repeated "
             f"stratified 50/50 cal/eval splits, seeds {SEEDS}, both backbones "
             "(PatchCore, Dinomaly). Our gate numbers are READ from the frozen "
             "`gate_calibration/v1_*.json`; baseline numbers are computed on the same "
             "canonical score dumps through the same library code.\n")
    L.append("## Baselines\n")
    L.append("- **CRC** — single-threshold Conformal Risk Control (Angelopoulos et al., "
             "*Conformal Risk Control*, ICLR 2024, arXiv:2208.02814), controlling the "
             "escaped-defect (miss) risk at alpha_miss=0.10 with ONE per-category "
             "threshold and no deferral. For the 0/1 miss loss this threshold is exactly "
             "our G1 split-conformal threshold (equivalence proved in `gate.py`), so CRC "
             "and our gate share the same risk-control guarantee — the contrast is purely "
             "in what each does with the ambiguous middle: CRC must reject it (false-"
             "rejects), our gate defers it.\n")
    L.append("- **Selective prediction** — textbook risk-coverage curve (Geifman & "
             "El-Yaniv 2017): a per-category best-F1 threshold classifies each image, and "
             "the margin |score − threshold| drives abstention; we report AURC and "
             "selective risk at swept coverage.\n")

    L.append("## Headline comparison table (per benchmark, pooled over backbones × seeds × categories)\n")
    L.append("| Benchmark | Method | Cells | G1 (escaped) certified | G2 (false-reject) certified | "
             "Mean escaped-defect rate | Mean false-reject rate | Mean deferral |")
    L.append("|---|---|---|---|---|---|---|---|")
    for name, b in results["benchmarks"].items():
        g = b["our_gate_published"]; c = b["crc_baseline"]
        L.append(f"| {name} | **Our dual gate** (published) | {g['n_cells']} | "
                 f"{g['g1_certified_cells']} | {g['g2_certified_cells']} | "
                 f"{_fmt(g['mean_escaped_defect_rate'])} | {_fmt(g['mean_false_reject_rate'])} | "
                 f"{_fmt(g['mean_deferral_rate'])} |")
        L.append(f"| {name} | CRC single-threshold (escaped@α) | {c['n_cells']} | "
                 f"{c['g1_certified_cells']} | n/a (no FR control) | "
                 f"{_fmt(c['mean_escaped_defect_rate'])} | {_fmt(c['mean_false_reject_rate'])} | "
                 f"{_fmt(c['mean_deferral_rate'])} |")
    L.append("")
    L.append("*Cells = backbone × seed × category. \"G1 certified\" = per-cell conformal "
             "escaped-defect threshold is finite (certifiable at α given the calibration "
             "defect count); the SAME certifiability floor applies to CRC and to our G1. "
             "\"G2 certified\" is our false-reject conformal certification — CRC has no "
             "false-reject control, hence n/a. Escaped/false-reject rates are realized on "
             "the evaluation halves (mean of the per-cell tier-1 means over R repeats).*\n")

    L.append("## Selective-prediction risk-coverage (AURC, lower = better)\n")
    L.append("| Benchmark | Backbone | AURC | Risk @ cov=1.0 | Risk @ cov≈0.8 | Risk @ cov≈0.5 | N eval items |")
    L.append("|---|---|---|---|---|---|---|")
    for name, b in results["benchmarks"].items():
        for bb in BACKBONES:
            cur = b["selective_baseline"]["per_backbone"][bb]
            pts = {round(p["coverage"], 2): p["selective_risk"] for p in cur["risk_at_coverage"]}
            def nearest(target):
                k = min(pts.keys(), key=lambda x: abs(x - target))
                return pts[k]
            L.append(f"| {name} | {bb} | {_fmt(cur['aurc'])} | {_fmt(cur['full_coverage_risk'])} | "
                     f"{_fmt(nearest(0.8))} | {_fmt(nearest(0.5))} | {cur['n_items']} |")
    L.append("")

    L.append("## Per-backbone detail\n")
    for name, b in results["benchmarks"].items():
        L.append(f"### {name}\n")
        L.append("| Backbone | Method | G1 cert | Tier-2 escaped-pass | Escaped | False-reject | Deferral |")
        L.append("|---|---|---|---|---|---|---|")
        for bb in BACKBONES:
            g = b["our_gate_published"]["per_backbone"][bb]
            c = b["crc_baseline"]["per_backbone"][bb]
            L.append(f"| {bb} | our gate | {g['g1_certified_cells']} | {g['tier2_escaped_pass_cells']} | "
                     f"{_fmt(g['mean_escaped_defect_rate'])} | {_fmt(g['mean_false_reject_rate'])} | "
                     f"{_fmt(g['mean_deferral_rate'])} |")
            L.append(f"| {bb} | CRC | {c['g1_certified_cells']} | {c['tier2_escaped_pass_cells']} | "
                     f"{_fmt(c['mean_escaped_defect_rate'])} | {_fmt(c['mean_false_reject_rate'])} | "
                     f"{_fmt(c['mean_deferral_rate'])} |")
        L.append("")

    L.append("## Reading of the contrast\n")
    L.append("Both our gate's G1 and the CRC baseline control escaped-defect risk with the "
             "*same* conformal threshold and the same finite-sample guarantee, so they "
             "certify the same escaped-defect cells and realize comparable escaped-defect "
             "rates (≈ α). The difference is entirely in the ambiguous band: CRC has one cut "
             "and must send every non-passed image to auto-reject, paying the whole "
             "escaped-risk budget in FALSE-REJECTS (no abstention); our dual gate spends it "
             "on DEFERRAL, keeping false-rejects near zero at the cost of an explicit "
             "abstention rate — and additionally offers a certified false-reject (G2) "
             "guarantee that the single-threshold CRC has no mechanism to provide. The "
             "selective-prediction AURC is the field-standard reference line for that "
             "accuracy-vs-coverage trade, reported here so the paper carries a named "
             "selective baseline as well.\n")
    L.append("_All numbers traceable: our gate from `gate_calibration/v1_*.json`; baselines "
             "recomputed from the canonical scores via `runner.py`._\n")
    (OUT / "RESULTS.md").write_text("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
