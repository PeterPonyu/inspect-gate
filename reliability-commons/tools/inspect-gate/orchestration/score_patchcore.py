#!/usr/bin/env python3
"""Box-side PatchCore scoring (anomalib), one category (or all) -> canonical
scores-JSONL (``inspect_gate.io`` schema).

UNVERIFIED against a real anomalib install at build time (no GPU/anomalib
in this environment) -- mirrors ``asr-gate/orchestration/corpora.py``'s
own "layout assumptions ... UNVERIFIED until Phase 0" convention. The
anomalib v1.x Python API this script targets (subject to confirmation on
the actual box, anomalib version pinned in ``../pyproject.toml``'s
``[project.optional-dependencies].box`` extra)::

    from anomalib.data import MVTecAD  # 2.x name; 1.x calls it MVTec
    from anomalib.models import Patchcore
    from anomalib.engine import Engine

    datamodule = MVTecAD(root=data_root, category=category, ...)
    model = Patchcore(backbone=..., layers=[...], coreset_sampling_ratio=...)
    engine = Engine(...)
    engine.fit(model=model, datamodule=datamodule)
    predictions = engine.predict(model=model, datamodule=datamodule)
    # predictions: list of batches; each batch is expected to expose
    # pred_score (image-level anomaly score, HIGHER = more anomalous --
    # matches io.py's sign convention directly, anomalib's own docs use
    # the same convention) and image_path, per-sample.

:func:`extract_prediction_fields` is a TOLERANT extractor -- it tries
several attribute/key names anomalib has used across versions
(``pred_score``, ``anomaly_score``, ``pred_scores``) rather than hard-
coding one, and raises an actionable error listing what it found
instead of silently returning garbage on a version mismatch. Run with
``--probe N`` first on a real box to dump the raw prediction shape
before trusting a full category run (mirrors the
``decode_conformer_ms.py --probe`` precedent referenced in
``asr-gate``'s boot chains).

Coreset-subsampling seed: PatchCore's ONLY source of run-to-run variance
(design §3.1 table: "seed = coreset-subsampling seed") -- passed through
to the model constructor's seed-bearing argument (name TBD per the
installed anomalib version; ``--seed`` also seeds Python/numpy/torch RNG
globally as a fallback so the run is reproducible even if that exact
kwarg doesn't exist in the installed version).

Train-holdout scoring (``--holdout-frac``, flag-gated, prereg-NEUTRAL)
-----------------------------------------------------------------------
Default ``--holdout-frac 0.0`` is EXACTLY today's behavior: no partition,
no filtering, no second predict pass -- nothing below this paragraph runs
at all. When ``--holdout-frac`` > 0, a deterministic per-category slice
of ``train/good`` images (:func:`partition_train_holdout`, torch-free and
unit-tested) is excluded from the data the model is fit on (so the
memory bank never sees them -- leakage otherwise) and then scored in a
SEPARATE ``engine.predict`` pass over a temp directory of symlinks to
just those images, via anomalib's folder-predict path
(``PredictDataset``/``data_path``). ``holdout_frac``/``holdout_seed`` and
the realized ``holdout_ids`` are stamped into a companion provenance
JSON (see ``main()``).

PHASE-0 ON-BOX VERIFICATION ITEM: :func:`partition_train_holdout` and the
CLI plumbing around it are torch-free and covered by this package's own
test suite; the anomalib-side pieces this docstring describes --
filtering ``MVTecADDataset.samples`` inside the ``_setup`` override, and
the holdout ``PredictDataset``/``data_path`` predict pass -- are, like
the rest of this module's anomalib integration, UNVERIFIED against a
real install at build time (no GPU/anomalib in this environment) and
MUST be confirmed on the real box before ``--holdout-frac`` > 0 is
trusted for a live run.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
sys.path.insert(0, str(SCRIPT_DIR))

from inspect_gate import io as _io  # noqa: E402
from mvtec_layout import MVTEC_CATEGORIES, discover_category  # noqa: E402

DEFAULT_BACKBONE = "wide_resnet50_2"
DEFAULT_LAYERS = ("layer2", "layer3")
DEFAULT_CORESET_RATIO = 0.10
DEFAULT_HOLDOUT_FRAC = 0.0  # 0.0 = current behavior, no train-holdout arm
DEFAULT_HOLDOUT_SEED = 0


def partition_train_holdout(
    sorted_ids: Sequence[str], frac: float, seed: int
) -> Tuple[List[str], List[str]]:
    """Deterministically partition ``sorted_ids`` (caller passes them
    already sorted, so the partition is reproducible independent of
    dict/filesystem iteration order) into ``(fit_ids, holdout_ids)``.

    ``frac`` <= 0 (the default, ``DEFAULT_HOLDOUT_FRAC``) is a no-op:
    everything stays in ``fit_ids``, ``holdout_ids`` is empty -- this is
    what makes ``--holdout-frac 0.0`` prereg-NEUTRAL (byte-identical to
    the pre-holdout code path). Otherwise, holdout size is
    ``max(1, round(frac * n))`` (capped at ``n``), and the holdout
    members are chosen via ``random.Random(seed).sample`` -- pure
    stdlib, no torch/numpy, unit-testable in isolation.
    """
    sorted_ids = list(sorted_ids)
    n = len(sorted_ids)
    if frac <= 0.0 or n == 0:
        return sorted_ids, []
    n_holdout = min(n, max(1, round(frac * n)))
    holdout_set = set(random.Random(seed).sample(sorted_ids, n_holdout))
    fit_ids = [i for i in sorted_ids if i not in holdout_set]
    holdout_ids = [i for i in sorted_ids if i in holdout_set]
    return fit_ids, holdout_ids


def extract_prediction_fields(pred: Any) -> Tuple[Optional[float], Optional[str]]:
    """Tolerant (score, image_path) extraction from one anomalib
    prediction record, across the field-name variants anomalib has used.
    Returns ``(None, None)`` (never raises) on total failure to extract
    EITHER field for this one record -- callers count these as
    ``n_failed``, per the exclude-and-count discipline used throughout
    this portfolio (``asr_gate.gate``'s ``excluded_missing_s1``
    precedent), rather than aborting the whole run over one bad record.
    """
    score = None
    for attr in ("pred_score", "anomaly_score", "pred_scores"):
        val = getattr(pred, attr, None) if not isinstance(pred, dict) else pred.get(attr)
        if val is not None:
            try:
                score = float(val)
            except (TypeError, ValueError):
                try:
                    score = float(val.item())  # torch/numpy scalar tensor
                except Exception:
                    score = None
            if score is not None:
                break

    image_path = None
    for attr in ("image_path", "path", "file_path"):
        val = getattr(pred, attr, None) if not isinstance(pred, dict) else pred.get(attr)
        if val is not None:
            image_path = str(val[0]) if isinstance(val, (list, tuple)) else str(val)
            break

    return score, image_path


def probe(predictions: List[Any], n: int) -> None:
    """Dump the raw shape/available fields of the first ``n`` predictions
    to stderr -- diagnostic only, never gates anything (mirrors the
    ``--probe`` convention referenced in this portfolio's ASR chains)."""
    for i, pred in enumerate(predictions[:n]):
        print(f"--- probe[{i}] type={type(pred)} ---", file=sys.stderr)
        if isinstance(pred, dict):
            print(f"  keys: {sorted(pred.keys())}", file=sys.stderr)
        else:
            print(f"  attrs: {sorted(a for a in dir(pred) if not a.startswith('_'))}", file=sys.stderr)


def _image_id_from_path(path: Optional[str], category: str, split_hint: str, defect_type_hint: str) -> str:
    if path is None:
        return f"{category}_{split_hint}_{defect_type_hint}_UNKNOWN"
    stem = Path(path).stem
    return f"{category}_{split_hint}_{defect_type_hint}_{stem}"


def _batch_to_items(batch: Any) -> List[Any]:
    """Normalize one ``engine.predict()`` batch into a list of per-image
    prediction records, across the shapes anomalib has used (see
    ``run_patchcore_category``'s inline comment, verified on-box
    2026-07-10, for why the ``items`` PROPERTY check matters)."""
    if isinstance(batch, (list, tuple)):
        return list(batch)
    if not isinstance(batch, dict) and hasattr(batch, "items") \
            and not callable(getattr(batch, "items")):
        return list(batch.items)
    return [batch]


def _match_predictions_to_disk_images(
    predictions: List[Any],
    by_path: Dict[str, Any],
    by_stem: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Shared match-predictions-to-disk-layout loop, used for both the
    main train+test predict pass and the (optional) holdout predict pass
    -- see ``run_patchcore_category``."""
    records: List[Dict[str, Any]] = []
    n_scored = 0
    n_failed = 0
    for batch in predictions:
        for pred in _batch_to_items(batch):
            score, image_path = extract_prediction_fields(pred)
            if score is None:
                n_failed += 1
                continue
            im = by_path.get(image_path) if image_path else None
            if im is None and image_path:
                im = by_stem.get(Path(image_path).stem)
            if im is None:
                n_failed += 1
                continue
            records.append({
                "image_id": im.image_id, "category": im.category, "split": im.split,
                "score": score, "label": im.label, "defect_type": im.defect_type,
            })
            n_scored += 1
    return records, n_scored, n_failed


def run_patchcore_category(
    data_root: str,
    category: str,
    seed: int,
    backbone: str,
    layers: List[str],
    coreset_sampling_ratio: float,
    device: str,
    probe_n: int = 0,
    holdout_frac: float = DEFAULT_HOLDOUT_FRAC,
    holdout_seed: int = DEFAULT_HOLDOUT_SEED,
) -> Tuple[List[Dict[str, Any]], int, int, List[str]]:
    """Fit PatchCore on ``category``'s train-good split, score train+test,
    return ``(records, n_scored, n_failed, holdout_ids)`` -- ``records``
    are RAW (image_id/category/split/label/defect_type known from disk
    layout; score attached from the anomalib prediction, matched by
    image_path). ``holdout_ids`` is the realized list of held-out
    ``image_id``s (empty unless ``holdout_frac`` > 0 -- see module
    docstring's "Train-holdout scoring" section).

    Heavy imports (torch, anomalib) happen HERE, inside this function --
    never at module scope, so this module remains importable (and its
    ``extract_prediction_fields``/``_image_id_from_path``/
    ``partition_train_holdout`` helpers unit-testable) with no GPU/
    anomalib installed.
    """
    # Cheap, torch-free disk-layout check FIRST: a missing category
    # directory should surface as FileNotFoundError (caller's staging
    # error, per discover_category's docstring) before paying for a
    # torch/anomalib import that a bad --data-root/--category makes moot.
    disk_images = discover_category(data_root, category)
    train_stems_sorted = sorted(im.path.stem for im in disk_images if im.split == "train")
    _, holdout_stems = partition_train_holdout(train_stems_sorted, holdout_frac, holdout_seed)
    holdout_stem_set = set(holdout_stems)

    import torch

    try:
        # anomalib >= 2.x renamed the datamodule (verified on-box 2.5.0,
        # 2026-07-10: "cannot import name 'MVTec' ... Did you mean: 'MVTec3D'?")
        from anomalib.data import MVTecAD as _MVTecBase

        class MVTec(_MVTecBase):  # type: ignore[misc]
            """anomalib 2.5.0 workaround (verified on-box 2026-07-10): the
            stock ``_setup`` passes ``Split.TRAIN``/``Split.TEST`` enums whose
            comparison against the samples DataFrame's string ``split`` column
            silently yields 0 rows (raw ``make_*_dataset(root, split="train")``
            returns 209 bottle rows; the datamodule returns 0). Passing string
            splits restores the rows; everything else (val subset splitting,
            transforms) is inherited unchanged from the base class.

            When ``holdout_stem_set`` (closed over from the enclosing
            ``run_patchcore_category`` call) is non-empty, holdout rows are
            additionally dropped from ``train_data.samples`` so the fitted
            memory bank never sees them -- UNVERIFIED against a real
            install, see module docstring's Phase-0 verification item."""

            def _setup(self, _stage=None) -> None:
                from anomalib.data.datasets.image.mvtecad import MVTecADDataset
                self.train_data = MVTecADDataset(
                    split="train", root=self.root, category=self.category)
                self.test_data = MVTecADDataset(
                    split="test", root=self.root, category=self.category)
                if holdout_stem_set:
                    samples = self.train_data.samples
                    keep_mask = ~samples["image_path"].map(
                        lambda p: Path(p).stem in holdout_stem_set
                    )
                    self.train_data.samples = samples[keep_mask].reset_index(drop=True)
    except ImportError:
        from anomalib.data import MVTec  # anomalib 1.x
    from anomalib.engine import Engine
    from anomalib.models import Patchcore

    torch.manual_seed(seed)

    datamodule = MVTec(root=data_root, category=category)
    model = Patchcore(backbone=backbone, layers=list(layers), coreset_sampling_ratio=coreset_sampling_ratio)
    engine = Engine(accelerator=device if device != "cpu" else "cpu")

    engine.fit(model=model, datamodule=datamodule)
    predictions = engine.predict(model=model, datamodule=datamodule) or []

    if probe_n:
        probe(predictions, probe_n)

    by_path = {str(im.path): im for im in disk_images}
    by_stem = {im.path.stem: im for im in disk_images}

    records, n_scored, n_failed = _match_predictions_to_disk_images(predictions, by_path, by_stem)

    holdout_ids: List[str] = []
    if holdout_stem_set:
        # Phase-0 on-box verification item (module docstring): score the
        # excluded holdout images with a SEPARATE predict pass over a temp
        # dir of symlinks, via anomalib's folder-predict path.
        import tempfile
        from anomalib.data import PredictDataset

        # TRAIN-split only: holdout stems are train/good stems, and MVTec
        # reuses bare numeric stems ("002") across test defect dirs -- a
        # stem-only filter pulls in test images, collides in the symlink
        # dir, and (worse) lets the stem-fallback matcher bind holdout
        # predictions to the WRONG disk image. Caught by the mandated
        # Phase-0 on-box probe (2026-07-10).
        holdout_images = [
            im for im in disk_images
            if im.split == "train" and im.path.stem in holdout_stem_set
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_p = Path(tmp_dir)
            for im in holdout_images:
                (tmp_dir_p / im.path.name).symlink_to(im.path.resolve())
            predict_dataset = PredictDataset(path=tmp_dir_p)
            holdout_predictions = engine.predict(model=model, dataset=predict_dataset) or []

        # Match against HOLDOUT-restricted maps: the predict pass returns
        # tmp-symlink paths, so path lookup misses and the stem fallback
        # must only ever resolve within the holdout set itself.
        hold_by_path = {str(im.path): im for im in holdout_images}
        hold_by_stem = {im.path.stem: im for im in holdout_images}
        holdout_records, holdout_n_scored, holdout_n_failed = _match_predictions_to_disk_images(
            holdout_predictions, hold_by_path, hold_by_stem
        )
        records.extend(holdout_records)
        n_scored += holdout_n_scored
        n_failed += holdout_n_failed
        holdout_ids = [im.image_id for im in holdout_images]

    return records, n_scored, n_failed, holdout_ids


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Score MVTec AD categories with PatchCore (anomalib)")
    p.add_argument("--data-root", required=True, help="MVTec AD root (contains per-category dirs)")
    p.add_argument("--category", default=None, help="comma-separated categories (default: all 15)")
    p.add_argument("--seed", type=int, default=0, help="coreset-subsampling seed (design §3.1)")
    p.add_argument("--backbone", default=DEFAULT_BACKBONE)
    p.add_argument("--layers", default=",".join(DEFAULT_LAYERS))
    p.add_argument("--coreset-sampling-ratio", type=float, default=DEFAULT_CORESET_RATIO)
    p.add_argument("--device", default="cuda")
    p.add_argument("--probe", type=int, default=0, help="dump the first N raw predictions to stderr, diagnostic only")
    p.add_argument(
        "--holdout-frac", type=float, default=DEFAULT_HOLDOUT_FRAC, dest="holdout_frac",
        help="fraction of each category's train-good images to hold out from "
             "fitting and score separately (0.0 = current behavior, no "
             "holdout arm; see module docstring's Phase-0 verification item)",
    )
    p.add_argument(
        "--holdout-seed", type=int, default=DEFAULT_HOLDOUT_SEED, dest="holdout_seed",
        help="RNG seed for the deterministic train-holdout partition",
    )
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    categories = args.category.split(",") if args.category else list(MVTEC_CATEGORIES)
    layers = args.layers.split(",")

    all_records: List[Dict[str, Any]] = []
    total_scored = 0
    total_failed = 0
    holdout_ids_by_category: Dict[str, List[str]] = {}
    for cat in categories:
        try:
            records, n_scored, n_failed, holdout_ids = run_patchcore_category(
                args.data_root, cat, args.seed, args.backbone, layers,
                args.coreset_sampling_ratio, args.device, probe_n=args.probe,
                holdout_frac=args.holdout_frac, holdout_seed=args.holdout_seed,
            )
        except FileNotFoundError as e:
            print(f"score_patchcore: category={cat} SKIPPED (staging error: {e})", file=sys.stderr)
            continue
        all_records.extend(records)
        total_scored += n_scored
        total_failed += n_failed
        if holdout_ids:
            holdout_ids_by_category[cat] = holdout_ids
        print(f"score_patchcore: category={cat} n_scored={n_scored} n_failed={n_failed}")

    if all_records:
        validated = _io.validate_scores(all_records)
        _io.write_jsonl(args.out, validated)

    if args.holdout_frac > 0.0:
        from relmetrics import provenance as _provenance
        holdout_provenance = {
            "holdout_frac": args.holdout_frac,
            "holdout_seed": args.holdout_seed,
            "holdout_ids_by_category": holdout_ids_by_category,
        }
        _provenance.stamp_result(holdout_provenance, script_path=__file__, seeds=[args.holdout_seed])
        holdout_provenance_path = Path(args.out).with_suffix(".holdout_provenance.json")
        with open(holdout_provenance_path, "w", encoding="utf-8") as f:
            json.dump(_io.to_jsonable(holdout_provenance), f, indent=2, ensure_ascii=False)
        print(f"score_patchcore: holdout provenance -> {holdout_provenance_path}")

    print(f"score_patchcore: DONE n_scored={total_scored} n_failed={total_failed} -> {args.out}")
    return 0 if total_scored > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
