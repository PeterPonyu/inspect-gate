import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from inspect_gate import io as _io
from tests.conftest import make_synthetic_scores

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "orchestration" / "run_pilot_cell.py"
_spec = importlib.util.spec_from_file_location("run_pilot_cell", _SCRIPT_PATH)
run_pilot_cell_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(run_pilot_cell_mod)


def test_run_pilot_cell_function_end_to_end():
    scores = make_synthetic_scores(
        categories=("bottle",), n_train_good=100, n_test_good=150, n_test_defect=150, separation=6.0,
    )
    result = run_pilot_cell_mod.run_pilot_cell(
        scores, "bottle", alpha_miss=0.10, alpha_fr=0.05, n_repeats=5, mondrian="category",
        good_cal_holdout_frac=None, backbone="patchcore", n_perm=200, audit_alpha=0.05,
    )
    assert result["v1"]["per_category"]["bottle"]["n_repeats"] == 5
    assert result["v1"]["per_category"]["bottle"]["tier1"]["pass_tier1"] is True
    assert result["audit"]["holm_family_size"] == 3


def test_run_pilot_cell_with_train_holdout_arm():
    scores = make_synthetic_scores(
        categories=("bottle",), n_train_good=200, n_test_good=100, n_test_defect=100, separation=6.0, seed=3,
    )
    result = run_pilot_cell_mod.run_pilot_cell(
        scores, "bottle", alpha_miss=0.10, alpha_fr=0.05, n_repeats=3, mondrian="category",
        good_cal_holdout_frac=0.2, backbone="patchcore", n_perm=100, audit_alpha=0.05,
    )
    assert result["gate_repeat0"]["good_cal_mode"] == "train-holdout"


def test_run_pilot_cell_cli(tmp_path):
    scores = make_synthetic_scores(
        categories=("bottle", "screw"), n_train_good=100, n_test_good=100, n_test_defect=100, separation=6.0,
    )
    scores_path = tmp_path / "scores.jsonl"
    _io.write_jsonl(scores_path, scores)
    out_path = tmp_path / "cell.json"
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--scores", str(scores_path), "--category", "bottle",
         "--n-repeats", "3", "--n-perm", "100", "--backbone", "patchcore", "-o", str(out_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    with open(out_path, "r", encoding="utf-8") as f:
        result = json.load(f)
    assert result["category"] == "bottle"
