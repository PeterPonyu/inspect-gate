"""MVTec AD on-disk layout helpers, shared by ``phase0.py`` and both
``score_*.py`` scripts -- the ONLY layout-aware code in this package
(mirrors ``asr-gate/orchestration``'s ``corpora.py`` precedent: one
shared discovery module rather than duplicating path assumptions).

Layout (per the published MVTec AD distribution, Bergmann et al. CVPR
2019 -- this is the standard, stable public archive layout, not an
unverified guess the way ``asr-gate``'s THCHS-30 discoverer had to be;
still worth confirming against the actual staged tarball at Phase 0
since AutoDL mirrors occasionally repack archives)::

    {data_root}/{category}/train/good/*.png
    {data_root}/{category}/test/good/*.png
    {data_root}/{category}/test/{defect_type}/*.png
    {data_root}/{category}/ground_truth/{defect_type}/*_mask.png   (unused
        by this package -- inspect-gate is image-level only, per design
        §2.2: "the gate never sees pixels, only scores+labels")

MVTEC_CATEGORIES is the frozen 15-category roster (10 objects + 5
textures, design §3.2); every ``score_*.py``/``phase0.py`` default to
this full roster but accept ``--category`` to restrict it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Union

__all__ = [
    "MVTEC_CATEGORIES",
    "MPDD_CATEGORIES",
    "MVTecImage",
    "discover_category",
    "discover_mvtec",
]

MVTEC_CATEGORIES = (
    "bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather",
    "metal_nut", "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper",
)

# MPDD (Metal Parts Defect Detection, Jezek et al., ICUMT 2021 -- the
# real painted-metal-parts benchmark added as inspect-gate's third
# dataset, post-freeze exploratory, COMPUTE-PLAN-2026-07-13.md). MPDD
# ships in NATIVE MVTec-AD layout, so ``discover_category`` /
# ``discover_mvtec`` operate on it unchanged; only this 6-category roster
# is new (mirrors the upstream Dinomaly ``dinomaly_mpdd_sep.py`` item_list
# exactly, so the reproduction target binds against the same category set).
MPDD_CATEGORIES = (
    "bracket_black", "bracket_brown", "bracket_white", "connector", "metal_plate", "tubes",
)


class MVTecImage(NamedTuple):
    """One discovered MVTec image: enough to build one canonical score
    record once a backbone assigns it a ``score`` (``io.py``'s schema)."""

    image_id: str
    category: str
    split: str          # "train" | "test"
    label: str           # "good" | "defect"
    defect_type: str     # "good" for non-defective, else the subfolder name
    path: Path


def discover_category(data_root: Union[str, Path], category: str) -> List[MVTecImage]:
    """Discover every image for ONE category under ``data_root`` (see
    module docstring for the assumed layout). Raises ``FileNotFoundError``
    with an actionable message if the category directory is absent --
    never silently returns an empty list for a genuinely-missing category
    (a truly empty-but-present directory, by contrast, returns ``[]`` and
    is the caller's problem to notice via a zero count)."""
    data_root = Path(data_root)
    cat_dir = data_root / category
    if not cat_dir.exists():
        raise FileNotFoundError(
            f"discover_category: category dir not found: {cat_dir} "
            f"(data_root={data_root}, category={category!r})"
        )

    images: List[MVTecImage] = []

    train_good_dir = cat_dir / "train" / "good"
    if train_good_dir.exists():
        for p in sorted(train_good_dir.glob("*.png")):
            images.append(MVTecImage(
                image_id=f"{category}_train_good_{p.stem}", category=category,
                split="train", label="good", defect_type="good", path=p,
            ))

    test_dir = cat_dir / "test"
    if test_dir.exists():
        for subdir in sorted(p for p in test_dir.iterdir() if p.is_dir()):
            defect_type = subdir.name
            label = "good" if defect_type == "good" else "defect"
            for p in sorted(subdir.glob("*.png")):
                images.append(MVTecImage(
                    image_id=f"{category}_test_{defect_type}_{p.stem}", category=category,
                    split="test", label=label, defect_type=defect_type, path=p,
                ))

    return images


def discover_mvtec(
    data_root: Union[str, Path], categories: Optional[Sequence[str]] = None
) -> Dict[str, List[MVTecImage]]:
    """Discover every requested category (default: all 15,
    :data:`MVTEC_CATEGORIES`) under ``data_root``. Per-category failures
    (missing directory) are NOT swallowed -- they propagate, since a
    missing category at scoring time means the staging step failed and
    should be fixed, not silently under-covered (Phase-0's job is to
    catch this before any GPU time is spent)."""
    cats = list(categories) if categories is not None else list(MVTEC_CATEGORIES)
    return {cat: discover_category(data_root, cat) for cat in cats}
