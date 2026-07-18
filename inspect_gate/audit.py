"""The excess-AURC audit: does field-standard threshold practice beat
honest random deferral? (design §2.2 audit/, §3.4-§3.5, the paper's ONLY
confirmatory Holm family).

Zero new math beyond bookkeeping: every statistic is a direct call into
``relmetrics.aurc``, ``relmetrics.nulls``, or ``relmetrics.multiplicity``
-- mirrors ``asr-gate.audit``'s "thin wrapper" design exactly.

Loss/confidence framing (documented deviation -- the design doc names the
statistics to reuse but not the exact per-item loss/confidence mapping
for this AD-triage setting; this is the resolved choice, flagged for
review per the task brief)
--------------------------------------------------------------------------
Each baseline B1/B2/B3 induces, per image, a threshold-based binary
prediction (score >= threshold -> predict "defect"). Define:

    loss_i   = 1{prediction_i != true_label_i}                (0/1 error)
    conf_i   = |score_i - threshold_i|                        (distance
               from the decision boundary; higher = more confident)

This is exactly the standard selective-classification framing
``relmetrics.aurc`` is built for (its own docstring: "losses: per-sample
loss in [0, inf); confidences: higher = more confident, accepted first").
The AURC of this (loss, confidence) pair over the FULL score range
measures how well "distance from threshold" orders correct vs incorrect
decisions; ``excess_aurc_gain`` compares it to the closed-form random-
deferral null (``relmetrics.aurc.random_aurc``, pooled 0/1 error rate --
never Monte-Carlo'd, per that module's own anti-bug-class rule).

The matched-abstention permutation p-value (design §3.5: "matched-
abstention permutation p-value computed within category") uses the
REALIZED band-deferral mask from ``baselines.band_route`` (matched to the
gate's deferral rate) as ``abstain_mask``, with ``strata=category`` so
the null re-draws abstentions matched PER CATEGORY -- not a median split
(unlike ``asr-gate.audit``'s own documented MVP simplification; this
audit already has a principled, gate-matched abstention set available,
so there is no need for that simplification here).

The category-blocked bootstrap CI on the pooled excess-AURC effect size
(design §3.5's "test machinery note") uses
``relmetrics.bootstrap.blocked_bootstrap`` with ``block_ids=category``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from relmetrics import aurc as _aurc
from relmetrics import bootstrap as _bootstrap
from relmetrics import multiplicity as _multiplicity
from relmetrics import nulls as _nulls
from relmetrics import provenance as _provenance

from inspect_gate import baselines as _baselines

__all__ = ["AuditError", "audit_practice", "run_audit"]


class AuditError(ValueError):
    """Raised on any audit precondition violation."""


def _practice_predictions_and_conf(
    records: List[Dict[str, Any]], baseline: Dict[str, Any]
) -> Sequence[np.ndarray]:
    losses = np.empty(len(records), dtype=float)
    conf = np.empty(len(records), dtype=float)
    for i, r in enumerate(records):
        thr = _baselines._threshold_for(baseline, r["category"])
        predicted_defect = np.isfinite(thr) and r["score"] >= thr
        true_defect = r["label"] == "defect"
        losses[i] = float(predicted_defect != true_defect)
        conf[i] = float("inf") if not np.isfinite(thr) else abs(r["score"] - thr)
    return losses, conf


def audit_practice(
    eval_records: List[Dict[str, Any]],
    baseline: Dict[str, Any],
    band_width: float,
    n_perm: int = 2000,
    seed: int = 0,
) -> Dict[str, Any]:
    """Excess-AURC + matched-abstention permutation p-value for ONE
    (practice, backbone) cell, evaluated on ``eval_records``.

    Parameters
    ----------
    eval_records:
        Canonical score records for one backbone's evaluation half (all
        categories pooled -- category enters only as the blocking/
        stratification unit, never dropped).
    baseline:
        A fitted B1/B2/B3 object (``baselines.fit_b*``).
    band_width:
        The gate-matched deferral band half-width (``baselines.
        band_width_for_target_deferral``), used for the abstention mask
        the permutation null matches per category.
    """
    if not eval_records:
        raise AuditError("audit_practice: eval_records must be non-empty")

    losses, conf = _practice_predictions_and_conf(eval_records, baseline)
    finite = np.isfinite(conf)
    n_excluded = int((~finite).sum())
    if finite.sum() == 0:
        raise AuditError("audit_practice: every record has an out-of-support (inf) threshold")
    losses_f = losses[finite]
    conf_f = conf[finite]
    categories = np.array([r["category"] for r in eval_records])[finite]

    aurc_method = _aurc.aurc(losses_f, conf_f)
    aurc_random = _aurc.random_aurc(losses_f)
    excess = _aurc.excess_aurc_gain(losses_f, conf_f)

    routed = _baselines.band_route(
        [r for r, keep in zip(eval_records, finite) if keep], baseline, band_width
    )
    abstain_mask = np.array([d["action"] == "defer" for d in routed], dtype=bool)

    perm = _nulls.matched_abstention_null(
        losses=losses_f, abstain_mask=abstain_mask, strata=categories,
        n_perm=n_perm, seed=seed,
    )

    boot = _bootstrap.blocked_bootstrap(
        lambda l, c: _aurc.excess_aurc_gain(l, c),
        [losses_f, conf_f], block_ids=categories, n_boot=1000, seeds=[seed],
    )

    return {
        "n": int(finite.sum()),
        "n_excluded": n_excluded,
        "aurc_method": aurc_method,
        "aurc_random": aurc_random,
        "excess_aurc": excess,
        "excess_aurc_ci": list(boot["ci"]),
        "abstention_fraction": float(abstain_mask.mean()),
        "p_value": perm["p_value_less"],
        "n_perm": perm["n_perm"],
    }


def run_audit(
    cal_records: List[Dict[str, Any]],
    eval_records: List[Dict[str, Any]],
    train_good_records: Optional[List[Dict[str, Any]]],
    target_deferral_rate: float,
    practices: Sequence[str] = ("fixed", "tuned", "quantile"),
    backbone: Optional[str] = None,
    b3_quantile: float = 0.95,
    n_perm: int = 2000,
    alpha: float = 0.05,
    seed: int = 0,
) -> Dict[str, Any]:
    """Fit B1/B2/B3 on ``cal_records`` (+ ``train_good_records`` for B3),
    audit each on ``eval_records`` against the analytic random null, and
    Holm-correct across the roster (design §3.5: the confirmatory family
    is ``{fixed, tuned, quantile} x backbones``, size ALWAYS computed as
    ``len(results)`` here -- never hardcoded to 6; running this with a
    different practice/backbone roster changes the family size
    automatically, per the design's own stated convention elsewhere).

    ``run_audit`` handles ONE backbone; the CLI/orchestration layer calls
    it once per backbone and combines the Holm family across both calls
    (mirrors ``asr-gate``'s ``next_boot_asr_expansion.sh`` roster-derived-
    Holm precedent -- the per-call ``holm_family_size``/``results`` here
    are per-backbone; global Holm combination is the caller's job when
    more than one backbone is being audited together).

    Returns
    -------
    dict
        ``results`` (one row per practice KEPT: ``practice``,
        ``backbone``, plus everything :func:`audit_practice` returns),
        ``skipped`` (practices dropped, e.g. B3 with no
        ``train_good_records``), ``holm_family_size``, and a provenance
        stamp.
    """
    if not cal_records:
        raise AuditError("run_audit: cal_records must be non-empty")
    if not eval_records:
        raise AuditError("run_audit: eval_records must be non-empty")
    unknown = set(practices) - {"fixed", "tuned", "quantile"}
    if unknown:
        raise AuditError(f"run_audit: unknown practice(s) {unknown}")

    results: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    if "fixed" in practices:
        b1 = _baselines.fit_b1_global_threshold(cal_records)
        thr_arr = np.array([b1["threshold"]] * len(eval_records), dtype=float)
        scores_arr = np.array([r["score"] for r in eval_records], dtype=float)
        w = _baselines.band_width_for_target_deferral(scores_arr, thr_arr, target_deferral_rate)
        cell = audit_practice(eval_records, b1, w, n_perm=n_perm, seed=seed)
        results.append({"practice": "fixed", "backbone": backbone, "band_width": w, **cell})

    if "tuned" in practices:
        b2 = _baselines.fit_b2_per_category_threshold(cal_records)
        thr_arr = np.array(
            [_baselines._threshold_for(b2, r["category"]) for r in eval_records], dtype=float
        )
        scores_arr = np.array([r["score"] for r in eval_records], dtype=float)
        w = _baselines.band_width_for_target_deferral(scores_arr, thr_arr, target_deferral_rate)
        cell = audit_practice(eval_records, b2, w, n_perm=n_perm, seed=seed)
        results.append({"practice": "tuned", "backbone": backbone, "band_width": w, **cell})

    if "quantile" in practices:
        if not train_good_records:
            skipped.append({
                "practice": "quantile", "backbone": backbone,
                "skipped_reason": "no train_good_records supplied -- B3 needs a held-out train-good pool",
            })
        else:
            b3 = _baselines.fit_b3_train_good_quantile(train_good_records, quantile=b3_quantile)
            thr_arr = np.array(
                [_baselines._threshold_for(b3, r["category"]) for r in eval_records], dtype=float
            )
            scores_arr = np.array([r["score"] for r in eval_records], dtype=float)
            w = _baselines.band_width_for_target_deferral(scores_arr, thr_arr, target_deferral_rate)
            cell = audit_practice(eval_records, b3, w, n_perm=n_perm, seed=seed)
            results.append({"practice": "quantile", "backbone": backbone, "band_width": w, **cell})

    if results:
        pvals = [r["p_value"] for r in results]
        holm = _multiplicity.holm_bonferroni(pvals, alpha=alpha)
        for r, p_holm, rej in zip(results, holm["adjusted_p"], holm["reject"]):
            r["p_holm"] = float(p_holm)
            r["reject_holm"] = bool(rej)

    out: Dict[str, Any] = {
        "alpha": float(alpha),
        "n_perm": int(n_perm),
        "backbone": backbone,
        "target_deferral_rate": float(target_deferral_rate),
        "holm_family_size": len(results),
        "results": results,
        "skipped": skipped,
    }
    return _provenance.stamp_result(out, script_path=__file__, seeds=[seed])
