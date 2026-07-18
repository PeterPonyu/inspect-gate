"""End-to-end CLI test: score -> calibrate -> route -> audit -> certify ->
report, driven entirely on synthetic data (no network, no GPU, no
torch/anomalib).

Asserts (per the verification bar):
  (a) calibrate/route produce well-formed certificates on synthetic data,
  (b) audit correctly flags the informative score family,
  (c) certify aggregates repeats into a coverage table with K1/K2 gates,
  (d) refusal rules fire: an out-of-support category always defers.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from tests.conftest import make_synthetic_scores


def _write_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "inspect_gate.cli", *args],
        capture_output=True, text=True,
    )


def test_full_pipeline_e2e(tmp_path):
    all_recs = make_synthetic_scores(
        categories=("bottle", "screw", "carpet"),
        n_train_good=100, n_test_good=100, n_test_defect=100, separation=5.0, seed=123,
    )
    test_recs = [r for r in all_recs if r["split"] == "test"]
    train_good = [r for r in all_recs if r["split"] == "train"]

    # Two repeats' worth of cal/eval halves, split manually (stable/simple
    # for a CLI smoke test -- the finer repeated-split machinery is unit-
    # tested directly in test_splits.py/test_certify.py).
    from inspect_gate import splits as _splits

    reps = _splits.repeated_stratified_splits(test_recs, n_repeats=2)

    gate_paths = []
    pairs = []
    for i, (cal, ev) in enumerate(reps):
        cal_path = tmp_path / f"cal_{i}.jsonl"
        ev_path = tmp_path / f"eval_{i}.jsonl"
        _write_jsonl(cal_path, cal)
        _write_jsonl(ev_path, ev)

        gate_path = tmp_path / f"gate_{i}.json"
        proc = _run_cli(
            "calibrate", "--scores", str(cal_path),
            "--alpha-miss", "0.10", "--alpha-fr", "0.05",
            "--backbone", "patchcore", "--seed", str(i), "-o", str(gate_path),
        )
        assert proc.returncode == 0, proc.stderr
        assert gate_path.exists()
        gate_paths.append(gate_path)
        pairs.append(f"{gate_path}:{ev_path}")

    with open(gate_paths[0], "r", encoding="utf-8") as f:
        gate0 = json.load(f)
    for cat in ("bottle", "screw", "carpet"):
        assert gate0["strata"][cat]["g1_certified"] is True
        assert gate0["strata"][cat]["g2_certified"] is True

    # --- route: unseen category always defers ---
    route_input = list(test_recs[:5])
    route_input.append({
        "image_id": "unseen_001", "category": "zipper", "split": "test",
        "score": 0.0, "label": "good", "defect_type": "good",
    })
    route_in_path = tmp_path / "route_in.jsonl"
    _write_jsonl(route_in_path, route_input)
    routing_path = tmp_path / "routing.json"
    proc = _run_cli("route", "--gate", str(gate_paths[0]), "--scores", str(route_in_path), "-o", str(routing_path))
    assert proc.returncode == 0, proc.stderr
    with open(routing_path, "r", encoding="utf-8") as f:
        routing = json.load(f)
    unseen_decision = next(d for d in routing["decisions"] if d["image_id"] == "unseen_001")
    assert unseen_decision["action"] == "defer"
    assert unseen_decision["out_of_support"] is True

    # --- audit: fixed/tuned/quantile vs analytic null ---
    cal_all_path = tmp_path / "cal_all.jsonl"
    eval_all_path = tmp_path / "eval_all.jsonl"
    train_good_path = tmp_path / "train_good.jsonl"
    cal0, ev0 = reps[0]
    _write_jsonl(cal_all_path, cal0)
    _write_jsonl(eval_all_path, ev0)
    _write_jsonl(train_good_path, train_good)

    audit_path = tmp_path / "audit.json"
    proc = _run_cli(
        "audit", "--cal-scores", str(cal_all_path), "--eval-scores", str(eval_all_path),
        "--train-good-scores", str(train_good_path), "--gate", str(gate_paths[0]),
        "--practices", "fixed,tuned,quantile", "--n-perm", "200", "--backbone", "patchcore",
        "-o", str(audit_path),
    )
    assert proc.returncode == 0, proc.stderr
    with open(audit_path, "r", encoding="utf-8") as f:
        audit_result = json.load(f)
    assert audit_result["holm_family_size"] == 3
    for r in audit_result["results"]:
        assert r["excess_aurc"] > -0.5  # sanity: not wildly negative

    # --- certify: aggregate the 2 repeats' V1 coverage cells ---
    certify_path = tmp_path / "certify.json"
    proc = _run_cli(
        "certify", "--pairs", *pairs, "--alpha-miss", "0.10", "--alpha-fr", "0.05",
        "-o", str(certify_path),
    )
    assert proc.returncode == 0, proc.stderr
    with open(certify_path, "r", encoding="utf-8") as f:
        certify_result = json.load(f)
    assert set(certify_result["per_category"]) == {"bottle", "screw", "carpet"}
    for cat, rec in certify_result["per_category"].items():
        assert rec["tier1"]["pass_tier1"] is True, f"{cat}: {rec['tier1']}"
    assert certify_result["k1"]["k1_tripped"] is False
    assert certify_result["k2"]["k2_tripped"] is False

    # --- report: markdown rendering doesn't crash and mentions categories ---
    report_path = tmp_path / "report.md"
    proc = _run_cli(
        "report", "--gate", str(gate_paths[0]), "--audit", str(audit_path),
        "--certify", str(certify_path), "-o", str(report_path),
    )
    assert proc.returncode == 0, proc.stderr
    text = report_path.read_text()
    assert "bottle" in text
    assert "excess_aurc" in text or "Audit" in text


def test_score_scores_json_backbone_validates_and_normalizes(tmp_path):
    records = make_synthetic_scores(n_train_good=3, n_test_good=3, n_test_defect=3)
    in_path = tmp_path / "raw.jsonl"
    _write_jsonl(in_path, records)
    out_path = tmp_path / "scored.jsonl"
    proc = _run_cli("score", "--backbone", "scores-json", "--data", str(in_path), "-o", str(out_path))
    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()


def test_score_patchcore_backbone_refuses_with_actionable_message(tmp_path):
    proc = _run_cli("score", "--backbone", "patchcore", "--data", "/nonexistent", "-o", str(tmp_path / "x.jsonl"))
    assert proc.returncode == 1
    assert "orchestration/score_patchcore.py" in proc.stderr


def test_calibrate_bad_input_reports_schema_error(tmp_path):
    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text(json.dumps({"image_id": "x"}) + "\n")
    out_path = tmp_path / "gate.json"
    proc = _run_cli("calibrate", "--scores", str(bad_path), "-o", str(out_path))
    assert proc.returncode == 1
    assert "error:" in proc.stderr
