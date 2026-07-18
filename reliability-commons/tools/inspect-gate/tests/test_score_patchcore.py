"""Mocked-boundary tests for orchestration/score_patchcore.py: exercises
extract_prediction_fields()/_image_id_from_path() with fake prediction
objects, NEVER importing torch/anomalib. Confirms this module is
importable with no heavy deps on the path (lazy-import discipline)."""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "orchestration" / "score_patchcore.py"


def _no_heavy_deps_installed() -> bool:
    for mod in ("torch", "anomalib"):
        if mod in sys.modules:
            return False
        spec = importlib.util.find_spec(mod)
        if spec is not None:
            return False
    return True


def test_module_imports_without_torch_or_anomalib():
    if not _no_heavy_deps_installed():
        # By this test's own docstring the assertion is "vacuous but not
        # wrong" when torch/anomalib ARE present (e.g. the dl research env)
        # -- an env property, not a code defect, so skip rather than fail
        # (2026-07-13; original asserted and failed on any torch-bearing env).
        import pytest
        pytest.skip("torch/anomalib present in this env -- lazy-import "
                    "discipline unprovable here, not violated")
    spec = importlib.util.spec_from_file_location("score_patchcore", _SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)  # must succeed with no torch/anomalib on the path
    assert hasattr(module, "run_patchcore_category")
    assert hasattr(module, "extract_prediction_fields")


_spec = importlib.util.spec_from_file_location("score_patchcore", _SCRIPT_PATH)
score_patchcore = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(score_patchcore)


def test_extract_prediction_fields_object_style():
    pred = SimpleNamespace(pred_score=0.87, image_path="/data/bottle/test/scratch/000.png")
    score, path = score_patchcore.extract_prediction_fields(pred)
    assert score == 0.87
    assert path == "/data/bottle/test/scratch/000.png"


def test_extract_prediction_fields_dict_style_fallback_attr_name():
    pred = {"anomaly_score": 0.42, "path": "/data/bottle/test/good/003.png"}
    score, path = score_patchcore.extract_prediction_fields(pred)
    assert score == 0.42
    assert path == "/data/bottle/test/good/003.png"


def test_extract_prediction_fields_tensor_like_scalar():
    class FakeTensor:
        def item(self):
            return 0.55

    pred = SimpleNamespace(pred_score=FakeTensor(), image_path="/x.png")
    score, path = score_patchcore.extract_prediction_fields(pred)
    assert score == 0.55


def test_extract_prediction_fields_missing_everything_returns_none():
    pred = SimpleNamespace(unrelated=1)
    score, path = score_patchcore.extract_prediction_fields(pred)
    assert score is None
    assert path is None


def test_extract_prediction_fields_batched_path_list():
    pred = SimpleNamespace(pred_score=0.1, image_path=["/x.png"])
    score, path = score_patchcore.extract_prediction_fields(pred)
    assert path == "/x.png"


def test_image_id_from_path_known():
    image_id = score_patchcore._image_id_from_path("/data/bottle/test/scratch/007.png", "bottle", "test", "scratch")
    assert image_id == "bottle_test_scratch_007"


def test_image_id_from_path_unknown_path():
    image_id = score_patchcore._image_id_from_path(None, "bottle", "test", "scratch")
    assert "UNKNOWN" in image_id


def test_probe_writes_to_stderr(capsys):
    score_patchcore.probe([SimpleNamespace(pred_score=0.5, image_path="/x.png")], 1)
    err = capsys.readouterr().err
    assert "probe[0]" in err


# --- partition_train_holdout (torch-free) -----------------------------


def test_partition_train_holdout_zero_frac_is_a_noop():
    ids = [f"img_{i:03d}" for i in range(10)]
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout(ids, frac=0.0, seed=0)
    assert fit_ids == ids
    assert holdout_ids == []


def test_partition_train_holdout_empty_input():
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout([], frac=0.2, seed=0)
    assert fit_ids == []
    assert holdout_ids == []


def test_partition_train_holdout_size_matches_round_with_floor_one():
    ids = [f"img_{i:03d}" for i in range(10)]
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout(ids, frac=0.2, seed=0)
    assert len(holdout_ids) == 2  # round(0.2 * 10)
    assert len(fit_ids) == 8
    assert set(fit_ids) | set(holdout_ids) == set(ids)
    assert set(fit_ids) & set(holdout_ids) == set()


def test_partition_train_holdout_tiny_frac_floors_to_one_not_zero():
    ids = [f"img_{i:03d}" for i in range(10)]
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout(ids, frac=0.01, seed=0)
    assert len(holdout_ids) == 1  # max(1, round(0.01 * 10)) = max(1, 0) = 1
    assert len(fit_ids) == 9


def test_partition_train_holdout_deterministic_for_fixed_seed():
    ids = [f"img_{i:03d}" for i in range(20)]
    fit1, hold1 = score_patchcore.partition_train_holdout(ids, frac=0.3, seed=42)
    fit2, hold2 = score_patchcore.partition_train_holdout(ids, frac=0.3, seed=42)
    assert fit1 == fit2
    assert hold1 == hold2


def test_partition_train_holdout_different_seeds_can_differ():
    ids = [f"img_{i:03d}" for i in range(20)]
    _, hold_a = score_patchcore.partition_train_holdout(ids, frac=0.5, seed=1)
    _, hold_b = score_patchcore.partition_train_holdout(ids, frac=0.5, seed=2)
    assert hold_a != hold_b


def test_partition_train_holdout_capped_at_n():
    ids = [f"img_{i:03d}" for i in range(3)]
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout(ids, frac=0.99, seed=0)
    assert len(holdout_ids) <= len(ids)
    assert len(fit_ids) + len(holdout_ids) == len(ids)


def test_partition_train_holdout_output_preserves_sort_order():
    ids = [f"img_{i:03d}" for i in range(10)]
    fit_ids, holdout_ids = score_patchcore.partition_train_holdout(ids, frac=0.4, seed=7)
    assert fit_ids == sorted(fit_ids)
    assert holdout_ids == sorted(holdout_ids)


# --- CLI plumbing (torch-free: run_patchcore_category itself imports
# torch/anomalib lazily and is NOT exercised here; these tests only check
# that main()'s argparse wiring accepts and defaults the new flags). ------


def test_main_holdout_flags_have_named_defaults():
    p_holdout_frac_default = score_patchcore.DEFAULT_HOLDOUT_FRAC
    p_holdout_seed_default = score_patchcore.DEFAULT_HOLDOUT_SEED
    assert p_holdout_frac_default == 0.0
    assert isinstance(p_holdout_seed_default, int)


def test_main_missing_data_root_still_errors_with_holdout_flags(tmp_path, capsys):
    # No real MVTec data present -> every category is SKIPPED
    # (FileNotFoundError), total_scored stays 0 -> exit 1. This proves the
    # new flags parse cleanly through argparse without requiring
    # torch/anomalib (run_patchcore_category's heavy imports are never
    # reached because discover_category raises first).
    out_path = tmp_path / "scores.jsonl"
    rc = score_patchcore.main([
        "--data-root", str(tmp_path), "--category", "bottle",
        "--holdout-frac", "0.2", "--holdout-seed", "7",
        "--out", str(out_path),
    ])
    assert rc == 1
    assert not out_path.exists()
