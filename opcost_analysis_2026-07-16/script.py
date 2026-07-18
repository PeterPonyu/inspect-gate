#!/usr/bin/env python3
"""
opcost_analysis_2026-07-16 / script.py

Deployable operating-point / human-review-cost analysis for the inspect-gate paper
(round-2 red-team panel, highest-leverage remaining lever; see
manuscripts/FINAL-SCORE-R2-2026-07-16.md, "Single highest-leverage remaining improvement").

Translates the frozen dual-gate vs. CRC-single-threshold rates (escaped-defect,
false-reject, deferral) from baseline_comparison_2026-07-15/results.json into
practitioner economics: parts/hour throughput -> human-review workload, and
$/hour cost of escaped defects + false rejects + review labor, under our dual
gate's certified operating point vs. the CRC baseline's operating point.

INPUTS:
  - FROZEN (not recomputed): per-benchmark pooled escaped/false-reject/deferral
    rates for "our_gate_published" and "crc_baseline", read verbatim from
    ../baseline_comparison_2026-07-15/results.json. These are the same numbers
    already in paper Table \ref{tab:crcbaseline} (Table 3 in the AEI version).
  - ASSUMED (scenario parameters): throughput (parts/hour), unit cost of an
    escaped defect, unit cost of a false reject, reviewer wage, and reviewer
    review-throughput. These are illustrative deployment scenarios, NOT derived
    from any benchmark's real factory economics (none of the three benchmarks
    ships real production/cost data) -- clearly labeled ASSUMED below and in
    the output JSON.

No frozen number (gate_calibration/*.json, baseline_comparison results) is
recomputed or altered by this script. This is a pure downstream cost-model
transform, run once, CPU-only.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN_PATH = os.path.join(HERE, "..", "baseline_comparison_2026-07-15", "results.json")

with open(FROZEN_PATH) as f:
    frozen = json.load(f)

# ---------------------------------------------------------------------------
# FROZEN rates, read verbatim (pooled over backbones x seeds x categories).
# Source: baseline_comparison_2026-07-15/results.json -> benchmarks.<B>.{our_gate_published,crc_baseline}
# ---------------------------------------------------------------------------
BENCHMARKS = ["MPDD", "VisA", "MVTec-AD"]

rates = {}
for b in BENCHMARKS:
    bm = frozen["benchmarks"][b]
    gate = bm["our_gate_published"]
    crc = bm["crc_baseline"]
    rates[b] = {
        "gate": {
            "escaped": gate["mean_escaped_defect_rate"],
            "false_reject": gate["mean_false_reject_rate"],
            "defer": gate["mean_deferral_rate"],
        },
        "crc": {
            "escaped": crc["mean_escaped_defect_rate"],
            "false_reject": crc["mean_false_reject_rate"],
            "defer": crc["mean_deferral_rate"],  # == 0.0 by construction (no defer mechanism)
        },
        "n_cells": gate["n_cells"],
    }

# ---------------------------------------------------------------------------
# ASSUMED scenario parameters (NOT frozen; illustrative deployment contexts).
# Each scenario is applied to all three benchmarks' certified rates -- the
# scenario models the LINE, the benchmark supplies the RATES.
# ---------------------------------------------------------------------------
SCENARIOS = {
    "low_volume_precision": {
        "label": "Low-volume precision line",
        "description": (
            "ASSUMED. Small-batch precision/safety-relevant parts (e.g. aerospace "
            "or medical-device brackets). Escaped defects carry recall/liability "
            "exposure; false rejects scrap an expensive machined part."
        ),
        "throughput_parts_per_hour": 100,
        "cost_per_escaped_defect_usd": 5000,
        "cost_per_false_reject_usd": 150,
        "reviewer_wage_usd_per_hour": 45,
        "reviewer_throughput_parts_per_hour": 120,  # ~30 s/part careful manual inspection
    },
    "mid_volume_general": {
        "label": "Mid-volume general industrial line",
        "description": (
            "ASSUMED. Generic manufactured components (the register most MVTec-AD- "
            "and VisA-style objects sit in): moderate part value, moderate volume."
        ),
        "throughput_parts_per_hour": 600,
        "cost_per_escaped_defect_usd": 300,
        "cost_per_false_reject_usd": 15,
        "reviewer_wage_usd_per_hour": 30,
        "reviewer_throughput_parts_per_hour": 240,  # ~15 s/part
    },
    "high_volume_commodity": {
        "label": "High-volume commodity line",
        "description": (
            "ASSUMED. Cheap, high-throughput parts (e.g. painted metal fasteners/ "
            "brackets, the MPDD real-world register). Escaped defects and false "
            "rejects are both individually cheap; economics are dominated by "
            "review-labor throughput at high volume."
        ),
        "throughput_parts_per_hour": 3000,
        "cost_per_escaped_defect_usd": 25,
        "cost_per_false_reject_usd": 2,
        "reviewer_wage_usd_per_hour": 26,
        "reviewer_throughput_parts_per_hour": 450,  # ~8 s/part quick visual check
    },
}


def cost_model(rate, scenario):
    """Given a method's (escaped, false_reject, defer) rates and a scenario,
    compute parts/hour and $/hour breakdown. defer=0 for CRC (no defer mechanism)."""
    X = scenario["throughput_parts_per_hour"]
    c_escape = scenario["cost_per_escaped_defect_usd"]
    c_reject = scenario["cost_per_false_reject_usd"]
    wage = scenario["reviewer_wage_usd_per_hour"]
    rev_thru = scenario["reviewer_throughput_parts_per_hour"]
    cost_per_reviewed_part = wage / rev_thru  # $/part

    escaped_parts_per_hour = X * rate["escaped"]
    reject_parts_per_hour = X * rate["false_reject"]
    reviewer_parts_per_hour = X * rate["defer"]
    reviewer_fte = reviewer_parts_per_hour / rev_thru

    escaped_cost_per_hour = escaped_parts_per_hour * c_escape
    reject_cost_per_hour = reject_parts_per_hour * c_reject
    review_labor_cost_per_hour = reviewer_parts_per_hour * cost_per_reviewed_part
    total_cost_per_hour = escaped_cost_per_hour + reject_cost_per_hour + review_labor_cost_per_hour

    return {
        "reviewer_workload_parts_per_hour": reviewer_parts_per_hour,
        "reviewer_fte_required": reviewer_fte,
        "escaped_defects_per_hour": escaped_parts_per_hour,
        "false_rejects_per_hour": reject_parts_per_hour,
        "escaped_cost_usd_per_hour": escaped_cost_per_hour,
        "false_reject_cost_usd_per_hour": reject_cost_per_hour,
        "review_labor_cost_usd_per_hour": review_labor_cost_per_hour,
        "total_cost_usd_per_hour": total_cost_per_hour,
    }


def breakeven_false_reject_cost(gate_rate, crc_rate, scenario):
    """Solve for cost_per_false_reject_usd (holding all else fixed) at which
    Total_gate == Total_crc. Independent of throughput X (cancels algebraically).
    Above this breakeven value, the dual gate is the cheaper deployment;
    below it, the CRC single-threshold baseline is cheaper.

    0 = c_escape*(e_gate - e_crc) + c_reject*(f_gate - f_crc) + defer_gate*cost_per_reviewed_part
    => c_reject* = -[c_escape*(e_gate - e_crc) + defer_gate*cost_per_reviewed_part] / (f_gate - f_crc)
    """
    c_escape = scenario["cost_per_escaped_defect_usd"]
    wage = scenario["reviewer_wage_usd_per_hour"]
    rev_thru = scenario["reviewer_throughput_parts_per_hour"]
    cost_per_reviewed_part = wage / rev_thru

    e_gate, f_gate, d_gate = gate_rate["escaped"], gate_rate["false_reject"], gate_rate["defer"]
    e_crc, f_crc = crc_rate["escaped"], crc_rate["false_reject"]

    denom = f_gate - f_crc  # always negative in our data (gate FR << CRC FR)
    if abs(denom) < 1e-15:
        return None
    numer = c_escape * (e_gate - e_crc) + d_gate * cost_per_reviewed_part
    return -numer / denom


def breakeven_review_cost_per_part(gate_rate, crc_rate, scenario):
    """Solve for cost_per_reviewed_part (holding c_escape, c_reject fixed at the
    scenario's assumed values) at which Total_gate == Total_crc. Independent of
    throughput X and of the wage/reviewer-throughput split (only their ratio
    matters). This answers the practitioner question directly: how much could
    human review cost per part, at this scenario's escaped/false-reject unit
    costs, before the gate's deferral overhead erases its false-reject savings?

    0 = c_escape*(e_gate - e_crc) + c_reject*(f_gate - f_crc) + defer_gate*cost_per_reviewed_part*
    => cost_per_reviewed_part* = -[c_escape*(e_gate - e_crc) + c_reject*(f_gate - f_crc)] / defer_gate
    """
    c_escape = scenario["cost_per_escaped_defect_usd"]
    c_reject = scenario["cost_per_false_reject_usd"]
    e_gate, f_gate, d_gate = gate_rate["escaped"], gate_rate["false_reject"], gate_rate["defer"]
    e_crc, f_crc = crc_rate["escaped"], crc_rate["false_reject"]

    if d_gate < 1e-15:
        return None
    numer = c_escape * (e_gate - e_crc) + c_reject * (f_gate - f_crc)
    return -numer / d_gate


results = {
    "label": (
        "Deployable operating-point / human-review-cost analysis. "
        "Downstream cost-model transform of FROZEN gate_calibration + "
        "baseline_comparison_2026-07-15 rates. No frozen number recomputed or altered. "
        "Scenario parameters (throughput, unit costs, wage, reviewer throughput) are "
        "ASSUMED illustrative deployment contexts, explicitly labeled, not derived from "
        "benchmark data."
    ),
    "provenance": {
        "frozen_rates_source": "baseline_comparison_2026-07-15/results.json (mean_escaped_defect_rate, mean_false_reject_rate, mean_deferral_rate; pooled over 2 backbones x 5 seeds x all categories per benchmark)",
        "frozen_rates_upstream": "gate_calibration/v1_<backbone>_seed<seed>.json (frozen 2026-07-12/13; not touched by this script)",
        "assumed_parameters": "scenario throughput/costs/wage/reviewer-throughput below; illustrative, not benchmark-derived",
    },
    "frozen_rates_used": rates,
    "scenarios": SCENARIOS,
    "benchmark_scenario_grid": {},
    "breakeven_false_reject_cost_usd": {},
}

for b in BENCHMARKS:
    results["benchmark_scenario_grid"][b] = {}
    results["breakeven_false_reject_cost_usd"][b] = {}
    for sname, scenario in SCENARIOS.items():
        gate_out = cost_model(rates[b]["gate"], scenario)
        crc_out = cost_model(rates[b]["crc"], scenario)
        savings_per_hour = crc_out["total_cost_usd_per_hour"] - gate_out["total_cost_usd_per_hour"]
        results["benchmark_scenario_grid"][b][sname] = {
            "gate": gate_out,
            "crc": crc_out,
            "gate_savings_usd_per_hour_vs_crc": savings_per_hour,
            "gate_cheaper": savings_per_hour > 0,
        }
        be = breakeven_false_reject_cost(rates[b]["gate"], rates[b]["crc"], scenario)
        results["breakeven_false_reject_cost_usd"][b][sname] = {
            "breakeven_cost_per_false_reject_usd": be,
            "scenario_assumed_cost_per_false_reject_usd": scenario["cost_per_false_reject_usd"],
            "gate_cheaper_at_assumed_cost": (
                scenario["cost_per_false_reject_usd"] > be if be is not None else None
            ),
        }
        be_review = breakeven_review_cost_per_part(rates[b]["gate"], rates[b]["crc"], scenario)
        actual_review_cost_per_part = scenario["reviewer_wage_usd_per_hour"] / scenario["reviewer_throughput_parts_per_hour"]
        results["breakeven_false_reject_cost_usd"][b][sname]["breakeven_review_cost_per_part_usd"] = be_review
        results["breakeven_false_reject_cost_usd"][b][sname]["scenario_actual_review_cost_per_part_usd"] = actual_review_cost_per_part
        results["breakeven_false_reject_cost_usd"][b][sname]["review_cost_headroom_multiple"] = (
            be_review / actual_review_cost_per_part if be_review is not None and actual_review_cost_per_part > 0 else None
        )

out_path = os.path.join(HERE, "results.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"Wrote {out_path}")

# ---------------------------------------------------------------------------
# Console summary (headline numbers)
# ---------------------------------------------------------------------------
for b in BENCHMARKS:
    print(f"\n=== {b} ===")
    print(f"  gate rates: escaped={rates[b]['gate']['escaped']:.4f} fr={rates[b]['gate']['false_reject']:.4f} defer={rates[b]['gate']['defer']:.4f}")
    print(f"  crc  rates: escaped={rates[b]['crc']['escaped']:.4f} fr={rates[b]['crc']['false_reject']:.4f} defer=0.0000")
    for sname, scenario in SCENARIOS.items():
        cell = results["benchmark_scenario_grid"][b][sname]
        be = results["breakeven_false_reject_cost_usd"][b][sname]
        print(f"  [{scenario['label']}] X={scenario['throughput_parts_per_hour']}/hr")
        print(f"    gate: reviewer_load={cell['gate']['reviewer_workload_parts_per_hour']:.1f}/hr (FTE={cell['gate']['reviewer_fte_required']:.3f}), total_cost=${cell['gate']['total_cost_usd_per_hour']:.2f}/hr")
        print(f"    crc:  reviewer_load=0/hr, total_cost=${cell['crc']['total_cost_usd_per_hour']:.2f}/hr")
        print(f"    gate savings vs crc: ${cell['gate_savings_usd_per_hour_vs_crc']:.2f}/hr (gate cheaper: {cell['gate_cheaper']})")
        print(f"    breakeven false-reject unit cost: ${be['breakeven_cost_per_false_reject_usd']:.2f} (scenario assumes ${be['scenario_assumed_cost_per_false_reject_usd']})")
        print(f"    breakeven review cost/part: ${be['breakeven_review_cost_per_part_usd']:.4f} (scenario actual ${be['scenario_actual_review_cost_per_part_usd']:.4f}, headroom {be['review_cost_headroom_multiple']:.1f}x)")
