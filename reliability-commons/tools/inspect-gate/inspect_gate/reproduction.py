"""Phase-0 reproduction gate: does this run's image-AUROC match the
backbone's published/consensus number within a preregistered tolerance
(SOTA-REPRODUCTION-PLAN-2026-07-10.md §3, design addendum 2026-07-10)?

"A certified-triage paper cannot anchor its reproduction gate on numbers
that are not independently re-derivable" -- this module computes the
image-level AUROC from THIS run's own scores+labels (never trusts a
literature number as ground truth for anything except the comparison
target) and compares it against named, env-overridable constants.

AUROC, textbook formula (Mann-Whitney U / rank-sum identity, zero new
math): with ``ranks`` the average-rank-for-ties ranking of all scores
(``scipy.stats.rankdata``), and defect as the positive class (score
convention: higher = more anomalous, matches ``io.py``),

    AUROC = (sum(ranks[is_defect]) - n_pos*(n_pos+1)/2) / (n_pos * n_neg)

Reproduction targets (PLACEHOLDERS pending PREREG freeze, per the
portfolio's own rule that no literature number is trusted without a
re-derivation pass -- design §3.6/SOTA-REPRODUCTION-PLAN §3): PatchCore's
target is the design doc's own stated figure (§3.1 table: "~99.1% mean
image AUROC on MVTec AD (published)"); Dinomaly's target is NOT filled in
here (no verified official-repo number available at build time) and
defaults to ``None``, which makes :func:`reproduction_gate` refuse to
grade that backbone until ``DINOMALY_TARGET_AUROC`` is set (env var
``INSPECT_GATE_DINOMALY_TARGET_AUROC``) from the confirmed official-repo
table at Phase 0 -- never silently graded against a guessed number.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.stats import rankdata

__all__ = [
    "ReproductionError",
    "image_auroc",
    "PATCHCORE_TARGET_AUROC",
    "DINOMALY_TARGET_AUROC",
    "DEFAULT_AUROC_TOLERANCE",
    "reproduction_gate",
]

# design §3.1 table, verbatim.
PATCHCORE_TARGET_AUROC: float = float(os.environ.get("INSPECT_GATE_PATCHCORE_TARGET_AUROC", "0.991"))
# Placeholder -- no verified official-repo number at build time; overridden
# at Phase 0 once the Dinomaly repo's reported MVTec table is confirmed.
DINOMALY_TARGET_AUROC: Optional[float] = (
    float(os.environ["INSPECT_GATE_DINOMALY_TARGET_AUROC"])
    if "INSPECT_GATE_DINOMALY_TARGET_AUROC" in os.environ else None
)
# Placeholder pending PREREG freeze (SOTA-REPRODUCTION-PLAN §3: "reproduction
# target = the honest val figure ± [tolerance], disclose any gap" -- exact
# number to be preregistered at Phase 0, not literature-sourced).
DEFAULT_AUROC_TOLERANCE: float = float(os.environ.get("INSPECT_GATE_AUROC_TOLERANCE", "0.02"))


class ReproductionError(ValueError):
    """Raised on any reproduction.py precondition violation."""


def image_auroc(scores: np.ndarray, is_defect: np.ndarray) -> float:
    """Image-level AUROC (defect = positive class, higher score = more
    anomalous), via the rank-sum identity -- see module docstring."""
    scores = np.asarray(scores, dtype=float)
    is_defect = np.asarray(is_defect, dtype=bool)
    if scores.shape != is_defect.shape or scores.size == 0:
        raise ReproductionError("scores and is_defect must be equal-length, non-empty")
    n_pos = int(is_defect.sum())
    n_neg = int((~is_defect).sum())
    if n_pos == 0 or n_neg == 0:
        raise ReproductionError(
            f"image_auroc: need both classes present, got n_pos={n_pos}, n_neg={n_neg}"
        )
    ranks = rankdata(scores)
    sum_ranks_pos = float(ranks[is_defect].sum())
    auroc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auroc)


def reproduction_gate(
    records: List[Dict[str, Any]],
    backbone: str,
    tolerance: float = DEFAULT_AUROC_TOLERANCE,
) -> Dict[str, Any]:
    """Per-category + mean image-AUROC for ``records`` (one backbone,
    ``split == "test"`` records only), compared against the backbone's
    named target constant.

    Returns
    -------
    dict
        ``backbone``, ``target``, ``tolerance``, ``per_category``
        (``{category: auroc}``), ``mean_auroc``, ``min_auroc``, ``pass``
        (``mean_auroc >= target - tolerance``; ``None`` if ``target`` is
        unset, e.g. Dinomaly before Phase-0 confirms its target).
    """
    if backbone == "patchcore":
        target = PATCHCORE_TARGET_AUROC
    elif backbone == "dinomaly":
        target = DINOMALY_TARGET_AUROC
    else:
        raise ReproductionError(f"reproduction_gate: unknown backbone {backbone!r}")

    test_records = [r for r in records if r["split"] == "test"]
    if not test_records:
        raise ReproductionError("reproduction_gate: no split='test' records supplied")

    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for r in test_records:
        by_cat.setdefault(r["category"], []).append(r)

    per_category: Dict[str, float] = {}
    for cat, recs in sorted(by_cat.items()):
        scores = np.array([r["score"] for r in recs], dtype=float)
        is_defect = np.array([r["label"] == "defect" for r in recs], dtype=bool)
        per_category[cat] = image_auroc(scores, is_defect)

    aurocs = list(per_category.values())
    mean_auroc = float(np.mean(aurocs))
    min_auroc = float(np.min(aurocs))

    return {
        "backbone": backbone,
        "target": target,
        "tolerance": float(tolerance),
        "per_category": per_category,
        "mean_auroc": mean_auroc,
        "min_auroc": min_auroc,
        "n_categories": len(per_category),
        "pass": (None if target is None else bool(mean_auroc >= target - tolerance)),
    }
