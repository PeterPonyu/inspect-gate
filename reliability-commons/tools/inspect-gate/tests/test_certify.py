import math

import numpy as np
import pytest

from inspect_gate import certify as _certify
from inspect_gate import gate as _gate
from tests.conftest import make_synthetic_scores


def test_clopper_pearson_zero_miss_matches_closed_form():
    # design §1's own worked identity: for k=0, CP one-sided UB at
    # confidence c is 1 - (1-c)^(1/n).
    for n in (5, 10, 22, 100):
        ub = _certify.clopper_pearson_upper(0, n, confidence=0.95)
        closed_form = 1.0 - 0.05 ** (1.0 / n)
        assert ub == pytest.approx(closed_form, rel=1e-9)


def test_clopper_pearson_all_success_upper_is_one():
    assert _certify.clopper_pearson_upper(10, 10, confidence=0.95) == 1.0


def test_clopper_pearson_interval_contains_point_estimate():
    k, n = 3, 20
    lo, hi = _certify.clopper_pearson_interval(k, n, confidence=0.95)
    assert lo <= k / n <= hi


def test_clopper_pearson_rejects_bad_inputs():
    with pytest.raises(_certify.CertifyError):
        _certify.clopper_pearson_upper(-1, 10)
    with pytest.raises(_certify.CertifyError):
        _certify.clopper_pearson_upper(11, 10)
    with pytest.raises(_certify.CertifyError):
        _certify.clopper_pearson_upper(1, 0)


def test_min_n_for_zero_miss_certifiable_matches_design_worked_example():
    # design §1: "1 − 0.05^(1/n) ≤ 0.13 ⟺ n ≥ ln 0.05 / ln 0.87 ≈ 21.5",
    # so n_min = 22.
    n_min = _certify.min_n_for_zero_miss_certifiable(threshold=0.13, confidence=0.95)
    assert n_min == 22
    # And n=21 should NOT satisfy the bound, n=22 should.
    assert 1.0 - 0.05 ** (1.0 / 21) > 0.13
    assert 1.0 - 0.05 ** (1.0 / 22) <= 0.13


def test_coverage_cell_basic_counts():
    eval_records = [
        {"image_id": "d1", "category": "bottle", "split": "test", "score": 5.0, "label": "defect", "defect_type": "scratch"},
        {"image_id": "d2", "category": "bottle", "split": "test", "score": 5.0, "label": "defect", "defect_type": "scratch"},
        {"image_id": "g1", "category": "bottle", "split": "test", "score": 0.0, "label": "good", "defect_type": "good"},
        {"image_id": "g2", "category": "bottle", "split": "test", "score": 0.0, "label": "good", "defect_type": "good"},
    ]
    decisions = [
        {"image_id": "d1", "action": "auto-pass"},   # escaped defect
        {"image_id": "d2", "action": "auto-reject"},
        {"image_id": "g1", "action": "auto-reject"},  # false reject
        {"image_id": "g2", "action": "defer"},
    ]
    cell = _certify.coverage_cell(eval_records, decisions)
    assert cell["n_eval_def"] == 2
    assert cell["n_eval_good"] == 2
    assert cell["n_escaped"] == 1
    assert cell["n_false_reject"] == 1
    assert cell["escaped_defect_rate"] == pytest.approx(0.5)
    assert cell["false_reject_rate"] == pytest.approx(0.5)
    assert cell["n_defer"] == 1
    assert cell["deferral_rate"] == pytest.approx(0.25)


def test_coverage_cell_raises_on_missing_decision():
    eval_records = [
        {"image_id": "d1", "category": "bottle", "split": "test", "score": 5.0, "label": "defect", "defect_type": "scratch"},
    ]
    with pytest.raises(_certify.CertifyError, match="matching decision"):
        _certify.coverage_cell(eval_records, [])


def test_v1_pass_tier1_and_tier2():
    # Build 5 repeat cells with zero misses each, n_eval_def=10 per repeat
    # (pooled 50 total -- below the min_n_for_zero_miss_certifiable(0.13)=22?
    # 50 >= 22, so pooled tier2 should PASS).
    cells = []
    for _ in range(5):
        cells.append({
            "n_eval_def": 10, "n_escaped": 0, "escaped_defect_rate": 0.0,
            "n_eval_good": 10, "n_false_reject": 0, "false_reject_rate": 0.0,
            "deferral_rate": 0.1,
        })
    tier1 = _certify.v1_pass_tier1(cells, alpha_miss=0.10, alpha_fr=0.05, tolerance_pp=0.03)
    assert tier1["pass_tier1"] is True

    tier2 = _certify.v1_pass_tier2(cells, alpha_miss=0.10, alpha_fr=0.05, tolerance_pp=0.03)
    assert tier2["n_eval_def_total"] == 50
    assert tier2["underpowered_escaped"] is False
    assert tier2["pass_escaped"] is True


def test_v1_pass_tier2_underpowered_flag():
    cells = [{
        "n_eval_def": 3, "n_escaped": 0, "escaped_defect_rate": 0.0,
        "n_eval_good": 3, "n_false_reject": 0, "false_reject_rate": 0.0,
        "deferral_rate": 0.0,
    }]
    tier2 = _certify.v1_pass_tier2(cells, alpha_miss=0.10, alpha_fr=0.05, tolerance_pp=0.03)
    assert tier2["underpowered_escaped"] is True
    assert tier2["pass_escaped"] is None  # excluded from tier-2 pass/fail per design §1


def test_v1_pass_tier1_fails_on_high_miss_rate():
    cells = [{
        "n_eval_def": 10, "n_escaped": 5, "escaped_defect_rate": 0.5,
        "n_eval_good": 10, "n_false_reject": 0, "false_reject_rate": 0.0,
        "deferral_rate": 0.0,
    }]
    tier1 = _certify.v1_pass_tier1(cells, alpha_miss=0.10, alpha_fr=0.05, tolerance_pp=0.03)
    assert tier1["pass_escaped"] is False
    assert tier1["pass_tier1"] is False


def test_aggregate_v1_cells_shape():
    cells_by_category = {
        "bottle": [{
            "n_eval_def": 20, "n_escaped": 0, "escaped_defect_rate": 0.0,
            "n_eval_good": 20, "n_false_reject": 0, "false_reject_rate": 0.0,
            "deferral_rate": 0.1,
        }] * 3,
        "screw": [{
            "n_eval_def": 20, "n_escaped": 2, "escaped_defect_rate": 0.10,
            "n_eval_good": 20, "n_false_reject": 1, "false_reject_rate": 0.05,
            "deferral_rate": 0.2,
        }] * 3,
    }
    result = _certify.aggregate_v1_cells(cells_by_category, alpha_miss=0.10, alpha_fr=0.05)
    assert set(result["per_category"]) == {"bottle", "screw"}
    for cat, rec in result["per_category"].items():
        assert "tier1" in rec and "tier2" in rec
        assert rec["n_repeats"] == 3


def test_aggregate_v1_cells_rejects_empty():
    with pytest.raises(_certify.CertifyError):
        _certify.aggregate_v1_cells({}, alpha_miss=0.1, alpha_fr=0.05)


def test_coverage_sanity_check_k1():
    per_cell_tier1 = [{"pass_escaped": False}] * 5 + [{"pass_escaped": True}] * 25
    k1 = _certify.coverage_sanity_check_k1(per_cell_tier1, max_violations=5)
    assert k1["n_violations"] == 5
    assert k1["k1_tripped"] is True

    per_cell_tier1_ok = [{"pass_escaped": False}] * 2 + [{"pass_escaped": True}] * 28
    k1_ok = _certify.coverage_sanity_check_k1(per_cell_tier1_ok, max_violations=5)
    assert k1_ok["k1_tripped"] is False


def test_vacuity_check_k2():
    rates_bad = {f"cat{i}": 0.9 for i in range(10)}
    k2 = _certify.vacuity_check_k2(rates_bad, threshold=0.80, min_categories=8)
    assert k2["k2_tripped"] is True

    rates_ok = {f"cat{i}": 0.2 for i in range(10)}
    k2_ok = _certify.vacuity_check_k2(rates_ok, threshold=0.80, min_categories=8)
    assert k2_ok["k2_tripped"] is False


def test_full_calibrate_route_certify_loop_on_synthetic_repeats():
    """End-to-end sanity: on well-separated synthetic data, the V1 tier1
    pass criterion should hold across repeats."""
    from inspect_gate import splits as _splits

    all_recs = make_synthetic_scores(
        categories=("bottle", "carpet"), n_train_good=1, n_test_good=150,
        n_test_defect=150, separation=6.0, seed=42,
    )
    test_records = [r for r in all_recs if r["split"] == "test"]
    reps = _splits.repeated_stratified_splits(test_records, n_repeats=5)

    cells_by_category: dict = {}
    for cal, ev in reps:
        gate = _gate.calibrate_gate(cal, alpha_miss=0.10, alpha_fr=0.05)
        routed = _gate.route_gate(gate, ev)
        by_cat: dict = {}
        for r in ev:
            by_cat.setdefault(r["category"], []).append(r)
        for cat, recs in by_cat.items():
            decisions = [d for d in routed["decisions"] if d["category"] == cat]
            cell = _certify.coverage_cell(recs, decisions)
            cells_by_category.setdefault(cat, []).append(cell)

    result = _certify.aggregate_v1_cells(cells_by_category, alpha_miss=0.10, alpha_fr=0.05)
    for cat, rec in result["per_category"].items():
        assert rec["tier1"]["pass_tier1"] is True, f"{cat} failed tier1: {rec['tier1']}"
