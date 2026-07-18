"""The conformal gate: G1 (escaped-defect) + G2 (false-reject), Mondrian
per-category (+ optional per-defect-type) stratification, and the honest-
uncertainty refusal rules (design §2.2-2.3).

ZERO new math (design §2.2 mandate) -- both guarantees reduce EXACTLY to
``relmetrics.conformal.SplitConformal``, proved below.
------------------------------------------------------------------------
Score convention (see ``io.py``): HIGHER score = MORE anomalous.

G2 (false-reject), directly
    Design: "t_hi(c) = conformal upper quantile of GOOD calibration
    scores in stratum c at level alpha_fr; auto-reject region {s >= t_hi}
    ==> P(auto-reject | good, c) <= alpha_fr." This is EXACTLY
    ``SplitConformal(alpha=alpha_fr, randomize=False).fit(good_scores)``:
    that class's ``.threshold`` is defined as the
    ``ceil((n+1)(1-alpha))``-th smallest calibration score, giving
    ``P(new > threshold) <= alpha`` by construction (module docstring of
    ``relmetrics.conformal``). ``t_hi = SplitConformal(...).threshold``,
    no adaptation needed.

G1 (escaped-defect), via negation
    Design: "t_lo(c) = conformal lower quantile of DEFECTIVE calibration
    scores in stratum c at level alpha_miss (order statistic
    k = floor(alpha_miss * (n_def+1))); auto-pass region {s <= t_lo} ==>
    P(auto-pass | defective, c) <= alpha_miss." Let X be the defective
    calibration scores (size n), Y = -X. ``SplitConformal(alpha_miss,
    randomize=False).fit(Y).threshold`` is Y's ``rank_Y``-th smallest
    value, ``rank_Y = ceil((n+1)(1 - alpha_miss))``. Order-statistic
    identity: for any real array of size n, the k-th smallest value of X
    equals the negative of the ``(n-k+1)``-th smallest value of ``-X``.
    So it suffices to show ``n - k + 1 == rank_Y`` where
    ``k = floor(alpha_miss*(n+1))``:

        n - k + 1 = (n+1) - k = (n+1) - floor(alpha_miss*(n+1))
                  = ceil((n+1) - alpha_miss*(n+1))   [integer N minus
                                                       floor(x) = ceil(N-x)]
                  = ceil((n+1)*(1 - alpha_miss))
                  = rank_Y.

    Hence ``t_lo = X_(k) = -(Y_(n-k+1)) = -(Y_(rank_Y))
    = -SplitConformal(alpha_miss, randomize=False).fit(-defective_scores)
        .threshold``.
    This is an exact algebraic identity (not an approximation), so G1 is
    implemented as a single negated call into the same
    ``relmetrics.conformal.SplitConformal`` class used for G2 -- see
    :func:`_g1_threshold` / :func:`_g2_threshold` below, both one-liners.
    ``randomize=False`` is used throughout (the design's formulas are the
    plain/conservative order-statistic construction, not the randomized-
    tie-breaking exact-coverage variant relmetrics also offers).

Certifiability floor, for free
    ``SplitConformal.threshold`` returns ``+inf`` whenever
    ``rank > n`` -- i.e. exactly when ``alpha * (n+1) < 1``, i.e. exactly
    the design's floor condition ``alpha_min = 1/(n_cal+1) > alpha``
    (§2.3). For G2 this directly means ``t_hi = +inf`` (auto-reject
    region empty -- G2 refused for that stratum). For G1 (via negation)
    ``Y``'s threshold at ``+inf`` gives ``t_lo = -inf`` (auto-pass region
    empty -- G1 refused). No separate refusal branch is needed in the
    threshold arithmetic; :func:`calibrate_gate` only adds the loud
    banner/printed floor the design requires on top of this.

Mondrian stratification reuses ``relmetrics.conformal.MondrianConformal``
the same way, per-category (default) or per-(category, defect_type) when
requested and the defect-type cell has enough calibration defectives
(design §2.3: "defect-type Mondrian stratum with n_def < 10 -> defect-
type certificate refused, falls back to category-level").
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from relmetrics import conformal as _conformal
from relmetrics import provenance as _provenance
from scipy import stats as _stats

__all__ = [
    "GateError",
    "sha256_of_file",
    "certifiability_floor",
    "calibrate_gate",
    "route_gate",
    "DEFAULT_MIN_DEFECT_TYPE_N",
    "DEFAULT_KS_ALPHA",
]

DEFAULT_MIN_DEFECT_TYPE_N = 10  # design §2.3
DEFAULT_KS_ALPHA = 0.05  # design §2.3 exchangeability gate


class GateError(ValueError):
    """Raised on any gate.py precondition violation, with a precise,
    actionable message."""


def sha256_of_file(path: Union[str, Path]) -> str:
    """SHA256 of a file's bytes, for provenance-stamping inputs."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def certifiability_floor(n: int) -> float:
    """alpha_min = 1/(n+1) (design §2.3) -- the smallest alpha certifiable
    from n calibration points at this stratum, for the printed banner."""
    if n < 0:
        raise GateError(f"certifiability_floor: n must be >= 0, got {n}")
    return 1.0 / (n + 1)


def _g2_threshold(good_scores: np.ndarray, alpha_fr: float) -> Tuple[float, int]:
    """t_hi via direct SplitConformal on GOOD scores. Returns
    ``(threshold, n_good)``; threshold is ``+inf`` iff the stratum's floor
    exceeds ``alpha_fr`` (see module docstring)."""
    n = int(good_scores.size)
    if n == 0:
        return float("inf"), 0
    sc = _conformal.SplitConformal(alpha=alpha_fr, randomize=False, rng=0).fit(good_scores)
    return sc.threshold, n


def _g1_threshold(defective_scores: np.ndarray, alpha_miss: float) -> Tuple[float, int]:
    """t_lo via SplitConformal on NEGATED defective scores (see module
    docstring for the exact order-statistic equivalence proof). Returns
    ``(threshold, n_defect)``; threshold is ``-inf`` iff the stratum's
    floor exceeds ``alpha_miss``."""
    n = int(defective_scores.size)
    if n == 0:
        return float("-inf"), 0
    sc = _conformal.SplitConformal(alpha=alpha_miss, randomize=False, rng=0).fit(-defective_scores)
    neg_threshold = sc.threshold
    if np.isinf(neg_threshold):
        return float("-inf"), n
    return -neg_threshold, n


def _stratum_label(category: str, defect_type: Optional[str]) -> str:
    return category if defect_type is None else f"{category}::{defect_type}"


def _ks_exchangeability_gate(
    holdout_good: Dict[str, np.ndarray],
    cal_good: Dict[str, np.ndarray],
    alpha: float,
) -> Dict[str, Dict[str, Any]]:
    """Per-category KS test (held-out-train-good vs cal-good scores),
    BH-corrected across categories (design §2.3: "the per-category KS
    exchangeability gate ... alpha=0.05 with BH across 15 categories").
    Categories present in ``cal_good`` but absent from ``holdout_good``
    (no train-holdout pool offered) are reported ``passed=False`` with a
    ``reason``, never silently skipped.
    """
    from relmetrics import multiplicity as _multiplicity

    categories = sorted(cal_good.keys())
    stats_: List[float] = []
    pvals: List[float] = []
    reasons: List[Optional[str]] = []
    for cat in categories:
        hold = holdout_good.get(cat)
        cal = cal_good[cat]
        if hold is None or hold.size < 2 or cal.size < 2:
            stats_.append(float("nan"))
            pvals.append(0.0)  # forces "not passed" without a spurious BH pass
            reasons.append(
                "no train-holdout pool for this category" if hold is None
                else "fewer than 2 points in holdout or cal pool"
            )
            continue
        res = _stats.ks_2samp(hold, cal)
        stats_.append(float(res.statistic))
        pvals.append(float(res.pvalue))
        reasons.append(None)

    bh = _multiplicity.benjamini_hochberg(pvals, alpha=alpha)
    out: Dict[str, Dict[str, Any]] = {}
    for i, cat in enumerate(categories):
        out[cat] = {
            "ks_statistic": stats_[i],
            "p_value": pvals[i],
            "p_bh": float(bh["adjusted_p"][i]),
            # BH "reject H0(exchangeable)" == FAILS the gate; reasons[i]
            # already forces failure for degenerate pools regardless of BH.
            "passed": bool(not bh["reject"][i]) if reasons[i] is None else False,
            "reason": reasons[i],
        }
    return out


def calibrate_gate(
    cal_records: List[Dict[str, Any]],
    alpha_miss: float,
    alpha_fr: float,
    mondrian: str = "category",
    good_cal_holdout: Optional[List[Dict[str, Any]]] = None,
    good_cal_holdout_cal: Optional[List[Dict[str, Any]]] = None,
    min_defect_type_n: int = DEFAULT_MIN_DEFECT_TYPE_N,
    ks_alpha: float = DEFAULT_KS_ALPHA,
    backbone: Optional[str] = None,
    seed: int = 0,
    input_paths: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Calibrate the three-way gate on a calibration-half scores table.

    Parameters
    ----------
    cal_records:
        Canonical score records (``io.validate_scores`` shape) forming the
        CALIBRATION half of one repeat's stratified split (design §3.2);
        every record's ``split`` should be ``"test"`` (not enforced here
        -- ``splits.py`` already guarantees this for its own output, and
        the gate itself only reads ``category``/``score``/``label``/
        ``defect_type``, so it tolerates being handed a pre-filtered
        subset from any source).
    alpha_miss, alpha_fr:
        Target escaped-defect / false-reject bounds (design §1 C1
        defaults: 0.10 / 0.05, not hardcoded here -- caller-supplied).
    mondrian:
        ``"category"`` (default, G1 and G2 both per-category) or
        ``"category,defect_type"`` (G1 additionally per-defect-type where
        the defect-type cell has >= ``min_defect_type_n`` calibration
        defectives; below that, G1 falls back to the category-level
        threshold for that defect type, per design §2.3 -- G2 is always
        per-category only, since "good" has no defect_type axis).
    good_cal_holdout:
        Optional held-out train-good records (``splits.
        train_good_holdout_split``'s second return value) for the
        ``--good-cal train-holdout`` calibration-efficiency arm (design
        §3.2). When given, G2's threshold is computed from THIS pool
        instead of the test-side calibration good scores, but ONLY for
        categories that pass the per-category KS exchangeability gate
        against ``good_cal_holdout_cal`` (design §2.3); categories that
        fail (or lack a holdout pool) fall back to the test-side
        calibration good scores AND are marked ``g2_certified=False,
        g2_mode="audited-not-certified"`` in the stratum record -- G1 is
        never affected by this arm (§2.3: "G1 unaffected").
    good_cal_holdout_cal:
        The corresponding CALIBRATION-half good scores to KS-test the
        holdout pool against (required, and only used, when
        ``good_cal_holdout`` is given) -- normally just the good subset
        of ``cal_records`` itself; passed explicitly so callers can KS-
        gate against a different reference pool if a future arm needs to.
    min_defect_type_n, ks_alpha:
        See module-level defaults; both are named, overridable constants,
        never inlined magic numbers.
    backbone, seed, input_paths:
        Provenance metadata.

    Returns
    -------
    dict
        The full gate specification (JSON-serializable via
        ``io.to_jsonable``): ``alpha_miss``, ``alpha_fr``, ``mondrian``,
        ``good_cal_mode`` (``"test"`` or ``"train-holdout"``),
        ``categories_seen`` (sorted list -- the calibration support; any
        category absent from this list is OUT-OF-SUPPORT at route time,
        per the always-defer convention), ``strata`` (per-category dict:
        ``t_lo``, ``t_hi``, ``n_cal_defect``, ``n_cal_good``,
        ``alpha_min_g1``, ``alpha_min_g2``, ``g1_certified``,
        ``g2_certified``, ``g2_mode``, and -- if ``mondrian`` includes
        defect_type -- ``defect_type_thresholds``: per-defect-type
        ``t_lo``/``n_cal_defect``/``certified``/``fallback_reason``),
        ``ks_gate`` (per-category KS results, empty dict unless
        ``good_cal_holdout`` given), and a provenance stamp.
    """
    if not 0.0 < alpha_miss < 1.0:
        raise GateError(f"alpha_miss must be in (0, 1), got {alpha_miss}")
    if not 0.0 < alpha_fr < 1.0:
        raise GateError(f"alpha_fr must be in (0, 1), got {alpha_fr}")
    if mondrian not in ("category", "category,defect_type"):
        raise GateError(
            f"mondrian must be 'category' or 'category,defect_type', got {mondrian!r}"
        )
    if (good_cal_holdout is None) != (good_cal_holdout_cal is None):
        raise GateError(
            "calibrate_gate: good_cal_holdout and good_cal_holdout_cal must be "
            "given together (or both omitted)"
        )
    if not cal_records:
        raise GateError("calibrate_gate: cal_records must be non-empty")

    use_defect_type = mondrian == "category,defect_type"
    good_cal_mode = "train-holdout" if good_cal_holdout is not None else "test"

    by_cat_defect: Dict[str, List[float]] = {}
    by_cat_good: Dict[str, List[float]] = {}
    by_cat_defect_type: Dict[str, Dict[str, List[float]]] = {}
    for r in cal_records:
        cat = r["category"]
        if r["label"] == "defect":
            by_cat_defect.setdefault(cat, []).append(r["score"])
            by_cat_defect_type.setdefault(cat, {}).setdefault(
                r["defect_type"], []
            ).append(r["score"])
        else:
            by_cat_good.setdefault(cat, []).append(r["score"])

    categories = sorted(set(by_cat_defect) | set(by_cat_good))

    ks_gate: Dict[str, Dict[str, Any]] = {}
    holdout_by_cat: Dict[str, np.ndarray] = {}
    cal_good_arr_by_cat: Dict[str, np.ndarray] = {
        c: np.asarray(by_cat_good.get(c, []), dtype=float) for c in categories
    }
    if good_cal_holdout is not None:
        for r in good_cal_holdout:
            holdout_by_cat.setdefault(r["category"], []).append(r["score"])  # type: ignore[union-attr]
        holdout_by_cat = {k: np.asarray(v, dtype=float) for k, v in holdout_by_cat.items()}
        ref_good_by_cat: Dict[str, List[float]] = {}
        for r in good_cal_holdout_cal:  # type: ignore[union-attr]
            if r["label"] == "good":
                ref_good_by_cat.setdefault(r["category"], []).append(r["score"])
        ref_good_arr = {k: np.asarray(v, dtype=float) for k, v in ref_good_by_cat.items()}
        ks_gate = _ks_exchangeability_gate(holdout_by_cat, ref_good_arr, alpha=ks_alpha)

    strata: Dict[str, Any] = {}
    for cat in categories:
        defect_scores = np.asarray(by_cat_defect.get(cat, []), dtype=float)
        t_lo, n_def = _g1_threshold(defect_scores, alpha_miss)
        g1_certified = np.isfinite(t_lo)
        alpha_min_g1 = certifiability_floor(n_def)

        g2_mode = "test"
        g2_source_good = cal_good_arr_by_cat.get(cat, np.asarray([], dtype=float))
        if good_cal_holdout is not None:
            passed = ks_gate.get(cat, {}).get("passed", False)
            if passed and cat in holdout_by_cat:
                g2_source_good = holdout_by_cat[cat]
                g2_mode = "train-holdout"
            else:
                g2_mode = "audited-not-certified"

        t_hi, n_good = _g2_threshold(g2_source_good, alpha_fr)
        g2_certified = np.isfinite(t_hi) and g2_mode != "audited-not-certified"
        alpha_min_g2 = certifiability_floor(n_good)

        stratum: Dict[str, Any] = {
            "t_lo": t_lo,
            "t_hi": t_hi,
            "n_cal_defect": n_def,
            "n_cal_good": n_good,
            "alpha_min_g1": alpha_min_g1,
            "alpha_min_g2": alpha_min_g2,
            "g1_certified": bool(g1_certified),
            "g2_certified": bool(g2_certified),
            "g2_mode": g2_mode,
        }

        if use_defect_type:
            dt_thresholds: Dict[str, Any] = {}
            for dt, scores_list in sorted(by_cat_defect_type.get(cat, {}).items()):
                dt_scores = np.asarray(scores_list, dtype=float)
                if dt_scores.size < min_defect_type_n:
                    dt_thresholds[dt] = {
                        "t_lo": t_lo,
                        "n_cal_defect": int(dt_scores.size),
                        "certified": False,
                        "fallback_reason": (
                            f"n_cal_defect={dt_scores.size} < min_defect_type_n="
                            f"{min_defect_type_n}; falls back to category-level "
                            "t_lo (design §2.3)"
                        ),
                    }
                    continue
                dt_t_lo, dt_n = _g1_threshold(dt_scores, alpha_miss)
                dt_thresholds[dt] = {
                    "t_lo": dt_t_lo,
                    "n_cal_defect": dt_n,
                    "certified": bool(np.isfinite(dt_t_lo)),
                    "fallback_reason": None,
                }
            stratum["defect_type_thresholds"] = dt_thresholds

        strata[cat] = stratum

    input_hashes = (
        {str(p): sha256_of_file(p) for p in input_paths} if input_paths else {}
    )

    result: Dict[str, Any] = {
        "alpha_miss": float(alpha_miss),
        "alpha_fr": float(alpha_fr),
        "mondrian": mondrian,
        "good_cal_mode": good_cal_mode,
        "backbone": backbone,
        "categories_seen": categories,
        "strata": strata,
        "ks_gate": ks_gate,
        "ks_alpha": float(ks_alpha),
        "min_defect_type_n": int(min_defect_type_n),
        "n_cal": len(cal_records),
        "no_defective_calibration": len(by_cat_defect) == 0,
        "input_sha256": input_hashes,
    }
    return _provenance.stamp_result(result, script_path=__file__, seeds=[seed])


def route_gate(
    gate: Dict[str, Any], records: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Route new (label-optional) images through a calibrated gate.

    Every image gets exactly one of ``auto-pass``, ``auto-reject``,
    ``defer``. Out-of-support categories (absent from
    ``gate["categories_seen"]``) get ``defer`` with a loud
    ``out_of_support=True`` flag (design §2.3: "category absent from
    calibration -> U = +inf convention: always-defer, loud banner").
    Crossed thresholds (``t_lo >= t_hi``) route the ``[t_hi, t_lo]``
    overlap to ``defer`` automatically -- this falls out of the plain
    comparison logic below (``score <= t_lo`` and ``score >= t_hi`` can
    both be true only when ``t_lo >= t_hi``, and auto-pass is checked
    first only when the regions don't overlap; see the explicit crossed-
    threshold branch).

    Returns
    -------
    dict
        ``decisions`` (list of per-image dicts: ``image_id``, ``action``,
        ``category``, ``score``, ``t_lo``, ``t_hi``, ``out_of_support``,
        ``g2_certified``), ``n``, ``n_auto_pass``, ``n_auto_reject``,
        ``n_defer``, ``n_out_of_support``, and a provenance stamp.
    """
    strata = gate["strata"]
    categories_seen = set(gate["categories_seen"])

    decisions = []
    for r in records:
        cat = r["category"]
        score = r["score"]
        out_of_support = cat not in categories_seen
        if out_of_support:
            decisions.append(
                {
                    "image_id": r["image_id"],
                    "category": cat,
                    "score": score,
                    "action": "defer",
                    "t_lo": None,
                    "t_hi": None,
                    "out_of_support": True,
                    "g2_certified": False,
                    "reason": "category not seen at calibration (out-of-support, always-defer)",
                }
            )
            continue

        s = strata[cat]
        t_lo, t_hi = s["t_lo"], s["t_hi"]
        if t_lo >= t_hi:
            # Crossed thresholds: the overlap band always defers, both
            # guarantees survive (design §2.2).
            if score < t_hi:
                action = "auto-pass"
            elif score > t_lo:
                action = "auto-reject"
            else:
                action = "defer"
        else:
            if score <= t_lo:
                action = "auto-pass"
            elif score >= t_hi:
                action = "auto-reject"
            else:
                action = "defer"

        decisions.append(
            {
                "image_id": r["image_id"],
                "category": cat,
                "score": score,
                "action": action,
                "t_lo": t_lo,
                "t_hi": t_hi,
                "out_of_support": False,
                "g2_certified": s["g2_certified"],
                "reason": None,
            }
        )

    result: Dict[str, Any] = {
        "n": len(decisions),
        "n_auto_pass": sum(1 for d in decisions if d["action"] == "auto-pass"),
        "n_auto_reject": sum(1 for d in decisions if d["action"] == "auto-reject"),
        "n_defer": sum(1 for d in decisions if d["action"] == "defer"),
        "n_out_of_support": sum(1 for d in decisions if d["out_of_support"]),
        "decisions": decisions,
    }
    return _provenance.stamp_result(result, script_path=__file__, seeds=None)
