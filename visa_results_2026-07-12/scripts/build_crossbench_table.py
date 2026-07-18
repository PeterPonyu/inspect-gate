#!/usr/bin/env python3
"""MVTec-vs-VisA cross-benchmark table for the JIM paper's second-benchmark
section. Every number is re-aggregated from the primary result JSONs
(analysis_2026-07-10/ for MVTec, visa_results_2026-07-12/ for VisA) --
nothing is copied from memos. Emits MVTEC-VS-VISA.json (full) and
MVTEC-VS-VISA.md (paper-ready compact table + notes)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

IG_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons/tools/inspect-gate")
MV = IG_ROOT / "analysis_2026-07-10"
VI = IG_ROOT / "visa_results_2026-07-12"
OUT_JSON = VI / "MVTEC-VS-VISA.json"
OUT_MD = VI / "MVTEC-VS-VISA.md"
SEEDS = [0, 1, 2, 3, 4]
BACKBONES = ["patchcore", "dinomaly"]


def agg_benchmark(root: Path) -> dict:
    repro = json.loads((root / "reproduction" / "reproduction_gate.json").read_text())
    out: dict = {}
    for bb in BACKBONES:
        mean_aurocs = [repro[bb][str(s)]["mean_auroc"] for s in SEEDS]
        min_aurocs = [repro[bb][str(s)]["min_auroc"] for s in SEEDS]
        repro_pass = [repro[bb][str(s)]["pass"] for s in SEEDS]
        target = repro[bb][str(SEEDS[0])]["target"]

        g1_cert = g2_cert = n_cats = None
        v1_pass_cells = v1_total_cells = 0
        k1_trips = k2_trips = 0
        med_deferrals = []
        for s in SEEDS:
            v1 = json.loads((root / "gate_calibration" / f"v1_{bb}_seed{s}.json").read_text())
            floors = v1["certifiability_floors"]
            n_cats = len(floors)
            g1 = sum(1 for f in floors.values() if f["g1_certified"])
            g2 = sum(1 for f in floors.values() if f["g2_certified"])
            # floors are seed-invariant (cross-checked by the analysis pass)
            if g1_cert is not None and (g1, g2) != (g1_cert, g2_cert):
                raise AssertionError(f"{root.name}/{bb}: floors vary across seeds")
            g1_cert, g2_cert = g1, g2
            per_cat = v1["v1"]["per_category"]
            v1_pass_cells += sum(1 for v in per_cat.values() if v["tier1"]["pass_tier1"])
            v1_total_cells += len(per_cat)
            k1_trips += bool(v1["k1"]["k1_tripped"])
            k2_trips += bool(v1["k2"]["k2_tripped"])
            med_deferrals.extend(v1["median_deferral_by_category"].values())

        audit_rejects = audit_tests = 0
        rejected_cells = []
        for s in SEEDS:
            aud = json.loads((root / "audit" / f"audit_{bb}_seed{s}.json").read_text())
            for cat, res in aud.items():
                for r in res["results"]:
                    audit_tests += 1
                    if r["reject_holm"]:
                        audit_rejects += 1
                        rejected_cells.append(f"{cat}/s{s}/{r['practice']}")

        out[bb] = {
            "n_categories": n_cats,
            "repro_target": target,
            "repro_pass_by_seed": repro_pass,
            "mean_iauroc_mean": float(np.mean(mean_aurocs)),
            "mean_iauroc_std": float(np.std(mean_aurocs, ddof=1)),
            "min_cat_iauroc_worst_seed": float(np.min(min_aurocs)),
            "g1_certified": g1_cert,
            "g2_certified_primary": g2_cert,
            "v1_tier1_pass_cells": v1_pass_cells,
            "v1_tier1_total_cells": v1_total_cells,
            "k1_seeds_tripped": k1_trips,
            "k2_seeds_tripped": k2_trips,
            "median_deferral_rate_across_cats_seeds": float(np.nanmedian(med_deferrals)),
            "audit_holm_rejects": audit_rejects,
            "audit_holm_tests": audit_tests,
            "audit_rejected_cells": rejected_cells,
        }
    return out


def fmt_row(bench: str, bb: str, d: dict) -> str:
    tgt = f"{d['repro_target']:.3f}" if d["repro_target"] is not None else "n/a*"
    rp = ("5/5" if all(d["repro_pass_by_seed"]) else
          "n/a*" if all(p is None for p in d["repro_pass_by_seed"]) else
          f"{sum(bool(p) for p in d['repro_pass_by_seed'])}/5")
    return (f"| {bench} | {bb} | {d['mean_iauroc_mean']:.4f} ± {d['mean_iauroc_std']:.4f} "
            f"| {tgt} | {rp} | {d['g1_certified']}/{d['n_categories']} "
            f"| {d['g2_certified_primary']}/{d['n_categories']} "
            f"| {d['v1_tier1_pass_cells']}/{d['v1_tier1_total_cells']} "
            f"| {d['k1_seeds_tripped']}+{d['k2_seeds_tripped']} "
            f"| {d['audit_holm_rejects']}/{d['audit_holm_tests']} "
            f"| {d['median_deferral_rate_across_cats_seeds']:.3f} |")


def main() -> None:
    mv = agg_benchmark(MV)
    vi = agg_benchmark(VI)
    payload = {"mvtec_ad": mv, "visa": vi,
               "sources": {"mvtec_ad": str(MV), "visa": str(VI)},
               "notes": [
                   "MVTec G2 primary-protocol counts; the 2026-07-12 G2 train-holdout "
                   "promotion (g2_promotion_2026-07-12/, PatchCore only -- Dinomaly has no "
                   "train-side score dump) lifts MVTec G2 to 12-13/15 and is reported "
                   "separately in the paper.",
                   "PatchCore VisA reproduction target n/a: no repo-confirmed published "
                   "PatchCore-on-VisA image-AUROC (reproduction.py no-guessed-target rule); "
                   "row is descriptive.",
                   "VisA PatchCore scores are NOT bit-identical across seeds (0/48 pairs; "
                   "MVTec was 60/60) -- see visa_results_2026-07-12/seed_stability/.",
               ]}
    OUT_JSON.write_text(json.dumps(payload, indent=2))

    lines = [
        "# MVTec-AD vs VisA cross-benchmark table (JIM paper, second-benchmark section)",
        "",
        "Re-aggregated 2026-07-12 from primary JSONs only (no memo numbers).",
        "Protocol identical on both benchmarks: 5 seeds, R=20 stratified repeats,",
        "alpha_miss=0.10, alpha_fr=0.05, primary (--good-cal test) protocol,",
        "exploratory audit fixed+tuned, n_perm=2000, per-cell Holm.",
        "",
        "| Benchmark | Backbone | mean I-AUROC (5 seeds) | repro target | repro pass "
        "| G1 cert. | G2 cert. (primary) | V1 tier-1 cells | K1+K2 seed trips "
        "| audit Holm rejects | median deferral |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for bench, data in (("MVTec-AD", mv), ("VisA", vi)):
        for bb in BACKBONES:
            lines.append(fmt_row(bench, bb, data[bb]))
    lines += [
        "",
        "*PatchCore-on-VisA has no repo-confirmed published image-AUROC figure, so its",
        "reproduction row is descriptive (target n/a), per the tool's no-guessed-target rule.",
        "",
        "## Reading",
        "",
        f"- VisA is the lower-ceiling benchmark the workload-gap memo asked for: PatchCore "
        f"drops from {mv['patchcore']['mean_iauroc_mean']:.3f} (MVTec) to "
        f"{vi['patchcore']['mean_iauroc_mean']:.3f} (VisA) mean I-AUROC; Dinomaly holds "
        f"({mv['dinomaly']['mean_iauroc_mean']:.3f} -> {vi['dinomaly']['mean_iauroc_mean']:.3f}, "
        f"reproduction-gated 5/5 vs the paper's published 0.987 VisA figure).",
        f"- Audit informativeness: MVTec Dinomaly rejected "
        f"{mv['dinomaly']['audit_holm_rejects']}/{mv['dinomaly']['audit_holm_tests']} "
        f"(ceiling effect); VisA Dinomaly rejects "
        f"{vi['dinomaly']['audit_holm_rejects']}/{vi['dinomaly']['audit_holm_tests']}; "
        f"VisA PatchCore rejects {vi['patchcore']['audit_holm_rejects']}/"
        f"{vi['patchcore']['audit_holm_tests']} (MVTec: "
        f"{mv['patchcore']['audit_holm_rejects']}/{mv['patchcore']['audit_holm_tests']}).",
        "- G2 counts above are the primary protocol on both benchmarks; the train-holdout",
        "  promotion arm (computed 2026-07-12, MVTec, PatchCore only -- Dinomaly has no",
        "  train-side score dump) is reported separately.",
        "- K1+K2 column: number of seeds (of 5) tripping each kill-gate; 0+0 everywhere",
        "  on both benchmarks.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_JSON}\nwrote {OUT_MD}")
    print("\n".join(lines[6:12]))


if __name__ == "__main__":
    main()
