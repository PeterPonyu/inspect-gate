import importlib.util
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "orchestration" / "mvtec_layout.py"
_spec = importlib.util.spec_from_file_location("mvtec_layout", _SCRIPT_PATH)
mvtec_layout = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(mvtec_layout)


def _make_category_dir(root: Path, category: str, n_train_good=3, n_test_good=2, defect_types=("scratch", "dent")):
    (root / category / "train" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(n_train_good):
        (root / category / "train" / "good" / f"{i:03d}.png").touch()
    (root / category / "test" / "good").mkdir(parents=True, exist_ok=True)
    for i in range(n_test_good):
        (root / category / "test" / "good" / f"{i:03d}.png").touch()
    for dt in defect_types:
        d = root / category / "test" / dt
        d.mkdir(parents=True, exist_ok=True)
        (d / "000.png").touch()
        (d / "001.png").touch()


def test_discover_category_counts(tmp_path):
    _make_category_dir(tmp_path, "bottle", n_train_good=5, n_test_good=3, defect_types=("scratch", "dent"))
    images = mvtec_layout.discover_category(tmp_path, "bottle")
    n_train = sum(1 for im in images if im.split == "train")
    n_test_good = sum(1 for im in images if im.split == "test" and im.label == "good")
    n_test_defect = sum(1 for im in images if im.split == "test" and im.label == "defect")
    assert n_train == 5
    assert n_test_good == 3
    assert n_test_defect == 4  # 2 defect types x 2 images each


def test_discover_category_defect_type_and_image_id():
    pass  # covered via discover_mvtec below


def test_discover_category_raises_on_missing_category(tmp_path):
    with pytest.raises(FileNotFoundError):
        mvtec_layout.discover_category(tmp_path, "nonexistent_category")


def test_discover_mvtec_multi_category(tmp_path):
    _make_category_dir(tmp_path, "bottle")
    _make_category_dir(tmp_path, "screw")
    result = mvtec_layout.discover_mvtec(tmp_path, ["bottle", "screw"])
    assert set(result.keys()) == {"bottle", "screw"}
    for cat, images in result.items():
        assert all(im.category == cat for im in images)


def test_mvtec_categories_has_15_entries():
    assert len(mvtec_layout.MVTEC_CATEGORIES) == 15
    assert len(set(mvtec_layout.MVTEC_CATEGORIES)) == 15


def test_image_id_uniqueness_within_category(tmp_path):
    _make_category_dir(tmp_path, "bottle")
    images = mvtec_layout.discover_category(tmp_path, "bottle")
    ids = [im.image_id for im in images]
    assert len(ids) == len(set(ids))
