"""V1 certificate validity: empirical coverage cells, Clopper-Pearson
intervals, the two-tier C1 pass criterion, and the K1/K2/K4/K5 kill-gate
statistics (design §1 C1, §4).

Clopper-Pearson interval
-------------------------
Textbook exact binomial confidence interval (Clopper & Pearson, 1934),
implemented via the standard beta-quantile identity -- no new statistics,
just the closed-form most stats texts derive:

    lower(k, n, conf) = Beta.ppf((1-conf)/2, k, n-k+1)          (0 if k=0)
    upper(k, n, conf) = Beta.ppf(1-(1-conf)/2, k+1, n-k)        (1 if k=n)

with the one-sided upper bound (what the design's tier-2 criterion needs)
using confidence level ``1 - alpha_conf`` in place of the two-sided
``(1-conf)/2`` split:

    upper_1sided(k, n, alpha_conf) = Beta.ppf(1 - alpha_conf, k+1, n-k)

For the ``k=0`` (zero-miss) special case this reduces to the closed form
the design doc states directly (§1): ``1 - alpha_conf**(1/n)`` --
verified algebraically and cross-checked in ``tests/test_certify.py``
against the general beta-quantile formula.

Minimum n for a zero-miss cell to be certifiable at a given target+
tolerance (design §1's worked example, generalized)
--------------------------------------------------------------------------
Solve ``1 - alpha_conf**(1/n) <= threshold`` for the smallest integer n:

    alpha_conf**(1/n) >= 1 - threshold
    (1/n) * ln(alpha_conf) >= ln(1 - threshold)         [alpha_conf < 1, ln<0]
    ln(alpha_conf) <= n * ln(1 - threshold)              [multiply by n>0]
    n >= ln(alpha_conf) / ln(1 - threshold)              [ln(1-threshold)<0,
                                                            divide flips <= to >=]

:func:`min_n_for_zero_miss_certifiable` implements this and is checked in
the test suite against the design's own worked numbers (alpha_conf=0.05,
threshold=0.13 -> n>=22).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from scipy import stats as _stats

__all__ = [
    "CertifyError",
    "clopper_pearson_interval",
    "clopper_pearson_upper",
    "min_n_for_zero_miss_certifiable",
    "coverage_cell",
    "v1_pass_tier1",
    "v1_pass_tier2",
    "aggregate_v1_cells",
    "vacuity_check_k2",
    "coverage_sanity_check_k1",
]


class CertifyError(ValueError):
    """Raised on any certify.py precondition violation."""


def clopper_pearson_interval(k: int, n: int, confidence: float = 0.95) -> Sequence[float]:
    """Two-sided exact binomial CI for k successes out of n trials."""
    if n <= 0:
        raise CertifyError(f"n must be > 0, got {n}")
    if not 0 <= k <= n:
        raise CertifyError(f"k must be in [0, n], got k={k}, n={n}")
    if not 0.0 < confidence < 1.0:
        raise CertifyError(f"confidence must be in (0, 1), got {confidence}")
    alpha = 1.0 - confidence
    lo = 0.0 if k == 0 else float(_stats.beta.ppf(alpha / 2.0, k, n - k + 1))
    hi = 1.0 if k == n else float(_stats.beta.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return (lo, hi)


def clopper_pearson_upper(k: int, n: int, confidence: float = 0.95) -> float:
    """One-sided exact binomial upper confidence bound for k/n."""
    if n <= 0:
        raise CertifyError(f"n must be > 0, got {n}")
    if not 0 <= k <= n:
        raise CertifyError(f"k must be in [0, n], got k={k}, n={n}")
    if not 0.0 < confidence < 1.0:
        raise CertifyError(f"confidence must be in (0, 1), got {confidence}")
    alpha_conf = 1.0 - confidence
    if k == n:
        return 1.0
    return float(_stats.beta.ppf(1.0 - alpha_conf, k + 1, n - k))


def min_n_for_zero_miss_certifiable(threshold: float, confidence: float = 0.95) -> int:
    """Smallest n such that a ZERO-miss cell's one-sided CP upper bound at
    ``confidence`` is <= ``threshold`` (design §1's worked example,
    generalized -- see module docstring for the derivation)."""
    if not 0.0 < threshold < 1.0:
        raise CertifyError(f"threshold must be in (0, 1), got {threshold}")
    if not 0.0 < confidence < 1.0:
        raise CertifyError(f"confidence must be in (0, 1), got {confidence}")
    alpha_conf = 1.0 - confidence
    n_real = math.log(alpha_conf) / math.log(1.0 - threshold)
    return int(math.ceil(n_real - 1e-9))


def coverage_cell(
    eval_records: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Empirical escaped-defect and false-reject rates for one (category,
    backbone, repeat) evaluation cell, plus Clopper-Pearson intervals.

    Parameters
    ----------
    eval_records:
        Canonical score records (the evaluation half; ``label`` required).
    decisions:
        ``gate.route_gate(...)["decisions"]`` restricted to the SAME
        ``image_id`` set as ``eval_records`` (one-to-one; raises on
        mismatch).
    confidence:
        Two-sided CI / one-sided UB confidence level (design default 0.95).

    Returns
    -------
    dict
        ``n_eval_def``, ``n_eval_good``, ``n_escaped`` (auto-pass among
        defectives), ``n_false_reject`` (auto-reject among goods),
        ``escaped_defect_rate``, ``false_reject_rate``, ``escaped_ci``,
        ``false_reject_ci`` (two-sided CP), ``escaped_ub_1sided``,
        ``false_reject_ub_1sided`` (one-sided CP UB at ``confidence``),
        ``n_defer``, ``deferral_rate`` (over ALL eval images, not just
        defectives/goods).
    """
    by_id = {r["image_id"]: r for r in eval_records}
    dec_by_id = {d["image_id"]: d for d in decisions}
    missing = set(by_id) - set(dec_by_id)
    if missing:
        raise CertifyError(
            f"coverage_cell: {len(missing)} eval record(s) have no matching "
            f"decision (e.g. {sorted(missing)[:3]})"
        )

    n_def = 0
    n_escaped = 0
    n_good = 0
    n_false_reject = 0
    n_defer = 0
    n_total = 0
    for image_id, r in by_id.items():
        d = dec_by_id[image_id]
        n_total += 1
        if d["action"] == "defer":
            n_defer += 1
        if r["label"] == "defect":
            n_def += 1
            if d["action"] == "auto-pass":
                n_escaped += 1
        else:
            n_good += 1
            if d["action"] == "auto-reject":
                n_false_reject += 1

    escaped_rate = (n_escaped / n_def) if n_def > 0 else float("nan")
    fr_rate = (n_false_reject / n_good) if n_good > 0 else float("nan")
    escaped_ci = clopper_pearson_interval(n_escaped, n_def, confidence) if n_def > 0 else (float("nan"), float("nan"))
    fr_ci = clopper_pearson_interval(n_false_reject, n_good, confidence) if n_good > 0 else (float("nan"), float("nan"))
    escaped_ub = clopper_pearson_upper(n_escaped, n_def, confidence) if n_def > 0 else float("nan")
    fr_ub = clopper_pearson_upper(n_false_reject, n_good, confidence) if n_good > 0 else float("nan")

    return {
        "n_eval_def": n_def,
        "n_eval_good": n_good,
        "n_escaped": n_escaped,
        "n_false_reject": n_false_reject,
        "escaped_defect_rate": escaped_rate,
        "false_reject_rate": fr_rate,
        "escaped_ci": list(escaped_ci),
        "false_reject_ci": list(fr_ci),
        "escaped_ub_1sided": escaped_ub,
        "false_reject_ub_1sided": fr_ub,
        "n_defer": n_defer,
        "n_total": n_total,
        "deferral_rate": (n_defer / n_total) if n_total > 0 else float("nan"),
    }


def v1_pass_tier1(
    cells: List[Dict[str, Any]], alpha_miss: float, alpha_fr: float, tolerance_pp: float = 0.03
) -> Dict[str, Any]:
    """Tier-1 V1 pass criterion (design §1 C1): mean empirical
    escaped-defect/false-reject rate over repeats <= target + tolerance,
    for EVERY cell (point estimate, no power requirement).

    Parameters
    ----------
    cells:
        List of :func:`coverage_cell`-shaped dicts for the R repeats of
        ONE (category, backbone) cell.
    alpha_miss, alpha_fr, tolerance_pp:
        Targets and the additive tolerance (design default 3pp = 0.03).
    """
    if not cells:
        raise CertifyError("v1_pass_tier1: cells must be non-empty")
    escaped = np.array([c["escaped_defect_rate"] for c in cells], dtype=float)
    fr = np.array([c["false_reject_rate"] for c in cells], dtype=float)
    mean_escaped = float(np.nanmean(escaped))
    mean_fr = float(np.nanmean(fr))
    return {
        "mean_escaped_defect_rate": mean_escaped,
        "mean_false_reject_rate": mean_fr,
        "pass_escaped": bool(mean_escaped <= alpha_miss + tolerance_pp),
        "pass_false_reject": bool(mean_fr <= alpha_fr + tolerance_pp),
        "pass_tier1": bool(
            mean_escaped <= alpha_miss + tolerance_pp
            and mean_fr <= alpha_fr + tolerance_pp
        ),
    }


def v1_pass_tier2(
    cells: List[Dict[str, Any]],
    alpha_miss: float,
    alpha_fr: float,
    tolerance_pp: float = 0.03,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Tier-2 V1 pass criterion (design §1 C1): one-sided CP UB <=
    target + tolerance, applied only to cells with enough eval-half
    defectives to be passable at all (design's power floor -- pooled
    across the R repeats' realized n_eval_def, since the criterion is
    evaluated per (category, backbone) not per repeat).

    Parameters
    ----------
    cells:
        List of :func:`coverage_cell`-shaped dicts for the R repeats of
        ONE (category, backbone) cell.

    Returns
    -------
    dict
        ``n_eval_def_total`` (pooled over repeats), ``min_n_required``
        (:func:`min_n_for_zero_miss_certifiable` at
        ``alpha_miss + tolerance_pp``), ``underpowered`` (bool),
        ``pooled_escaped_rate``/``ub_1sided`` (pooled k/n across repeats,
        one CP UB on the pooled counts -- the design's "adequately
        powered cells only" criterion), and the mirror for false-reject.
    """
    if not cells:
        raise CertifyError("v1_pass_tier2: cells must be non-empty")
    n_def_total = sum(c["n_eval_def"] for c in cells)
    n_escaped_total = sum(c["n_escaped"] for c in cells)
    n_good_total = sum(c["n_eval_good"] for c in cells)
    n_fr_total = sum(c["n_false_reject"] for c in cells)

    min_n_def = min_n_for_zero_miss_certifiable(alpha_miss + tolerance_pp, confidence)
    min_n_good = min_n_for_zero_miss_certifiable(alpha_fr + tolerance_pp, confidence)

    underpowered_def = n_def_total < min_n_def
    underpowered_good = n_good_total < min_n_good

    escaped_ub = (
        clopper_pearson_upper(n_escaped_total, n_def_total, confidence)
        if n_def_total > 0 else float("nan")
    )
    fr_ub = (
        clopper_pearson_upper(n_fr_total, n_good_total, confidence)
        if n_good_total > 0 else float("nan")
    )

    return {
        "n_eval_def_total": n_def_total,
        "n_eval_good_total": n_good_total,
        "min_n_def_required": min_n_def,
        "min_n_good_required": min_n_good,
        "underpowered_escaped": bool(underpowered_def),
        "underpowered_false_reject": bool(underpowered_good),
        "pooled_escaped_rate": (n_escaped_total / n_def_total) if n_def_total > 0 else float("nan"),
        "pooled_false_reject_rate": (n_fr_total / n_good_total) if n_good_total > 0 else float("nan"),
        "escaped_ub_1sided": escaped_ub,
        "false_reject_ub_1sided": fr_ub,
        "pass_escaped": (
            None if underpowered_def else bool(escaped_ub <= alpha_miss + tolerance_pp)
        ),
        "pass_false_reject": (
            None if underpowered_good else bool(fr_ub <= alpha_fr + tolerance_pp)
        ),
    }


def aggregate_v1_cells(
    cells_by_category: Dict[str, List[Dict[str, Any]]],
    alpha_miss: float,
    alpha_fr: float,
    tolerance_pp: float = 0.03,
    confidence: float = 0.95,
) -> Dict[str, Any]:
    """Aggregate R repeats of :func:`coverage_cell` (per category) into the
    two-tier V1 pass/fail table (design §1 C1's headline result, F2/T3).

    Parameters
    ----------
    cells_by_category:
        ``{category: [coverage_cell(...), ...]}``, one list of R repeat
        cells per category (design: R = 20).
    """
    if not cells_by_category:
        raise CertifyError("aggregate_v1_cells: cells_by_category must be non-empty")
    per_category: Dict[str, Any] = {}
    for cat, cells in sorted(cells_by_category.items()):
        if not cells:
            raise CertifyError(f"aggregate_v1_cells: category {cat!r} has zero repeat cells")
        per_category[cat] = {
            "tier1": v1_pass_tier1(cells, alpha_miss, alpha_fr, tolerance_pp),
            "tier2": v1_pass_tier2(cells, alpha_miss, alpha_fr, tolerance_pp, confidence),
            "n_repeats": len(cells),
            "mean_deferral_rate": float(np.nanmean([c["deferral_rate"] for c in cells])),
        }
    return {
        "alpha_miss": float(alpha_miss),
        "alpha_fr": float(alpha_fr),
        "tolerance_pp": float(tolerance_pp),
        "confidence": float(confidence),
        "per_category": per_category,
    }


def coverage_sanity_check_k1(
    per_cell_tier1: List[Dict[str, Any]], max_violations: int = 5
) -> Dict[str, Any]:
    """K1 (design §4): "empirical escaped-defect rate exceeds
    alpha_miss + 3pp in >= 5 of the 30 V1 cells" -- reports the count and
    whether the kill threshold is tripped; does not halt anything itself
    (a human/orchestration decision, per the design's own phrasing)."""
    n_violations = sum(1 for c in per_cell_tier1 if not c["pass_escaped"])
    return {
        "n_violations": n_violations,
        "n_cells": len(per_cell_tier1),
        "max_violations": max_violations,
        "k1_tripped": bool(n_violations >= max_violations),
    }


def vacuity_check_k2(
    deferral_rates_by_category: Dict[str, float],
    threshold: float = 0.80,
    min_categories: int = 8,
) -> Dict[str, Any]:
    """K2 (design §4): "median deferral rate > 80% ... in >= 8/15
    categories" -- vacuity guard. Reports the count; does not halt."""
    n_vacuous = sum(1 for v in deferral_rates_by_category.values() if v > threshold)
    return {
        "n_vacuous_categories": n_vacuous,
        "n_categories": len(deferral_rates_by_category),
        "threshold": threshold,
        "min_categories": min_categories,
        "k2_tripped": bool(n_vacuous >= min_categories),
    }
