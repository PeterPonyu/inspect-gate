"""Command-line entry point: ``inspect-gate {score,calibrate,route,audit,certify,report}``.

Every subcommand emits machine-readable JSON (``--out``, and to stdout
with ``--json``); ``report`` renders compact Markdown/JSON (see
``report.py``'s module docstring for the documented HTML-MVP deviation).

Two documented deviations from the design doc's literal §2.1 CLI listing
(mirrors ``asr-gate/cli.py``'s own precedent of small, documented CLI
extensions/simplifications over the design's literal listing):

1. ``score --backbone patchcore|dinomaly`` is NOT implemented in this CLI.
   Running inference is a GPU/torch/anomalib-heavy step, and this
   package's lazy-import discipline (design brief: "``--help`` and the
   full test suite run with NO torch/anomalib installed") means heavy
   deps may only be imported inside functions that are never on the
   ``--help``/test-suite import path. ``asr-gate`` sets exactly this
   precedent: its CLI has no ``decode`` subcommand at all -- decoding
   (the GPU step) lives entirely in standalone ``orchestration/decode_*.py``
   scripts that emit the canonical schema DIRECTLY, never routing back
   through the main CLI's ingest/score verbs. This package follows the
   same shape: ``orchestration/score_patchcore.py`` and
   ``orchestration/score_dinomaly.py`` are the box-side scoring scripts;
   they emit canonical scores-JSONL directly. ``inspect-gate score`` here
   therefore only supports ``--backbone scores-json`` (validate/normalize
   an already-produced or externally-precomputed table) -- exactly the
   backbone-agnostic ingestion path the design doc itself calls out
   (§2.2: "the scores-json adapter makes the tool backbone-agnostic").
   Requesting ``patchcore``/``dinomaly`` here prints an actionable error
   pointing at the orchestration script.
2. ``certify`` is not in the design's literal §2.1 listing but is a
   necessary CLI surface for the V1 coverage-certificate deliverable
   (design §1 C1's two-tier pass criterion needs R repeated calibrate+
   evaluate cells aggregated together, see ``certify.py``); it takes
   ``--pairs gate.json:eval.jsonl ...`` (one calibrated gate + its
   matching evaluation-half scores per repeat).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from inspect_gate import audit as _audit
from inspect_gate import baselines as _baselines
from inspect_gate import certify as _certify
from inspect_gate import gate as _gate
from inspect_gate import io as _io
from inspect_gate import report as _report


def _emit(result: Dict[str, Any], out: Optional[str], as_json: bool, summary: str) -> None:
    payload = _io.to_jsonable(result)
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
    if as_json or not out:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print(summary)


# ---------------------------------------------------------------------------
# score
# ---------------------------------------------------------------------------


def _cmd_score(args: argparse.Namespace) -> int:
    if args.backbone != "scores-json":
        print(
            f"error: inspect-gate score --backbone {args.backbone} is not implemented in "
            "this CLI (lazy-import discipline -- see cli.py module docstring). Run "
            f"'orchestration/score_{args.backbone}.py' directly; it emits canonical "
            "scores-JSONL that this CLI's 'calibrate'/'route'/'audit'/'certify' consume.",
            file=sys.stderr,
        )
        return 1
    records = _io.load_scores(args.data)
    _io.write_jsonl(args.out, records)
    counts = _io.category_counts(records)
    print(f"score: backbone=scores-json n={len(records)} categories={len(counts)} -> {args.out}")
    return 0


# ---------------------------------------------------------------------------
# calibrate
# ---------------------------------------------------------------------------


def _cmd_calibrate(args: argparse.Namespace) -> int:
    cal_records = _io.load_scores(args.scores)
    good_cal_holdout = _io.load_scores(args.good_cal_holdout) if args.good_cal_holdout else None
    good_cal_holdout_cal = (
        _io.load_scores(args.good_cal_holdout_cal) if args.good_cal_holdout_cal
        else (cal_records if good_cal_holdout is not None else None)
    )
    gate = _gate.calibrate_gate(
        cal_records,
        alpha_miss=args.alpha_miss,
        alpha_fr=args.alpha_fr,
        mondrian=args.mondrian,
        good_cal_holdout=good_cal_holdout,
        good_cal_holdout_cal=good_cal_holdout_cal,
        min_defect_type_n=args.min_defect_type_n,
        ks_alpha=args.ks_alpha,
        backbone=args.backbone,
        seed=args.seed,
        input_paths=[args.scores],
    )
    n_g1_ok = sum(1 for s in gate["strata"].values() if s["g1_certified"])
    n_g2_ok = sum(1 for s in gate["strata"].values() if s["g2_certified"])
    summary = (
        f"calibrate: backbone={gate['backbone']} categories={len(gate['strata'])} "
        f"g1_certified={n_g1_ok} g2_certified={n_g2_ok} "
        f"no_defective_calibration={gate['no_defective_calibration']} n_cal={gate['n_cal']}"
    )
    _emit(gate, args.out, args.json, summary)
    return 0


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------


def _cmd_route(args: argparse.Namespace) -> int:
    with open(args.gate, "r", encoding="utf-8") as f:
        gate = json.load(f)
    records = _io.load_scores(args.scores)
    result = _gate.route_gate(gate, records)
    summary = (
        f"route: n={result['n']} auto_pass={result['n_auto_pass']} "
        f"auto_reject={result['n_auto_reject']} defer={result['n_defer']} "
        f"out_of_support={result['n_out_of_support']}"
    )
    _emit(result, args.out, args.json, summary)
    return 0


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


def _cmd_audit(args: argparse.Namespace) -> int:
    cal_records = _io.load_scores(args.cal_scores)
    eval_records = _io.load_scores(args.eval_scores)
    train_good_records = _io.load_scores(args.train_good_scores) if args.train_good_scores else None
    practices = args.practices.split(",")

    target_deferral_rate = args.target_deferral_rate
    if target_deferral_rate is None:
        if not args.gate:
            print("error: audit needs --target-deferral-rate or --gate to derive it", file=sys.stderr)
            return 1
        with open(args.gate, "r", encoding="utf-8") as f:
            gate = json.load(f)
        routed = _gate.route_gate(gate, eval_records)
        target_deferral_rate = routed["n_defer"] / routed["n"] if routed["n"] else 0.0

    result = _audit.run_audit(
        cal_records, eval_records, train_good_records,
        target_deferral_rate=target_deferral_rate,
        practices=practices, backbone=args.backbone, b3_quantile=args.b3_quantile,
        n_perm=args.n_perm, alpha=args.alpha, seed=args.seed,
    )
    lines = [f"audit: backbone={args.backbone} holm_family_size={result['holm_family_size']} "
             f"target_deferral_rate={result['target_deferral_rate']:.4f}"]
    for r in result["results"]:
        lines.append(
            f"  {r['practice']}: excess_aurc={r['excess_aurc']:.4f} p={r['p_value']:.4f} "
            f"p_holm={r['p_holm']:.4f} reject_holm={r['reject_holm']}"
        )
    _emit(result, args.out, args.json, "\n".join(lines))
    return 0


# ---------------------------------------------------------------------------
# certify
# ---------------------------------------------------------------------------


def _cmd_certify(args: argparse.Namespace) -> int:
    cells_by_category: Dict[str, List[Dict[str, Any]]] = {}
    deferral_rate_samples: Dict[str, List[float]] = {}
    for spec in args.pairs:
        try:
            gate_path, eval_path = spec.split(":", 1)
        except ValueError:
            print(f"error: --pairs entry {spec!r} is not GATE_PATH:EVAL_PATH", file=sys.stderr)
            return 1
        with open(gate_path, "r", encoding="utf-8") as f:
            gate = json.load(f)
        eval_records = _io.load_scores(eval_path)
        routed = _gate.route_gate(gate, eval_records)

        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for r in eval_records:
            by_cat.setdefault(r["category"], []).append(r)
        for cat, recs in by_cat.items():
            cat_decisions = [d for d in routed["decisions"] if d["category"] == cat]
            cell = _certify.coverage_cell(recs, cat_decisions, confidence=args.confidence)
            cells_by_category.setdefault(cat, []).append(cell)
            deferral_rate_samples.setdefault(cat, []).append(cell["deferral_rate"])

    result = _certify.aggregate_v1_cells(
        cells_by_category, alpha_miss=args.alpha_miss, alpha_fr=args.alpha_fr,
        tolerance_pp=args.tolerance_pp, confidence=args.confidence,
    )
    import numpy as np

    median_deferral = {cat: float(np.nanmedian(v)) for cat, v in deferral_rate_samples.items()}
    k2 = _certify.vacuity_check_k2(median_deferral, threshold=args.k2_threshold, min_categories=args.k2_min_categories)
    per_cell_tier1 = [v["tier1"] for v in result["per_category"].values()]
    k1 = _certify.coverage_sanity_check_k1(per_cell_tier1, max_violations=args.k1_max_violations)
    result["k1"] = k1
    result["k2"] = k2

    n_pass_tier1 = sum(1 for v in result["per_category"].values() if v["tier1"]["pass_tier1"])
    summary = (
        f"certify: categories={len(result['per_category'])} pass_tier1={n_pass_tier1} "
        f"k1_tripped={k1['k1_tripped']} k2_tripped={k2['k2_tripped']}"
    )
    _emit(result, args.out, args.json, summary)
    return 0


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def _cmd_report(args: argparse.Namespace) -> int:
    gate_result = None
    audit_result = None
    certify_result = None
    if args.gate:
        with open(args.gate, "r", encoding="utf-8") as f:
            gate_result = json.load(f)
    if args.audit:
        with open(args.audit, "r", encoding="utf-8") as f:
            audit_result = json.load(f)
    if args.certify:
        with open(args.certify, "r", encoding="utf-8") as f:
            certify_result = json.load(f)
    if gate_result is None and audit_result is None and certify_result is None:
        print("error: report needs --gate and/or --audit and/or --certify", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix == ".json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"gate": gate_result, "audit": audit_result, "certify": certify_result}, f, indent=2, ensure_ascii=False)
    else:
        markdown = _report.render_markdown(gate_result, audit_result, certify_result)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown)
    print(f"wrote {out_path}")
    return 0


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="inspect-gate", description="Certified escaped-defect triage on MVTec AD")
    sub = p.add_subparsers(dest="command", required=True)

    p_score = sub.add_parser("score", help="validate/normalize a backbone's precomputed scores table")
    p_score.add_argument("--backbone", required=True, choices=["patchcore", "dinomaly", "scores-json"])
    p_score.add_argument("--data", required=True, help="path to a precomputed scores-JSONL (scores-json backbone only)")
    p_score.add_argument("-o", "--out", required=True)
    p_score.set_defaults(func=_cmd_score)

    p_cal = sub.add_parser("calibrate", help="G1 + G2 conformal gate calibration")
    p_cal.add_argument("--scores", required=True, help="calibration-half canonical scores-JSONL")
    p_cal.add_argument("--alpha-miss", type=float, default=0.10, dest="alpha_miss")
    p_cal.add_argument("--alpha-fr", type=float, default=0.05, dest="alpha_fr")
    p_cal.add_argument("--mondrian", default="category", choices=["category", "category,defect_type"])
    p_cal.add_argument("--good-cal", default="test", choices=["test", "train-holdout"], dest="good_cal_mode_flag",
                        help="informational; actual behavior is driven by whether --good-cal-holdout is given")
    p_cal.add_argument("--good-cal-holdout", default=None, help="held-out train-good scores-JSONL for the train-holdout arm")
    p_cal.add_argument("--good-cal-holdout-cal", default=None, help="reference cal-good scores-JSONL for the KS gate (default: --scores)")
    p_cal.add_argument("--min-defect-type-n", type=int, default=_gate.DEFAULT_MIN_DEFECT_TYPE_N, dest="min_defect_type_n")
    p_cal.add_argument("--ks-alpha", type=float, default=_gate.DEFAULT_KS_ALPHA, dest="ks_alpha")
    p_cal.add_argument("--backbone", default=None)
    p_cal.add_argument("--seed", type=int, default=0)
    p_cal.add_argument("-o", "--out", default=None)
    p_cal.add_argument("--json", action="store_true")
    p_cal.set_defaults(func=_cmd_calibrate)

    p_route = sub.add_parser("route", help="route new images through a calibrated gate")
    p_route.add_argument("--gate", required=True, help="gate.json from `inspect-gate calibrate`")
    p_route.add_argument("--scores", required=True, help="canonical scores-JSONL to route")
    p_route.add_argument("-o", "--out", default=None)
    p_route.add_argument("--json", action="store_true")
    p_route.set_defaults(func=_cmd_route)

    p_audit = sub.add_parser("audit", help="excess-AURC audit of B1/B2/B3 vs the analytic random null")
    p_audit.add_argument("--cal-scores", required=True, dest="cal_scores")
    p_audit.add_argument("--eval-scores", required=True, dest="eval_scores")
    p_audit.add_argument("--train-good-scores", default=None, dest="train_good_scores",
                          help="held-out train-good scores-JSONL, required for the 'quantile' (B3) practice")
    p_audit.add_argument("--practices", default="fixed,tuned,quantile")
    p_audit.add_argument("--target-deferral-rate", type=float, default=None, dest="target_deferral_rate")
    p_audit.add_argument("--gate", default=None, help="derive --target-deferral-rate from routing --eval-scores through this gate")
    p_audit.add_argument("--b3-quantile", type=float, default=0.95, dest="b3_quantile")
    p_audit.add_argument("--n-perm", type=int, default=2000, dest="n_perm")
    p_audit.add_argument("--alpha", type=float, default=0.05)
    p_audit.add_argument("--backbone", default=None)
    p_audit.add_argument("--seed", type=int, default=0)
    p_audit.add_argument("-o", "--out", default=None)
    p_audit.add_argument("--json", action="store_true")
    p_audit.set_defaults(func=_cmd_audit)

    p_cert = sub.add_parser("certify", help="V1 coverage certification across R repeats (design §1 C1)")
    p_cert.add_argument("--pairs", nargs="+", required=True, help="GATE_PATH:EVAL_SCORES_PATH, one per repeat")
    p_cert.add_argument("--alpha-miss", type=float, default=0.10, dest="alpha_miss")
    p_cert.add_argument("--alpha-fr", type=float, default=0.05, dest="alpha_fr")
    p_cert.add_argument("--tolerance-pp", type=float, default=0.03, dest="tolerance_pp")
    p_cert.add_argument("--confidence", type=float, default=0.95)
    p_cert.add_argument("--k1-max-violations", type=int, default=5, dest="k1_max_violations")
    p_cert.add_argument("--k2-threshold", type=float, default=0.80, dest="k2_threshold")
    p_cert.add_argument("--k2-min-categories", type=int, default=8, dest="k2_min_categories")
    p_cert.add_argument("-o", "--out", default=None)
    p_cert.add_argument("--json", action="store_true")
    p_cert.set_defaults(func=_cmd_certify)

    p_report = sub.add_parser("report", help="compact JSON+Markdown summary")
    p_report.add_argument("--gate", default=None)
    p_report.add_argument("--audit", default=None)
    p_report.add_argument("--certify", default=None)
    p_report.add_argument("-o", "--output", required=True, help="output .md or .json path")
    p_report.set_defaults(func=_cmd_report)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (_io.SchemaError, _gate.GateError, _audit.AuditError, _certify.CertifyError, _baselines.BaselineError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
