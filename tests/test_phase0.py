"""Tests for orchestration/phase0.py: staging, count-freezing, and the
reproduction gate -- all CPU/stdlib-only paths, no torch/anomalib."""

import importlib.util
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from inspect_gate import io as _io
from tests.conftest import make_synthetic_scores

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "orchestration" / "phase0.py"
_spec = importlib.util.spec_from_file_location("phase0", _SCRIPT_PATH)
phase0 = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(phase0)


def _make_bottle_tree(root: Path):
    (root / "bottle" / "train" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (root / "bottle" / "train" / "good" / f"{i:03d}.png").touch()
    (root / "bottle" / "test" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(3):
        (root / "bottle" / "test" / "good" / f"{i:03d}.png").touch()
    (root / "bottle" / "test" / "scratch").mkdir(parents=True, exist_ok=True)
    for i in range(2):
        (root / "bottle" / "test" / "scratch" / f"{i:03d}.png").touch()


def test_stage_tarball_extracts_and_checksums(tmp_path):
    src = tmp_path / "src"
    _make_bottle_tree(src)
    tarball = tmp_path / "mvtec.tar.gz"
    with tarfile.open(tarball, "w:gz") as tf:
        tf.add(src / "bottle", arcname="bottle")

    data_root = tmp_path / "extracted"
    result = phase0.stage_tarball(str(tarball), str(data_root))
    assert result["already_staged"] is False
    assert (data_root / "bottle" / "train" / "good").exists()
    assert len(result["tarball_sha256"]) == 64


def test_stage_tarball_idempotent_skips_reextraction(tmp_path):
    src = tmp_path / "src"
    _make_bottle_tree(src)
    tarball = tmp_path / "mvtec.tar.gz"
    with tarfile.open(tarball, "w:gz") as tf:
        tf.add(src / "bottle", arcname="bottle")
    data_root = tmp_path / "extracted"
    phase0.stage_tarball(str(tarball), str(data_root))
    result2 = phase0.stage_tarball(str(tarball), str(data_root))
    assert result2["already_staged"] is True


def test_stage_tarball_raises_on_missing_tarball(tmp_path):
    with pytest.raises(FileNotFoundError):
        phase0.stage_tarball(str(tmp_path / "nope.tar.xz"), str(tmp_path / "out"))


def test_freeze_category_counts(tmp_path):
    _make_bottle_tree(tmp_path)
    counts = phase0.freeze_category_counts(str(tmp_path), ["bottle"])
    assert counts["bottle"]["n_train_good"] == 5
    assert counts["bottle"]["n_test_good"] == 3
    assert counts["bottle"]["n_test_defect"] == 2
    assert counts["bottle"]["defect_type_counts"] == {"scratch": 2}


def test_run_reproduction_gate_from_scores_file(tmp_path):
    records = make_synthetic_scores(categories=("bottle",), n_train_good=1, n_test_good=100, n_test_defect=100, separation=8.0)
    scores_path = tmp_path / "scores.jsonl"
    _io.write_jsonl(scores_path, records)
    result = phase0.run_reproduction_gate(str(scores_path), "patchcore", tolerance=0.5)
    assert result["backbone"] == "patchcore"
    assert result["pass"] is True


def test_phase0_cli_counts_only_and_reproduction(tmp_path):
    _make_bottle_tree(tmp_path)
    records = make_synthetic_scores(categories=("bottle",), n_train_good=1, n_test_good=100, n_test_defect=100, separation=8.0)
    scores_path = tmp_path / "scores.jsonl"
    _io.write_jsonl(scores_path, records)

    out_path = tmp_path / "phase0.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--data-root", str(tmp_path), "--category", "bottle",
         "--counts-only", "--patchcore-scores", str(scores_path), "--auroc-tolerance", "0.5",
         "-o", str(out_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    with open(out_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["category_counts"]["bottle"]["n_train_good"] == 5
    assert result["reproduction"]["patchcore"]["pass"] is True
    assert result["reproduction_gate_pass"] is True


def test_phase0_cli_fails_vacuously_when_zero_backbones_graded(tmp_path):
    # Neither --patchcore-scores nor --dinomaly-scores supplied: the
    # reproduction dict ends up empty. Without --skip-reproduction-gate,
    # this must NOT be reported as a silent pass.
    _make_bottle_tree(tmp_path)
    out_path = tmp_path / "phase0.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--data-root", str(tmp_path), "--category", "bottle",
         "--counts-only", "-o", str(out_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1, proc.stderr
    with open(out_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["reproduction_gate_pass"] is False
    assert "zero backbones graded" in result["reproduction_gate_reason"]


def test_phase0_cli_skip_reproduction_gate_flag_avoids_vacuous_failure(tmp_path):
    # A genuinely staging-only invocation (e.g. Phase-0 Stage 1, before any
    # backbone has been scored) opts out explicitly and must succeed.
    _make_bottle_tree(tmp_path)
    out_path = tmp_path / "phase0.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--data-root", str(tmp_path), "--category", "bottle",
         "--counts-only", "--skip-reproduction-gate", "-o", str(out_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    with open(out_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["reproduction_gate_pass"] is None
    assert "reproduction_gate_reason" not in result


def test_phase0_cli_fails_on_reproduction_gate_failure(tmp_path):
    _make_bottle_tree(tmp_path)
    # Uninformative scores (separation=0) -> AUROC near 0.5, should fail the
    # PatchCore target (~0.991) even with a generous tolerance.
    records = make_synthetic_scores(categories=("bottle",), n_train_good=1, n_test_good=100, n_test_defect=100, separation=0.0)
    scores_path = tmp_path / "scores.jsonl"
    _io.write_jsonl(scores_path, records)

    out_path = tmp_path / "phase0.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--data-root", str(tmp_path), "--category", "bottle",
         "--counts-only", "--patchcore-scores", str(scores_path), "--auroc-tolerance", "0.05",
         "-o", str(out_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    with open(out_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["reproduction_gate_pass"] is False
