import numpy as np
import pytest

from inspect_gate import baselines as _baselines
from tests.conftest import make_synthetic_scores


def test_best_f1_threshold_perfect_separation():
    scores = np.array([0.0, 0.1, 0.2, 5.0, 5.1, 5.2])
    is_defect = np.array([False, False, False, True, True, True])
    thr, f1 = _baselines.best_f1_threshold(scores, is_defect)
    assert 0.2 < thr <= 5.0
    assert f1 == pytest.approx(1.0)


def test_best_f1_threshold_rejects_bad_shapes():
    with pytest.raises(_baselines.BaselineError):
        _baselines.best_f1_threshold(np.array([1.0]), np.array([True, False]))
    with pytest.raises(_baselines.BaselineError):
        _baselines.best_f1_threshold(np.array([], dtype=float), np.array([], dtype=bool))


def _cal_records(**kw):
    all_recs = make_synthetic_scores(**kw)
    return [r for r in all_recs if r["split"] == "test"]


def _train_good_records(**kw):
    all_recs = make_synthetic_scores(**kw)
    return [r for r in all_recs if r["split"] == "train"]


def test_fit_b1_global_threshold():
    cal = _cal_records(categories=("bottle", "screw"), n_train_good=1, n_test_good=60, n_test_defect=60, separation=5.0)
    b1 = _baselines.fit_b1_global_threshold(cal)
    assert b1["practice"] == "fixed"
    assert b1["cal_f1"] > 0.8  # well separated synthetic data


def test_fit_b2_per_category_threshold_handles_zero_defect_category():
    cal = _cal_records(categories=("bottle",), n_train_good=1, n_test_good=30, n_test_defect=30, separation=5.0)
    # Inject a second category with NO defectives in cal.
    cal = cal + [{
        "image_id": "screw_good_only", "category": "screw", "split": "test",
        "score": 0.0, "label": "good", "defect_type": "good",
    }]
    b2 = _baselines.fit_b2_per_category_threshold(cal)
    assert b2["per_category"]["bottle"]["cal_f1"] > 0.8
    assert b2["per_category"]["screw"]["threshold"] == float("inf")


def test_fit_b3_train_good_quantile():
    train_good = _train_good_records(categories=("bottle",), n_train_good=200, n_test_good=1, n_test_defect=1)
    b3 = _baselines.fit_b3_train_good_quantile(train_good, quantile=0.95)
    scores = np.array([r["score"] for r in train_good])
    expected = float(np.quantile(scores, 0.95))
    assert b3["per_category"]["bottle"]["threshold"] == pytest.approx(expected)


def test_fit_b3_rejects_non_good_records():
    all_recs = make_synthetic_scores(n_train_good=5, n_test_good=5, n_test_defect=5)
    with pytest.raises(_baselines.BaselineError, match="good"):
        _baselines.fit_b3_train_good_quantile(all_recs)


def test_band_width_for_target_deferral_achieves_target_rate():
    rng = np.random.default_rng(0)
    scores = rng.normal(0.0, 1.0, size=5000)
    thresholds = np.zeros_like(scores)
    w = _baselines.band_width_for_target_deferral(scores, thresholds, target_deferral_rate=0.20)
    realized = float(np.mean(np.abs(scores - thresholds) <= w))
    assert realized == pytest.approx(0.20, abs=0.02)


def test_band_width_zero_target_gives_zero_width():
    scores = np.array([0.0, 1.0, 2.0])
    thresholds = np.array([0.5, 0.5, 0.5])
    w = _baselines.band_width_for_target_deferral(scores, thresholds, target_deferral_rate=0.0)
    assert w == 0.0


def test_band_route_classifies_outside_band_correctly():
    baseline = {"practice": "fixed", "threshold": 5.0}
    records = [
        {"image_id": "a", "category": "bottle", "score": 0.0},
        {"image_id": "b", "category": "bottle", "score": 4.9},
        {"image_id": "c", "category": "bottle", "score": 5.1},
        {"image_id": "d", "category": "bottle", "score": 10.0},
    ]
    routed = _baselines.band_route(records, baseline, band_width=0.2)
    actions = {r["image_id"]: r["action"] for r in routed}
    assert actions["a"] == "auto-pass"
    assert actions["b"] == "defer"
    assert actions["c"] == "defer"
    assert actions["d"] == "auto-reject"


def test_band_route_out_of_support_category_is_auto_pass():
    baseline = {"practice": "tuned", "per_category": {"bottle": {"threshold": 5.0, "cal_f1": 1.0, "n_cal": 10}}}
    records = [{"image_id": "x", "category": "zipper", "score": 100.0}]
    routed = _baselines.band_route(records, baseline, band_width=0.1)
    assert routed[0]["action"] == "auto-pass"
