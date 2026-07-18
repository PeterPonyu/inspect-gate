"""Repeated stratified calibration/evaluation splits of the MVTec test set
(design §3.2, the "subtle part, stated honestly").

G1's calibration data (labeled defectives) exists ONLY in the MVTec test
set -- train is defect-free by construction. The protocol this module
implements:

    test set, per category -> repeated stratified splits: 50% calibration
    / 50% evaluation, stratified by good/defective (and by defect_type
    where counts permit), R = 20 repeats per (backbone, category, seed)
    with split-seed = repeat index; no image ever in both halves of one
    repeat.

The split role (calibration vs evaluation) is deliberately NOT persisted
into the canonical scores-JSONL (see ``io.py``'s ``split`` field
docstring) -- it is a per-repeat, in-memory partition computed here and
consumed immediately by ``gate.calibrate_gate`` / ``certify.py``, exactly
mirroring how ``asr-gate.gate.split_by_speaker`` produces an ephemeral
fit/conformalize partition rather than a persisted column.

Stratification unit: the (category, label) cell, stratified further by
defect_type WITHIN the defective cell when ``by_defect_type=True`` and
every defect_type in that category has enough images to split without an
empty half (see ``min_defect_type_n`` below) -- falling back to a plain
category x label split (never a hard failure) when it doesn't, exactly
the same "refuse the finer stratum, not the whole split" discipline as
``gate.py``'s Mondrian defect-type fallback.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "SplitError",
    "stratified_cal_eval_split",
    "repeated_stratified_splits",
    "train_good_holdout_split",
]


class SplitError(ValueError):
    """Raised on any splits.py precondition violation."""


def _stratum_key(rec: Dict[str, Any], by_defect_type: bool) -> Tuple[str, ...]:
    if by_defect_type and rec["label"] == "defect":
        return (rec["category"], rec["label"], rec["defect_type"])
    return (rec["category"], rec["label"])


def stratified_cal_eval_split(
    test_records: List[Dict[str, Any]],
    repeat_seed: int,
    frac: float = 0.5,
    by_defect_type: bool = False,
    min_defect_type_n: int = 2,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """One 50/50-by-default stratified calibration/evaluation split of the
    MVTec ``test`` split, seeded by ``repeat_seed`` (design §3.2: "split-
    seed = repeat index").

    Parameters
    ----------
    test_records:
        Canonical score records with ``split == "test"`` (raises
        :class:`SplitError` if any record has a different split -- this
        function is test-set-only per the protocol; callers filter
        upstream, e.g. ``[r for r in scores if r["split"] == "test"]``).
    repeat_seed:
        RNG seed for THIS repeat; distinct repeats use distinct seeds
        (the design's ``R = 20`` repeats use ``split-seed = repeat
        index``, i.e. call this with ``repeat_seed=0..19``).
    frac:
        Fraction of each stratum routed to the calibration half.
    by_defect_type:
        If True, stratify the defective cell further by ``defect_type``
        WITHIN each category, falling back to plain category-level
        stratification for any defect_type with fewer than
        ``min_defect_type_n`` images in that category (never fails the
        whole split over one sparse defect type).
    min_defect_type_n:
        Minimum per-(category, defect_type) count required to stratify at
        that granularity; below it, those images fall back into the
        plain (category, "defect") stratum.

    Returns
    -------
    (cal_records, eval_records)
        Disjoint partition of ``test_records``; every stratum is split
        independently so BOTH halves see every (category, label) cell
        present in the input (down to a 1-image stratum, which routes
        entirely to whichever half ``frac`` rounds it into -- flagged by
        the caller via realized post-split counts, not by this function).
    """
    if not 0.0 < frac < 1.0:
        raise SplitError(f"frac must be in (0, 1), got {frac}")
    bad_split = [r["image_id"] for r in test_records if r["split"] != "test"]
    if bad_split:
        raise SplitError(
            f"stratified_cal_eval_split: {len(bad_split)} record(s) are not "
            f"split='test' (e.g. {bad_split[:3]}) -- this function only "
            "splits the MVTec test set (design §3.2); train images are "
            "either used for backbone fitting or routed through "
            "train_good_holdout_split, never through here."
        )

    if by_defect_type:
        dt_counts: Dict[Tuple[str, str], int] = {}
        for r in test_records:
            if r["label"] == "defect":
                dt_counts[(r["category"], r["defect_type"])] = (
                    dt_counts.get((r["category"], r["defect_type"]), 0) + 1
                )
        sparse = {k for k, n in dt_counts.items() if n < min_defect_type_n}
    else:
        sparse = set()

    strata: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
    for r in test_records:
        use_dt = by_defect_type and r["label"] == "defect" and (
            (r["category"], r["defect_type"]) not in sparse
        )
        key = _stratum_key(r, use_dt)
        strata.setdefault(key, []).append(r)

    rng = np.random.default_rng(repeat_seed)
    cal: List[Dict[str, Any]] = []
    ev: List[Dict[str, Any]] = []
    for key in sorted(strata.keys()):
        members = strata[key]
        n = len(members)
        perm = rng.permutation(n)
        n_cal = int(round(frac * n))
        n_cal = min(max(n_cal, 0), n)
        cal_idx = set(perm[:n_cal].tolist())
        for i, m in enumerate(members):
            (cal if i in cal_idx else ev).append(m)

    return cal, ev


def repeated_stratified_splits(
    test_records: List[Dict[str, Any]],
    n_repeats: int = 20,
    frac: float = 0.5,
    by_defect_type: bool = False,
    min_defect_type_n: int = 2,
) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
    """``R = n_repeats`` independent :func:`stratified_cal_eval_split` calls
    with ``repeat_seed = 0 .. n_repeats - 1`` (design §3.2/§3.3: "R = 20
    repeats ... with split-seed = repeat index"). Returns the list of
    ``(cal, eval)`` pairs in repeat order.
    """
    if n_repeats < 1:
        raise SplitError(f"n_repeats must be >= 1, got {n_repeats}")
    return [
        stratified_cal_eval_split(
            test_records, repeat_seed=i, frac=frac,
            by_defect_type=by_defect_type, min_defect_type_n=min_defect_type_n,
        )
        for i in range(n_repeats)
    ]


def train_good_holdout_split(
    train_records: List[Dict[str, Any]],
    holdout_frac: float = 0.2,
    seed: int = 0,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Per-category 80/20 split of ``train`` (defect-free-by-construction)
    images into {fitting pool, held-out G2 calibration pool} (design §3.2
    table, row 2: "train goods, held-out 20% per category").

    Parameters
    ----------
    train_records:
        Canonical score records with ``split == "train"`` (raises
        :class:`SplitError` on any other split, or any non-"good" label --
        MVTec train is good-only by construction; a defect record here
        indicates upstream staging corruption, not a valid input).
    holdout_frac:
        Fraction of each category's train-good images held out for the
        optional ``--good-cal train-holdout`` G2 calibration-efficiency
        arm (design §3.2).
    seed:
        RNG seed for the per-category permutation.

    Returns
    -------
    (fit_pool, holdout_pool)
        ``fit_pool`` (never scored into calibration/eval, per design §3.2
        row 1 -- backbone fitting only) and ``holdout_pool`` (candidate
        G2 good-calibration pool, admitted per category only through the
        KS exchangeability gate, see ``gate.py``).
    """
    if not 0.0 < holdout_frac < 1.0:
        raise SplitError(f"holdout_frac must be in (0, 1), got {holdout_frac}")
    bad_split = [r["image_id"] for r in train_records if r["split"] != "train"]
    if bad_split:
        raise SplitError(
            f"train_good_holdout_split: {len(bad_split)} record(s) are not "
            f"split='train' (e.g. {bad_split[:3]})"
        )
    bad_label = [r["image_id"] for r in train_records if r["label"] != "good"]
    if bad_label:
        raise SplitError(
            f"train_good_holdout_split: {len(bad_label)} train record(s) are "
            f"not label='good' (e.g. {bad_label[:3]}) -- MVTec train is "
            "defect-free by construction; this indicates a staging bug, "
            "not a valid input (design §3.2)."
        )

    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for r in train_records:
        by_cat.setdefault(r["category"], []).append(r)

    rng = np.random.default_rng(seed)
    fit_pool: List[Dict[str, Any]] = []
    holdout_pool: List[Dict[str, Any]] = []
    for cat in sorted(by_cat.keys()):
        members = by_cat[cat]
        n = len(members)
        perm = rng.permutation(n)
        n_hold = int(round(holdout_frac * n))
        n_hold = min(max(n_hold, 0), n - 1) if n > 1 else 0
        hold_idx = set(perm[:n_hold].tolist())
        for i, m in enumerate(members):
            (holdout_pool if i in hold_idx else fit_pool).append(m)

    return fit_pool, holdout_pool
