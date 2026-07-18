import math

import numpy as np
import pytest

from inspect_gate import gate as _gate
from tests.conftest import make_synthetic_scores


def test_g1_threshold_matches_design_order_statistic_formula():
    """Direct check of the design §2.2 formula: t_lo = the k-th smallest
    defective calibration score, k = floor(alpha*(n+1)) -- independent of
    the SplitConformal-negation implementation, to catch a sign-flip bug
    class dead in its tracks."""
    rng = np.random.default_rng(0)
    scores = rng.normal(5.0, 2.0, size=37)
    alpha = 0.10
    n = scores.size
    k = math.floor(alpha * (n + 1))
    expected = float(np.sort(scores)[k - 1])  # k-th smallest, 1-indexed

    t_lo, n_out = _gate._g1_threshold(scores, alpha)
    assert n_out == n
    assert t_lo == pytest.approx(expected)


def test_g2_threshold_matches_design_order_statistic_formula():
    """Direct check of the design §2.2 formula: t_hi = the
    ceil((n+1)(1-alpha))-th smallest good calibration score."""
    rng = np.random.default_rng(1)
    scores = rng.normal(0.0, 1.0, size=41)
    alpha = 0.05
    n = scores.size
    rank = math.ceil((n + 1) * (1 - alpha))
    expected = float(np.sort(scores)[rank - 1])

    t_hi, n_out = _gate._g2_threshold(scores, alpha)
    assert n_out == n
    assert t_hi == pytest.approx(expected)


def test_g1_threshold_refuses_below_certifiability_floor():
    # n=8: alpha_min = 1/9 = 0.111; alpha=0.10 < floor -> refused (-inf).
    scores = np.arange(8, dtype=float)
    t_lo, n = _gate._g1_threshold(scores, alpha_miss=0.10)
    assert n == 8
    assert t_lo == float("-inf")
    assert _gate.certifiability_floor(8) == pytest.approx(1 / 9)


def test_g1_threshold_certifies_above_certifiability_floor():
    # n=9: alpha_min = 1/10 = 0.10; alpha=0.10 is exactly at the floor,
    # still certifiable (design §4 K5: "at n_def_cal = 9 the floor is
    # exactly 0.10 and still certifiable, off-by-one corrected").
    scores = np.arange(9, dtype=float)
    t_lo, n = _gate._g1_threshold(scores, alpha_miss=0.10)
    assert n == 9
    assert math.isfinite(t_lo)


def test_g2_threshold_empty_pool_is_always_reject_refused():
    t_hi, n = _gate._g2_threshold(np.asarray([], dtype=float), alpha_fr=0.05)
    assert n == 0
    assert t_hi == float("inf")


def _cal_records(seed=0, **kw):
    all_recs = make_synthetic_scores(seed=seed, **kw)
    return [r for r in all_recs if r["split"] == "test"]


def test_calibrate_gate_basic_shape_and_provenance():
    # Enough separation + enough n that the extreme calibration order
    # statistics (alpha_miss=0.10, alpha_fr=0.05) don't cross by chance --
    # crossed thresholds are a legitimate gate state (tested separately in
    # test_route_gate_crossed_thresholds_defer_the_overlap), not something
    # this shape-and-provenance smoke test should trip over.
    cal = _cal_records(categories=("bottle", "screw"), n_train_good=1, n_test_good=200, n_test_defect=200, separation=6.0)
    result = _gate.calibrate_gate(cal, alpha_miss=0.10, alpha_fr=0.05, backbone="patchcore", seed=0)
    assert set(result["categories_seen"]) == {"bottle", "screw"}
    assert "provenance" in result
    for cat, s in result["strata"].items():
        assert s["n_cal_defect"] > 0
        assert s["n_cal_good"] > 0
        assert s["g1_certified"] is True
        assert s["g2_certified"] is True
        assert math.isfinite(s["t_lo"]) and math.isfinite(s["t_hi"])
        # NOTE: t_lo need not be < t_hi even under strong separation -- t_lo
        # is set purely from the defect distribution's alpha_miss-quantile,
        # independent of where the good distribution sits; a crossed-
        # threshold regime is a legitimate, correctly-handled gate state
        # (design §2.2, tested directly in
        # test_route_gate_crossed_thresholds_defer_the_overlap and
        # end-to-end in test_certify.py's full calibrate/route/certify loop).


def test_calibrate_gate_rejects_invalid_alpha():
    cal = _cal_records(n_train_good=1, n_test_good=20, n_test_defect=20)
    with pytest.raises(_gate.GateError, match="alpha_miss"):
        _gate.calibrate_gate(cal, alpha_miss=1.5, alpha_fr=0.05)
    with pytest.raises(_gate.GateError, match="alpha_fr"):
        _gate.calibrate_gate(cal, alpha_miss=0.1, alpha_fr=-0.1)


def test_calibrate_gate_rejects_invalid_mondrian():
    cal = _cal_records(n_train_good=1, n_test_good=20, n_test_defect=20)
    with pytest.raises(_gate.GateError, match="mondrian"):
        _gate.calibrate_gate(cal, alpha_miss=0.1, alpha_fr=0.05, mondrian="bogus")


def test_calibrate_gate_no_defective_calibration_flag():
    # A pool with only good images (cold-start factory case, design §2.3
    # last row): G1 impossible everywhere, flagged not silently dropped.
    all_recs = make_synthetic_scores(categories=("bottle",), n_train_good=1, n_test_good=30, n_test_defect=0)
    cal = [r for r in all_recs if r["split"] == "test"]
    result = _gate.calibrate_gate(cal, alpha_miss=0.10, alpha_fr=0.05)
    assert result["no_defective_calibration"] is True
    for s in result["strata"].values():
        assert s["g1_certified"] is False
        assert s["t_lo"] == float("-inf")


def test_calibrate_gate_defect_type_mondrian_fallback():
    all_recs = make_synthetic_scores(
        categories=("bottle",), n_train_good=1, n_test_good=30, n_test_defect=30, n_defect_types=3,
    )
    cal = [r for r in all_recs if r["split"] == "test"]
    result = _gate.calibrate_gate(
        cal, alpha_miss=0.10, alpha_fr=0.05, mondrian="category,defect_type", min_defect_type_n=100,
    )
    dt_thresholds = result["strata"]["bottle"]["defect_type_thresholds"]
    assert len(dt_thresholds) == 3
    for dt, rec in dt_thresholds.items():
        # min_defect_type_n=100 guarantees every defect type falls back.
        assert rec["certified"] is False
        assert rec["fallback_reason"] is not None
        assert rec["t_lo"] == result["strata"]["bottle"]["t_lo"]


def test_route_gate_out_of_support_category_always_defers():
    cal = _cal_records(categories=("bottle",), n_train_good=1, n_test_good=30, n_test_defect=30, separation=3.0)
    gate = _gate.calibrate_gate(cal, alpha_miss=0.10, alpha_fr=0.05)
    new_record = [{
        "image_id": "unseen_cat_001", "category": "zipper", "split": "test",
        "score": 0.0, "label": "good", "defect_type": "good",
    }]
    result = _gate.route_gate(gate, new_record)
    d = result["decisions"][0]
    assert d["action"] == "defer"
    assert d["out_of_support"] is True
    assert result["n_out_of_support"] == 1


def test_route_gate_auto_pass_and_auto_reject_on_well_separated_data():
    cal = _cal_records(categories=("bottle",), n_train_good=1, n_test_good=200, n_test_defect=200, separation=6.0)
    gate = _gate.calibrate_gate(cal, alpha_miss=0.10, alpha_fr=0.05)
    fresh = _cal_records(seed=99, categories=("bottle",), n_train_good=1, n_test_good=50, n_test_defect=50, separation=6.0)
    routed = _gate.route_gate(gate, fresh)
    assert routed["n_auto_pass"] > 0
    assert routed["n_auto_reject"] > 0
    # With this much separation, escaped defects among auto-passes should
    # be rare (a smoke check on the realized rate, not a per-repeat
    # guarantee -- the certified statement is statistical, checked
    # properly in test_certify.py's coverage-cell tests).
    by_id = {r["image_id"]: r for r in fresh}
    auto_pass_ids = [d["image_id"] for d in routed["decisions"] if d["action"] == "auto-pass"]
    n_escaped = sum(1 for i in auto_pass_ids if by_id[i]["label"] == "defect")
    assert n_escaped / max(len(auto_pass_ids), 1) < 0.10 + 0.10  # generous slack over target


def test_route_gate_crossed_thresholds_defer_the_overlap():
    gate = {
        "categories_seen": ["bottle"],
        "strata": {
            "bottle": {"t_lo": 5.0, "t_hi": 2.0, "g2_certified": True},  # crossed
        },
    }
    records = [
        {"image_id": "a", "category": "bottle", "score": 1.0, "label": "good", "defect_type": "good", "split": "test"},
        {"image_id": "b", "category": "bottle", "score": 3.5, "label": "good", "defect_type": "good", "split": "test"},
        {"image_id": "c", "category": "bottle", "score": 6.0, "label": "good", "defect_type": "good", "split": "test"},
    ]
    result = _gate.route_gate(gate, records)
    actions = {d["image_id"]: d["action"] for d in result["decisions"]}
    assert actions["a"] == "auto-pass"    # below t_hi=2.0
    assert actions["b"] == "defer"        # inside [t_hi, t_lo] = [2.0, 5.0]
    assert actions["c"] == "auto-reject"  # above t_lo=5.0


def test_calibrate_gate_train_holdout_ks_gate_downgrades_g2_on_shift():
    all_recs = make_synthetic_scores(
        categories=("bottle",), n_train_good=200, n_test_good=100, n_test_defect=100, separation=3.0,
    )
    cal = [r for r in all_recs if r["split"] == "test"]
    train_good = [r for r in all_recs if r["split"] == "train"]
    # Shift the holdout pool's scores far away -- should fail the KS gate.
    shifted_holdout = [dict(r, score=r["score"] + 50.0) for r in train_good]

    result = _gate.calibrate_gate(
        cal, alpha_miss=0.10, alpha_fr=0.05,
        good_cal_holdout=shifted_holdout, good_cal_holdout_cal=cal,
    )
    assert result["good_cal_mode"] == "train-holdout"
    stratum = result["strata"]["bottle"]
    assert stratum["g2_mode"] == "audited-not-certified"
    assert stratum["g2_certified"] is False
    assert result["ks_gate"]["bottle"]["passed"] is False


def test_calibrate_gate_train_holdout_ks_gate_passes_on_exchangeable_data():
    all_recs = make_synthetic_scores(
        categories=("bottle",), n_train_good=300, n_test_good=150, n_test_defect=100, separation=3.0, seed=7,
    )
    cal = [r for r in all_recs if r["split"] == "test"]
    train_good = [r for r in all_recs if r["split"] == "train"]

    result = _gate.calibrate_gate(
        cal, alpha_miss=0.10, alpha_fr=0.05,
        good_cal_holdout=train_good, good_cal_holdout_cal=cal, seed=1,
    )
    stratum = result["strata"]["bottle"]
    assert result["ks_gate"]["bottle"]["passed"] is True
    assert stratum["g2_mode"] == "train-holdout"
    assert stratum["g2_certified"] is True


def test_calibrate_gate_mismatched_holdout_args_rejected():
    cal = _cal_records(n_train_good=1, n_test_good=20, n_test_defect=20)
    with pytest.raises(_gate.GateError, match="good_cal_holdout"):
        _gate.calibrate_gate(cal, alpha_miss=0.1, alpha_fr=0.05, good_cal_holdout=cal)


def test_calibrate_gate_rejects_empty_input():
    with pytest.raises(_gate.GateError, match="non-empty"):
        _gate.calibrate_gate([], alpha_miss=0.1, alpha_fr=0.05)
