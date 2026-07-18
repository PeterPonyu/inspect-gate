import pytest

from inspect_gate import audit as _audit
from inspect_gate import splits as _splits
from tests.conftest import make_synthetic_scores, make_uninformative_scores


def _halves(**kw):
    all_recs = make_synthetic_scores(**kw)
    test_recs = [r for r in all_recs if r["split"] == "test"]
    train_good = [r for r in all_recs if r["split"] == "train"]
    # Stratified by (category, label), NOT a positional index slice --
    # make_synthetic_scores emits good-then-defect blocks per category, so
    # a naive index-halved split would (with one category) put all-good
    # in one half and all-defect in the other.
    cal, ev = _splits.stratified_cal_eval_split(test_recs, repeat_seed=0)
    return cal, ev, train_good


def test_run_audit_full_roster_and_holm_family_size():
    cal, ev, train_good = _halves(
        categories=("bottle", "screw"), n_train_good=100, n_test_good=100, n_test_defect=100, separation=4.0,
    )
    result = _audit.run_audit(cal, ev, train_good, target_deferral_rate=0.2, backbone="patchcore", n_perm=200, seed=0)
    assert result["holm_family_size"] == 3  # fixed, tuned, quantile
    assert len(result["results"]) == 3
    practices = {r["practice"] for r in result["results"]}
    assert practices == {"fixed", "tuned", "quantile"}
    for r in result["results"]:
        assert "p_holm" in r and "reject_holm" in r


def test_run_audit_informative_score_shows_positive_excess_aurc():
    cal, ev, train_good = _halves(
        categories=("bottle",), n_train_good=100, n_test_good=150, n_test_defect=150, separation=6.0,
    )
    result = _audit.run_audit(cal, ev, train_good, target_deferral_rate=0.1, n_perm=500, seed=0)
    for r in result["results"]:
        assert r["excess_aurc"] > 0, f"{r['practice']}: expected positive excess_aurc on separated data"


def test_run_audit_skips_quantile_practice_without_train_good():
    cal, ev, _ = _halves(categories=("bottle",), n_train_good=1, n_test_good=60, n_test_defect=60, separation=4.0)
    result = _audit.run_audit(cal, ev, None, target_deferral_rate=0.2, practices=("fixed", "tuned", "quantile"), n_perm=100, seed=0)
    assert result["holm_family_size"] == 2
    skipped_practices = {s["practice"] for s in result["skipped"]}
    assert skipped_practices == {"quantile"}


def test_run_audit_rejects_unknown_practice():
    cal, ev, _ = _halves(n_train_good=1, n_test_good=20, n_test_defect=20)
    with pytest.raises(_audit.AuditError, match="unknown"):
        _audit.run_audit(cal, ev, None, target_deferral_rate=0.1, practices=("bogus",))


def test_run_audit_rejects_empty_inputs():
    with pytest.raises(_audit.AuditError, match="non-empty"):
        _audit.run_audit([], [{"image_id": "x"}], None, target_deferral_rate=0.1)


def test_run_audit_holm_correction_is_monotone_and_bounded():
    cal, ev, train_good = _halves(
        categories=("bottle",), n_train_good=80, n_test_good=80, n_test_defect=80, separation=3.0,
    )
    result = _audit.run_audit(cal, ev, train_good, target_deferral_rate=0.15, n_perm=200, seed=1)
    for r in result["results"]:
        assert r["p_holm"] >= r["p_value"]
        assert 0.0 <= r["p_holm"] <= 1.0
