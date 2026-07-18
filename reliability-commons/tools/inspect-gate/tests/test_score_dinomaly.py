"""Mocked-boundary tests for orchestration/score_dinomaly.py: exercises
load_score_dump()/dump_ingest_category() with fake CSV/JSON dumps and a
synthetic on-disk MVTec tree, no torch/Dinomaly-repo dependency at all
(dump-ingest mode is the supported, tested path -- see the script's
module docstring)."""

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "orchestration" / "score_dinomaly.py"
_spec = importlib.util.spec_from_file_location("score_dinomaly", _SCRIPT_PATH)
score_dinomaly = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(score_dinomaly)


def _make_bottle_tree(root: Path):
    (root / "bottle" / "train" / "good").mkdir(parents=True, exist_ok=True)
    (root / "bottle" / "train" / "good" / "000.png").touch()
    (root / "bottle" / "test" / "good").mkdir(parents=True, exist_ok=True)
    (root / "bottle" / "test" / "good" / "000.png").touch()
    (root / "bottle" / "test" / "scratch").mkdir(parents=True, exist_ok=True)
    (root / "bottle" / "test" / "scratch" / "000.png").touch()


def test_load_score_dump_csv(tmp_path):
    dump_path = tmp_path / "dump.csv"
    dump_path.write_text("image_path,score\n/a/x.png,0.5\n/a/y.png,0.9\n")
    scores = score_dinomaly.load_score_dump(str(dump_path))
    assert scores["/a/x.png"] == 0.5
    assert scores["/a/y.png"] == 0.9


def test_load_score_dump_csv_skips_header_gracefully(tmp_path):
    dump_path = tmp_path / "dump.csv"
    dump_path.write_text("path,score\n/a/x.png,0.5\n")
    scores = score_dinomaly.load_score_dump(str(dump_path))
    assert scores == {"/a/x.png": 0.5}


def test_load_score_dump_json_list(tmp_path):
    dump_path = tmp_path / "dump.json"
    dump_path.write_text(json.dumps([
        {"image_path": "/a/x.png", "score": 0.3},
        {"path": "/a/y.png", "pred_score": 0.7},
    ]))
    scores = score_dinomaly.load_score_dump(str(dump_path))
    assert scores["/a/x.png"] == 0.3
    assert scores["/a/y.png"] == 0.7


def test_dump_ingest_category_matches_by_stem(tmp_path):
    _make_bottle_tree(tmp_path)
    train_path = str(tmp_path / "bottle" / "train" / "good" / "000.png")
    test_good_path = str(tmp_path / "bottle" / "test" / "good" / "000.png")
    test_defect_path = str(tmp_path / "bottle" / "test" / "scratch" / "000.png")
    dump_scores = {train_path: 0.05, test_good_path: 0.10, test_defect_path: 0.95}

    records, n_scored, n_failed = score_dinomaly.dump_ingest_category(str(tmp_path), "bottle", dump_scores)
    assert n_scored == 3
    assert n_failed == 0
    by_id = {r["image_id"]: r for r in records}
    defect_rec = next(r for r in records if r["label"] == "defect")
    assert defect_rec["score"] == 0.95
    assert defect_rec["defect_type"] == "scratch"


def test_dump_ingest_category_ingests_a_zero_score_row(tmp_path):
    # A score of exactly 0.0 is the least-anomalous score, not a "missing
    # value" -- it must survive dump_scores -> records unchanged.
    _make_bottle_tree(tmp_path)
    train_path = str(tmp_path / "bottle" / "train" / "good" / "000.png")
    dump_scores = {train_path: 0.0}

    records, n_scored, n_failed = score_dinomaly.dump_ingest_category(str(tmp_path), "bottle", dump_scores)
    assert n_scored == 1
    train_rec = next(r for r in records if r["split"] == "train")
    assert train_rec["score"] == 0.0


def test_dump_ingest_category_counts_unmatched_as_failed(tmp_path):
    _make_bottle_tree(tmp_path)
    dump_scores = {}  # nothing matches
    records, n_scored, n_failed = score_dinomaly.dump_ingest_category(str(tmp_path), "bottle", dump_scores)
    assert n_scored == 0
    assert n_failed == 3  # 3 images on disk, none matched


def test_load_score_dump_json_survives_zero_score_and_empty_path():
    # A legitimate score of 0.0 (least-anomalous possible) or an empty-
    # string path must not be treated as "missing" by an `or`-chain
    # falling through to the next candidate key.
    dump_path_data = [
        {"image_path": "/a/x.png", "score": 0.0},
        {"path": "", "pred_score": 0.5, "file": "/a/fallback.png"},
    ]
    import json as _json
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _json.dump(dump_path_data, f)
        tmp_name = f.name
    try:
        scores = score_dinomaly.load_score_dump(tmp_name)
    finally:
        Path(tmp_name).unlink()
    assert scores["/a/x.png"] == 0.0
    # empty string "" is falsy but a legitimate lookup result for "path";
    # it must be used as the key rather than falling through to "file".
    assert scores[""] == 0.5


def test_first_present_prefers_falsy_but_non_none_value():
    assert score_dinomaly._first_present({"score": 0.0, "pred_score": 0.9}, ("score", "pred_score")) == 0.0
    assert score_dinomaly._first_present({"score": None, "pred_score": 0.9}, ("score", "pred_score")) == 0.9
    assert score_dinomaly._first_present({}, ("score", "pred_score")) is None


def test_run_direct_category_refuses_with_actionable_message():
    with pytest.raises(score_dinomaly.DinomalyDirectModeUnverified, match="dump-ingest"):
        score_dinomaly.run_direct_category("/fake/repo", "/fake/ckpt", "/fake/data", "bottle", "cuda")
