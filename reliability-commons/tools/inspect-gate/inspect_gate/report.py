"""Compact JSON+Markdown report renderer.

Documented deviation from the design doc's literal §2.1 CLI listing
(``inspect-gate report ... -o report.html``): this MVP renders compact
Markdown (or raw JSON passthrough for ``.json`` output paths), not HTML
with embedded SVGs -- the same MVP simplification ``asr-gate``'s own
``cli.py`` documents ("no HTML needed for MVP"). Every number in the
report traces back to a provenance-stamped result JSON (``gate.json``/
``audit.json``/``certify.json``), which is the artifact figure scripts
should consume directly per design §5, not this report.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = ["render_markdown"]


def _fmt(x: Any, spec: str = ".4f") -> str:
    if x is None:
        return "n/a"
    try:
        if isinstance(x, float) and (x != x):  # NaN
            return "n/a"
        return format(x, spec)
    except (TypeError, ValueError):
        return str(x)


def render_markdown(
    gate_result: Optional[Dict[str, Any]] = None,
    audit_result: Optional[Dict[str, Any]] = None,
    certify_result: Optional[Dict[str, Any]] = None,
) -> str:
    lines = ["# inspect-gate report", ""]

    if gate_result is not None:
        lines += [
            "## Gate calibration",
            "",
            f"- backbone: `{gate_result.get('backbone')}`",
            f"- alpha_miss: {gate_result['alpha_miss']}, alpha_fr: {gate_result['alpha_fr']}",
            f"- mondrian: `{gate_result['mondrian']}`, good_cal_mode: `{gate_result['good_cal_mode']}`",
            f"- n_cal: {gate_result['n_cal']}, categories_seen: {len(gate_result['categories_seen'])}",
            f"- no_defective_calibration: **{gate_result['no_defective_calibration']}**",
            "",
            "| category | t_lo | t_hi | n_cal_defect | n_cal_good | g1_certified | g2_certified | g2_mode |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for cat, s in sorted(gate_result["strata"].items()):
            lines.append(
                f"| {cat} | {_fmt(s['t_lo'])} | {_fmt(s['t_hi'])} | {s['n_cal_defect']} | "
                f"{s['n_cal_good']} | {s['g1_certified']} | {s['g2_certified']} | {s['g2_mode']} |"
            )
        lines.append("")

    if certify_result is not None:
        lines += [
            "## V1 coverage certification",
            "",
            "| category | mean_escaped | pass_t1_escaped | mean_fr | pass_t1_fr | underpowered_escaped | pooled_escaped_ub |",
            "|---|---|---|---|---|---|---|",
        ]
        for cat, c in sorted(certify_result.get("per_category", {}).items()):
            t1 = c["tier1"]
            t2 = c["tier2"]
            lines.append(
                f"| {cat} | {_fmt(t1['mean_escaped_defect_rate'])} | {t1['pass_escaped']} | "
                f"{_fmt(t1['mean_false_reject_rate'])} | {t1['pass_false_reject']} | "
                f"{t2['underpowered_escaped']} | {_fmt(t2['escaped_ub_1sided'])} |"
            )
        lines.append("")

    if audit_result is not None:
        lines += [
            "## Audit (excess-AURC, Holm m={})".format(audit_result["holm_family_size"]),
            "",
            f"- backbone: `{audit_result.get('backbone')}`",
            f"- target_deferral_rate: {audit_result['target_deferral_rate']:.4f}",
            "",
            "| practice | n | excess_aurc | ci | p | p_holm | reject_holm |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in audit_result["results"]:
            ci = r["excess_aurc_ci"]
            lines.append(
                f"| {r['practice']} | {r['n']} | {_fmt(r['excess_aurc'])} | "
                f"[{_fmt(ci[0])}, {_fmt(ci[1])}] | {_fmt(r['p_value'])} | "
                f"{_fmt(r['p_holm'])} | {r['reject_holm']} |"
            )
        for r in audit_result.get("skipped", []):
            lines.append(f"| {r['practice']} (skipped) | - | - | - | - | - | - |  <!-- {r['skipped_reason']} -->")
        lines.append("")

    return "\n".join(lines)
