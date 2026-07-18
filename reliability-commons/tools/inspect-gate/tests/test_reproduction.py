import numpy as np
import pytest

from inspect_gate import reproduction as _repro
from tests.conftest import make_synthetic_scores


def test_image_auroc_perfect_separation_is_one():
    scores = np.array([0.0, 0.1, 0.2, 5.0, 5.1, 5.2])
    is_defect = np.array([False, False, False, True, True, True])
    assert _repro.image_auroc(scores, is_defect) == pytest.approx(1.0)


def test_image_auroc_reversed_separation_is_zero():
    scores = np.array([5.0, 5.1, 5.2, 0.0, 0.1, 0.2])
    is_defect = np.array([False, False, False, True, True, True])
    assert _repro.image_auroc(scores, is_defect) == pytest.approx(0.0)


def test_image_auroc_random_scores_near_half():
    rng = np.random.default_rng(0)
    scores = rng.normal(0.0, 1.0, size=4000)
    is_defect = rng.random(4000) < 0.5
    auroc = _repro.image_auroc(scores, is_defect)
    assert 0.45 < auroc < 0.55


def test_image_auroc_rejects_single_class():
    scores = np.array([1.0, 2.0, 3.0])
    is_defect = np.array([False, False, False])
    with pytest.raises(_repro.ReproductionError, match="both classes"):
        _repro.image_auroc(scores, is_defect)


def test_reproduction_gate_patchcore_target_and_pass():
    records = make_synthetic_scores(
        categories=("bottle", "screw"), n_train_good=1, n_test_good=100, n_test_defect=100, separation=8.0,
    )
    result = _repro.reproduction_gate(records, backbone="patchcore", tolerance=0.5)
    assert result["target"] == _repro.PATCHCORE_TARGET_AUROC
    assert result["pass"] is True  # near-perfect separation, generous tolerance
    assert set(result["per_category"]) == {"bottle", "screw"}


def test_reproduction_gate_dinomaly_unset_target_returns_none_pass():
    records = make_synthetic_scores(n_train_good=1, n_test_good=50, n_test_defect=50, separation=3.0)
    result = _repro.reproduction_gate(records, backbone="dinomaly")
    if _repro.DINOMALY_TARGET_AUROC is None:
        assert result["pass"] is None
        assert result["target"] is None


def test_reproduction_gate_rejects_unknown_backbone():
    records = make_synthetic_scores(n_train_good=1, n_test_good=10, n_test_defect=10)
    with pytest.raises(_repro.ReproductionError, match="unknown backbone"):
        _repro.reproduction_gate(records, backbone="efficientad")


def test_reproduction_gate_rejects_no_test_records():
    records = [r for r in make_synthetic_scores(n_train_good=10, n_test_good=1, n_test_defect=1) if r["split"] == "train"]
    with pytest.raises(_repro.ReproductionError, match="test"):
        _repro.reproduction_gate(records, backbone="patchcore")
