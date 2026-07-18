"""Torch-free unit tests for orchestration/ksdd2_prep.py (the KSDD2 ->
MVTec-layout converter/verifier) against a synthetic KSDD2 flat tree built
from real tiny PNGs -- no real KSDD2 download, no GPU. Mirrors
test_mpdd_prep.py's discipline; the one extra thing exercised here is the
GT-mask defect oracle (all-black mask == good, any nonzero pixel == defect)."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

_ORCH = Path(__file__).resolve().parents[1] / "orchestration"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ksdd2_prep = _load("ksdd2_prep", _ORCH / "ksdd2_prep.py")


def _save_png(path: Path, defect: bool) -> None:
    """Tiny 4x4 grayscale image + its paired GT mask (all-black for good, a
    single white pixel for defect)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((4, 4), 128, dtype=np.uint8)).save(path)
    mask = np.zeros((4, 4), dtype=np.uint8)
    if defect:
        mask[0, 0] = 255
    Image.fromarray(mask).save(path.with_name(f"{path.stem}_GT.png"))


def _make_ksdd2(root, n_train_good, n_train_defect, n_test_good, n_test_defect):
    idx = 0
    for _ in range(n_train_good):
        _save_png(root / "train" / f"{idx:05d}.png", defect=False); idx += 1
    for _ in range(n_train_defect):
        _save_png(root / "train" / f"{idx:05d}.png", defect=True); idx += 1
    for _ in range(n_test_good):
        _save_png(root / "test" / f"{idx:05d}.png", defect=False); idx += 1
    for _ in range(n_test_defect):
        _save_png(root / "test" / f"{idx:05d}.png", defect=True); idx += 1


def test_defect_oracle(tmp_path):
    _save_png(tmp_path / "good.png", defect=False)
    _save_png(tmp_path / "bad.png", defect=True)
    assert ksdd2_prep.is_defective(tmp_path / "good_GT.png") is False
    assert ksdd2_prep.is_defective(tmp_path / "bad_GT.png") is True


def test_discover_and_manifest_counts(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=5, n_train_defect=2, n_test_good=3, n_test_defect=2)
    discovered = ksdd2_prep.discover_ksdd2(src)
    assert len(discovered["train"]["good"]) == 5
    assert len(discovered["train"]["defect"]) == 2
    assert len(discovered["test"]["good"]) == 3
    assert len(discovered["test"]["defect"]) == 2

    manifest = ksdd2_prep.build_manifest(discovered, tmp_path / "out")
    c = manifest["per_category"]["kolektor_surface"]
    assert c["n_train_good"] == 5
    assert c["n_test_good"] == 3
    assert c["n_test_defect"] == 2
    assert c["n_test_total"] == 5
    assert c["defect_type_counts"] == {"bad": 2}
    assert manifest["excluded_train_defect"] == 2
    assert manifest["totals"] == {
        "train_good": 5, "test_good": 3, "test_defect": 2,
        "test_total": 5, "excluded_train_defect": 2,
    }
    # test roster is the (defect_type, stem) join key, collision-free
    keys = {tuple(x) for x in c["test_split"]}
    assert len(keys) == len(c["test_split"]) == 5


def test_build_tree_creates_mvtec_layout(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=5, n_train_defect=2, n_test_good=3, n_test_defect=2)
    out = tmp_path / "out"
    discovered = ksdd2_prep.discover_ksdd2(src)
    linked = ksdd2_prep.build_mvtec_tree(discovered, out)
    assert linked == {"train_good": 5, "test_good": 3, "test_defect": 2, "excluded_train_defect": 2}
    cat = out / "kolektor_surface"
    assert len(list((cat / "train" / "good").glob("*.png"))) == 5
    assert len(list((cat / "test" / "good").glob("*.png"))) == 3
    assert len(list((cat / "test" / "bad").glob("*.png"))) == 2
    # symlinks resolve to real image bytes (pipeline reads .png via glob)
    one = next((cat / "test" / "bad").glob("*.png"))
    assert one.is_symlink() and one.resolve().exists()
    # idempotent rebuild
    ksdd2_prep.build_mvtec_tree(discovered, out)
    assert len(list((cat / "train" / "good").glob("*.png"))) == 5


def test_verify_passes_and_writes_manifest(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=5, n_train_defect=2, n_test_good=3, n_test_defect=2)
    out = tmp_path / "out"
    man = tmp_path / "manifest.json"
    ksdd2_prep.verify(
        src, out, man,
        expect_train_good=5, expect_test_good=3, expect_test_defect=2,
        expect_train_defect_excluded=2, archive_sha256="deadbeef",
    )
    assert man.exists()
    m = json.loads(man.read_text())
    assert m["archive_sha256"] == "deadbeef"
    assert m["totals"]["train_good"] == 5 and m["totals"]["test_total"] == 5
    assert (out / "kolektor_surface" / "test" / "bad").is_dir()


def test_verify_refuses_on_wrong_total(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=5, n_train_defect=2, n_test_good=3, n_test_defect=2)
    with pytest.raises(SystemExit):
        ksdd2_prep.verify(src, tmp_path / "out", tmp_path / "m.json",
                          expect_train_good=999, expect_test_good=3,
                          expect_test_defect=2, expect_train_defect_excluded=2)


def test_verify_refuses_on_missing_split(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=5, n_train_defect=2, n_test_good=3, n_test_defect=2)
    import shutil
    shutil.rmtree(src / "test")
    with pytest.raises(SystemExit):
        ksdd2_prep.discover_ksdd2(src)


def test_refuses_on_missing_gt_mask(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=2, n_train_defect=0, n_test_good=2, n_test_defect=1)
    # delete one GT mask -> discovery must refuse (corrupt extraction)
    gt = next((src / "test").glob("*_GT.png"))
    gt.unlink()
    with pytest.raises(SystemExit):
        ksdd2_prep.discover_ksdd2(src)


def test_verify_refuses_on_empty_test_defect(tmp_path):
    src = tmp_path / "KSDD2"
    _make_ksdd2(src, n_train_good=3, n_train_defect=0, n_test_good=3, n_test_defect=0)
    with pytest.raises(SystemExit):
        ksdd2_prep.verify(src, tmp_path / "out", tmp_path / "m.json",
                          expect_train_good=3, expect_test_good=3,
                          expect_test_defect=0, expect_train_defect_excluded=0)
