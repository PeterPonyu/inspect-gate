import json

import pytest

from inspect_gate import io as _io
from tests.conftest import make_synthetic_scores


def test_validate_scores_roundtrip():
    records = make_synthetic_scores(n_train_good=5, n_test_good=5, n_test_defect=5)
    normalized = _io.validate_scores(records)
    assert len(normalized) == len(records)
    for r in normalized:
        assert set(r.keys()) == set(_io.REQUIRED_FIELDS)


def test_validate_scores_rejects_missing_field():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    del records[0]["score"]
    with pytest.raises(_io.SchemaError, match="score"):
        _io.validate_scores(records)


def test_validate_scores_rejects_bad_label():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    records[0]["label"] = "defective"  # not in VALID_LABELS
    with pytest.raises(_io.SchemaError, match="label"):
        _io.validate_scores(records)


def test_validate_scores_rejects_bad_split():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    records[0]["split"] = "val"
    with pytest.raises(_io.SchemaError, match="split"):
        _io.validate_scores(records)


def test_validate_scores_rejects_duplicate_image_id():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    records[1]["image_id"] = records[0]["image_id"]
    with pytest.raises(_io.SchemaError, match="duplicate"):
        _io.validate_scores(records)


def test_validate_scores_good_label_requires_good_defect_type():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    good_rec = next(r for r in records if r["label"] == "good")
    good_rec["defect_type"] = "scratch"
    with pytest.raises(_io.SchemaError, match="good"):
        _io.validate_scores(records)


def test_validate_scores_defect_label_rejects_good_defect_type():
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    defect_rec = next(r for r in records if r["label"] == "defect")
    defect_rec["defect_type"] = "good"
    with pytest.raises(_io.SchemaError, match="defect"):
        _io.validate_scores(records)


def test_validate_scores_rejects_empty_list():
    with pytest.raises(_io.SchemaError, match="non-empty"):
        _io.validate_scores([])


def test_load_scores_rejects_non_jsonl_extension(tmp_path):
    path = tmp_path / "scores.json"
    path.write_text("{}")
    with pytest.raises(_io.SchemaError, match="jsonl"):
        _io.load_scores(path)


def test_write_and_load_jsonl_roundtrip(tmp_path):
    records = make_synthetic_scores(n_train_good=3, n_test_good=3, n_test_defect=3)
    path = tmp_path / "scores.jsonl"
    _io.write_jsonl(path, records)
    loaded = _io.load_scores(path)
    assert len(loaded) == len(records)
    ids = {r["image_id"] for r in loaded}
    assert ids == {r["image_id"] for r in records}


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), float("-inf")])
def test_validate_scores_rejects_non_finite_score(bad_score):
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    records[0]["score"] = bad_score
    with pytest.raises(_io.SchemaError, match="finite"):
        _io.validate_scores(records)


def test_write_jsonl_atomic_no_partial_file_on_mid_write_failure(tmp_path, monkeypatch):
    records = make_synthetic_scores(n_train_good=3, n_test_good=3, n_test_defect=3)
    path = tmp_path / "scores.jsonl"

    real_dumps = json.dumps
    calls = {"n": 0}

    def flaky_dumps(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated mid-write failure")
        return real_dumps(*args, **kwargs)

    monkeypatch.setattr(_io.json, "dumps", flaky_dumps)
    with pytest.raises(RuntimeError, match="simulated mid-write failure"):
        _io.write_jsonl(path, records)

    assert not path.exists()
    assert list(tmp_path.iterdir()) == []  # the .tmp sibling is cleaned up, not left behind


def test_write_jsonl_atomic_leaves_existing_file_unchanged_on_failure(tmp_path, monkeypatch):
    records = make_synthetic_scores(n_train_good=2, n_test_good=2, n_test_defect=2)
    path = tmp_path / "scores.jsonl"
    _io.write_jsonl(path, records)
    original_content = path.read_text(encoding="utf-8")

    real_dumps = json.dumps
    calls = {"n": 0}

    def flaky_dumps(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated mid-write failure")
        return real_dumps(*args, **kwargs)

    monkeypatch.setattr(_io.json, "dumps", flaky_dumps)
    with pytest.raises(RuntimeError, match="simulated mid-write failure"):
        _io.write_jsonl(path, records)

    assert path.read_text(encoding="utf-8") == original_content


def test_category_counts():
    records = make_synthetic_scores(
        categories=("bottle", "screw"), n_train_good=5, n_test_good=10, n_test_defect=7
    )
    counts = _io.category_counts(records)
    assert set(counts) == {"bottle", "screw"}
    for cat, c in counts.items():
        assert c["n_total"] == 5 + 10 + 7
        assert c["n_good"] == 5 + 10
        assert c["n_defect"] == 7
