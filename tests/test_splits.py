import pytest

from inspect_gate import splits as _splits
from tests.conftest import make_synthetic_scores


def _test_records(**kw):
    all_recs = make_synthetic_scores(**kw)
    return [r for r in all_recs if r["split"] == "test"]


def test_stratified_split_disjoint_and_covers_all():
    test_records = _test_records(n_train_good=1, n_test_good=60, n_test_defect=40)
    cal, ev = _splits.stratified_cal_eval_split(test_records, repeat_seed=0)
    cal_ids = {r["image_id"] for r in cal}
    ev_ids = {r["image_id"] for r in ev}
    assert cal_ids.isdisjoint(ev_ids)
    assert cal_ids | ev_ids == {r["image_id"] for r in test_records}


def test_stratified_split_balances_label_within_category():
    test_records = _test_records(
        categories=("bottle",), n_train_good=1, n_test_good=100, n_test_defect=50
    )
    cal, ev = _splits.stratified_cal_eval_split(test_records, repeat_seed=0, frac=0.5)
    cal_defect = sum(1 for r in cal if r["label"] == "defect")
    ev_defect = sum(1 for r in ev if r["label"] == "defect")
    # 50/50 split of 50 defectives -> 25/25, exact since 50 is even.
    assert cal_defect == 25
    assert ev_defect == 25
    cal_good = sum(1 for r in cal if r["label"] == "good")
    ev_good = sum(1 for r in ev if r["label"] == "good")
    assert cal_good == 50
    assert ev_good == 50


def test_stratified_split_rejects_non_test_records():
    train_and_test = make_synthetic_scores(n_train_good=5, n_test_good=5, n_test_defect=5)
    with pytest.raises(_splits.SplitError, match="split"):
        _splits.stratified_cal_eval_split(train_and_test, repeat_seed=0)


def test_repeated_splits_use_distinct_seeds_and_produce_different_partitions():
    test_records = _test_records(
        categories=("bottle",), n_train_good=1, n_test_good=100, n_test_defect=60
    )
    reps = _splits.repeated_stratified_splits(test_records, n_repeats=5)
    assert len(reps) == 5
    cal_id_sets = [frozenset(r["image_id"] for r in cal) for cal, _ in reps]
    # Not all repeats should produce an identical calibration half (would
    # indicate the seed isn't actually varying the partition).
    assert len(set(cal_id_sets)) > 1


def test_repeated_splits_rejects_bad_n_repeats():
    test_records = _test_records(n_train_good=1, n_test_good=10, n_test_defect=10)
    with pytest.raises(_splits.SplitError, match="n_repeats"):
        _splits.repeated_stratified_splits(test_records, n_repeats=0)


def test_by_defect_type_stratification_and_sparse_fallback():
    # bottle: 3 defect types, one deliberately sparse (n=1, below min_defect_type_n=2).
    all_recs = make_synthetic_scores(
        categories=("bottle",), n_train_good=1, n_test_good=20, n_test_defect=21, n_defect_types=3,
    )
    test_records = [r for r in all_recs if r["split"] == "test"]
    # Force one defect type down to a single image (sparse).
    dt_to_sparsify = test_records[-1]["defect_type"]
    kept = []
    seen_sparse = 0
    for r in test_records:
        if r["label"] == "defect" and r["defect_type"] == dt_to_sparsify:
            seen_sparse += 1
            if seen_sparse > 1:
                continue
        kept.append(r)

    cal, ev = _splits.stratified_cal_eval_split(
        kept, repeat_seed=0, by_defect_type=True, min_defect_type_n=2
    )
    cal_ids = {r["image_id"] for r in cal}
    ev_ids = {r["image_id"] for r in ev}
    assert cal_ids | ev_ids == {r["image_id"] for r in kept}
    assert cal_ids.isdisjoint(ev_ids)


def test_train_good_holdout_split_disjoint_and_per_category():
    all_recs = make_synthetic_scores(
        categories=("bottle", "screw"), n_train_good=100, n_test_good=5, n_test_defect=5
    )
    train_records = [r for r in all_recs if r["split"] == "train"]
    fit_pool, holdout_pool = _splits.train_good_holdout_split(train_records, holdout_frac=0.2, seed=0)
    fit_ids = {r["image_id"] for r in fit_pool}
    hold_ids = {r["image_id"] for r in holdout_pool}
    assert fit_ids.isdisjoint(hold_ids)
    assert fit_ids | hold_ids == {r["image_id"] for r in train_records}
    for cat in ("bottle", "screw"):
        n_hold_cat = sum(1 for r in holdout_pool if r["category"] == cat)
        assert 15 <= n_hold_cat <= 25  # ~20% of 100, per-category


def test_train_good_holdout_split_rejects_non_train_or_defective():
    all_recs = make_synthetic_scores(n_train_good=10, n_test_good=5, n_test_defect=5)
    test_recs = [r for r in all_recs if r["split"] == "test"]
    with pytest.raises(_splits.SplitError, match="train"):
        _splits.train_good_holdout_split(test_recs)

    train_recs = [r for r in all_recs if r["split"] == "train"]
    defect_rec = next(r for r in test_recs if r["label"] == "defect")
    tainted = list(train_recs) + [
        {**defect_rec, "split": "train"}  # a defect record mislabeled as train
    ]
    with pytest.raises(_splits.SplitError, match="good"):
        _splits.train_good_holdout_split(tainted)
