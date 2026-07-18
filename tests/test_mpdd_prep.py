"""Torch-free unit tests for orchestration/mpdd_prep.py (the MPDD staging
verifier) and the MPDD_CATEGORIES roster, against synthetic MVTec-layout
fixtures -- no real MPDD images, no GPU."""
import importlib.util
import json
from pathlib import Path

import pytest

_ORCH = Path(__file__).resolve().parents[1] / "orchestration"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


mpdd_prep = _load("mpdd_prep", _ORCH / "mpdd_prep.py")
mvtec_layout = _load("mvtec_layout", _ORCH / "mvtec_layout.py")


def _make_mpdd_category(root, cat, n_train_good, n_test_good, defect_types):
    (root / cat / "train" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(n_train_good):
        (root / cat / "train" / "good" / f"{i:03d}.png").touch()
    (root / cat / "test" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(n_test_good):
        (root / cat / "test" / "good" / f"{i:03d}.png").touch()
    for dt, n in defect_types.items():
        d = root / cat / "test" / dt
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            (d / f"{i:03d}.png").touch()


def _make_full_mpdd(root, n_train_good=3, n_test_good=2, defect_types=None):
    defect_types = defect_types or {"scratch": 2, "hole": 1}
    for cat in mvtec_layout.MPDD_CATEGORIES:
        _make_mpdd_category(root, cat, n_train_good, n_test_good, defect_types)


def test_mpdd_roster_has_6_entries():
    assert len(mvtec_layout.MPDD_CATEGORIES) == 6
    assert len(set(mvtec_layout.MPDD_CATEGORIES)) == 6
    assert "bracket_black" in mvtec_layout.MPDD_CATEGORIES
    assert "tubes" in mvtec_layout.MPDD_CATEGORIES


def test_build_manifest_counts(tmp_path):
    _make_full_mpdd(tmp_path, n_train_good=3, n_test_good=2, defect_types={"scratch": 2, "hole": 1})
    manifest = mpdd_prep.build_manifest(tmp_path)
    assert manifest["totals"]["train_good"] == 6 * 3
    assert manifest["totals"]["test_good"] == 6 * 2
    assert manifest["totals"]["test_defect"] == 6 * 3  # scratch 2 + hole 1
    assert manifest["totals"]["test_total"] == 6 * 5
    c = manifest["per_category"]["bracket_black"]
    assert c["n_train_good"] == 3 and c["n_test_good"] == 2 and c["n_test_defect"] == 3
    assert c["defect_type_counts"] == {"scratch": 2, "hole": 1}
    # test_split roster is the (defect_type, stem) join key, collision-free
    keys = {tuple(x) for x in c["test_split"]}
    assert len(keys) == len(c["test_split"]) == 5


def test_verify_passes_and_writes_manifest(tmp_path):
    _make_full_mpdd(tmp_path, n_train_good=3, n_test_good=2, defect_types={"scratch": 2, "hole": 1})
    out = tmp_path / "manifest.json"
    mpdd_prep.verify(tmp_path, out, expect_train_good=18, expect_test=30, archive_sha256="deadbeef")
    assert out.exists()
    m = json.loads(out.read_text())
    assert m["archive_sha256"] == "deadbeef"
    assert m["totals"]["train_good"] == 18 and m["totals"]["test_total"] == 30


def test_verify_refuses_on_wrong_total(tmp_path):
    _make_full_mpdd(tmp_path)
    with pytest.raises(SystemExit):
        mpdd_prep.verify(tmp_path, tmp_path / "m.json", expect_train_good=999, expect_test=30)


def test_verify_refuses_on_missing_category(tmp_path):
    _make_full_mpdd(tmp_path)
    # nuke one category dir entirely -> discover_category raises FileNotFoundError
    import shutil
    shutil.rmtree(tmp_path / "tubes")
    with pytest.raises(FileNotFoundError):
        mpdd_prep.build_manifest(tmp_path)


def test_verify_refuses_on_empty_test_good(tmp_path):
    _make_full_mpdd(tmp_path)
    # remove every test/good image from one category -> empty split cell refuse
    for p in (tmp_path / "connector" / "test" / "good").glob("*.png"):
        p.unlink()
    with pytest.raises(SystemExit):
        mpdd_prep.build_manifest(tmp_path)
