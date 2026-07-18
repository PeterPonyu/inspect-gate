"""Field-standard threshold practices B1-B3, and the matched-deferral
ambiguity band that gives each a fair (coverage-matched) comparison
against the certified gate (design §3.4).

B1: one global fixed score threshold (single operating point across all
    categories), tuned on the pooled calibration half.
B2: per-category tuned threshold, tuned on that category's calibration
    half.
B3: train-good score-quantile heuristic (threshold at a high quantile of
    held-out train-good scores; uses NO defective data at all).
B4 (the analytic random-deferral null) is NOT a baseline object here --
    it never needs a threshold or a fitted object, it is the closed-form
    ``relmetrics.aurc.random_aurc`` call made directly in ``audit.py``
    (design §3.4: "a reference line, never a scored run").

"Tuned" (B1/B2), concretely
----------------------------
The design table says B1/B2 are "tuned" without pinning the exact metric.
This module's concrete instantiation (documented deviation, mirrors
``asr-gate.scores``'s own "the design is underspecified at the level of
exact mechanics" precedent): best-F1 threshold search over the
calibration half's ROC-style operating points, F1 computed treating
"defect" as the positive class (score >= threshold -> predicted defect).
This is the natural reading of "diligent field practice" and is a single,
clearly-labeled scope choice -- see the module's ``fit_*`` docstrings.

Matched-deferral ambiguity band
---------------------------------
Design §3.4: "each [baseline] is given the same deferral budget as the
gate via a symmetric ambiguity band around its threshold (band width set
to match the gate's realized deferral rate)." :func:`band_width_for_target_deferral`
finds the band half-width ``w`` (score units) such that
``P(|score - threshold| <= w)`` on the given evaluation pool matches
``target_deferral_rate``, via bisection on the empirical CDF of
``|score - threshold|`` (monotone in ``w`` by construction, so bisection
is exact up to floating-point tolerance -- no iterative optimizer needed).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = [
    "BaselineError",
    "best_f1_threshold",
    "fit_b1_global_threshold",
    "fit_b2_per_category_threshold",
    "fit_b3_train_good_quantile",
    "band_width_for_target_deferral",
    "band_route",
]


class BaselineError(ValueError):
    """Raised on any baselines.py precondition violation."""


def best_f1_threshold(scores: np.ndarray, labels_is_defect: np.ndarray) -> Tuple[float, float]:
    """Threshold (score >= threshold -> predicted defect) maximizing F1
    against ``labels_is_defect``, searched over the midpoints between
    consecutive sorted unique scores (the only candidates that can change
    the F1 value; standard exact threshold-search construction).

    Returns
    -------
    (threshold, best_f1)
    """
    scores = np.asarray(scores, dtype=float)
    labels_is_defect = np.asarray(labels_is_defect, dtype=bool)
    if scores.shape != labels_is_defect.shape or scores.size == 0:
        raise BaselineError("scores and labels_is_defect must be equal-length, non-empty")
    uniq = np.unique(scores)
    if uniq.size == 1:
        candidates = np.array([uniq[0] - 1e-9, uniq[0] + 1e-9])
    else:
        candidates = np.concatenate([[uniq[0] - 1e-9], (uniq[:-1] + uniq[1:]) / 2.0, [uniq[-1] + 1e-9]])

    best_thr = float(candidates[0])
    best_f1 = -1.0
    n_pos = int(labels_is_defect.sum())
    for thr in candidates:
        pred = scores >= thr
        tp = int(np.sum(pred & labels_is_defect))
        fp = int(np.sum(pred & ~labels_is_defect))
        fn = n_pos - tp
        if tp == 0:
            f1 = 0.0
        else:
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        if f1 > best_f1:
            best_f1 = f1
            best_thr = float(thr)
    return best_thr, best_f1


def fit_b1_global_threshold(cal_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """B1: one global threshold, best-F1 on the POOLED calibration half
    (all categories combined -- the naive field practice, design §3.4)."""
    if not cal_records:
        raise BaselineError("fit_b1_global_threshold: cal_records must be non-empty")
    scores = np.array([r["score"] for r in cal_records], dtype=float)
    is_defect = np.array([r["label"] == "defect" for r in cal_records], dtype=bool)
    thr, f1 = best_f1_threshold(scores, is_defect)
    return {"practice": "fixed", "threshold": thr, "cal_f1": f1, "n_cal": len(cal_records)}


def fit_b2_per_category_threshold(cal_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """B2: per-category threshold, best-F1 on that category's calibration
    half (the diligent field practice, design §3.4). Categories with zero
    defectives in the calibration half get ``threshold=+inf`` (never
    auto-reject anything, since there is no calibration signal at all for
    that category) rather than a spurious fit."""
    if not cal_records:
        raise BaselineError("fit_b2_per_category_threshold: cal_records must be non-empty")
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for r in cal_records:
        by_cat.setdefault(r["category"], []).append(r)

    thresholds: Dict[str, Any] = {}
    for cat, recs in sorted(by_cat.items()):
        scores = np.array([r["score"] for r in recs], dtype=float)
        is_defect = np.array([r["label"] == "defect" for r in recs], dtype=bool)
        if not is_defect.any():
            thresholds[cat] = {"threshold": float("inf"), "cal_f1": 0.0, "n_cal": len(recs)}
            continue
        thr, f1 = best_f1_threshold(scores, is_defect)
        thresholds[cat] = {"threshold": thr, "cal_f1": f1, "n_cal": len(recs)}
    return {"practice": "tuned", "per_category": thresholds}


def fit_b3_train_good_quantile(
    train_good_records: List[Dict[str, Any]], quantile: float = 0.95
) -> Dict[str, Any]:
    """B3: per-category threshold at a high quantile of held-out train-
    good scores (design §3.4: "no defective data used"). Categories
    absent from ``train_good_records`` get ``threshold=+inf``."""
    if not 0.0 < quantile < 1.0:
        raise BaselineError(f"quantile must be in (0, 1), got {quantile}")
    if not train_good_records:
        raise BaselineError("fit_b3_train_good_quantile: train_good_records must be non-empty")
    bad = [r["image_id"] for r in train_good_records if r["label"] != "good"]
    if bad:
        raise BaselineError(
            f"fit_b3_train_good_quantile: {len(bad)} record(s) are not "
            f"label='good' (e.g. {bad[:3]}) -- B3 uses NO defective data by design"
        )
    by_cat: Dict[str, List[float]] = {}
    for r in train_good_records:
        by_cat.setdefault(r["category"], []).append(r["score"])

    thresholds: Dict[str, Any] = {}
    for cat, scores_list in sorted(by_cat.items()):
        scores = np.asarray(scores_list, dtype=float)
        thresholds[cat] = {"threshold": float(np.quantile(scores, quantile)), "n_train_good": int(scores.size)}
    return {"practice": "quantile", "quantile": float(quantile), "per_category": thresholds}


def _threshold_for(baseline: Dict[str, Any], category: str) -> float:
    if baseline["practice"] == "fixed":
        return baseline["threshold"]
    per_cat = baseline["per_category"]
    if category not in per_cat:
        return float("inf")  # out-of-support -> never auto-reject
    return per_cat[category]["threshold"]


def band_width_for_target_deferral(
    scores: np.ndarray,
    thresholds: np.ndarray,
    target_deferral_rate: float,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> float:
    """Bisect for the symmetric band half-width ``w`` such that
    ``mean(|scores - thresholds| <= w) ~= target_deferral_rate``.

    Parameters
    ----------
    scores, thresholds:
        Equal-length arrays; ``thresholds[i]`` is the per-item threshold
        (same value repeated for B1, per-category value for B2/B3).
    target_deferral_rate:
        The realized gate deferral rate to match (design §3.4).
    """
    scores = np.asarray(scores, dtype=float)
    thresholds = np.asarray(thresholds, dtype=float)
    if scores.shape != thresholds.shape or scores.size == 0:
        raise BaselineError("scores and thresholds must be equal-length, non-empty")
    if not 0.0 <= target_deferral_rate <= 1.0:
        raise BaselineError(f"target_deferral_rate must be in [0, 1], got {target_deferral_rate}")

    dist = np.abs(scores - thresholds)
    finite = np.isfinite(dist)
    if not finite.any() or target_deferral_rate == 0.0:
        return 0.0

    lo, hi = 0.0, float(np.max(dist[finite]))
    if hi == 0.0:
        return 0.0

    def frac_deferred(w: float) -> float:
        return float(np.mean(dist[finite] <= w))

    if frac_deferred(hi) < target_deferral_rate:
        return hi  # even the widest band undershoots -- best achievable

    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        if frac_deferred(mid) < target_deferral_rate:
            lo = mid
        else:
            hi = mid
        if hi - lo < tol:
            break
    return hi


def band_route(
    records: List[Dict[str, Any]],
    baseline: Dict[str, Any],
    band_width: float,
) -> List[Dict[str, Any]]:
    """Route ``records`` through a fitted B1/B2/B3 baseline with a
    symmetric ambiguity band of half-width ``band_width`` (design §3.4).
    Score >= threshold -> "auto-reject" outside the band, < threshold ->
    "auto-pass" outside the band, within ``[threshold-w, threshold+w]`` ->
    "defer".
    """
    out = []
    for r in records:
        thr = _threshold_for(baseline, r["category"])
        score = r["score"]
        if not np.isfinite(thr):
            action = "auto-pass"  # no calibration signal at all for this category
        elif abs(score - thr) <= band_width:
            action = "defer"
        elif score >= thr:
            action = "auto-reject"
        else:
            action = "auto-pass"
        out.append({"image_id": r["image_id"], "category": r["category"], "action": action, "threshold": thr})
    return out
