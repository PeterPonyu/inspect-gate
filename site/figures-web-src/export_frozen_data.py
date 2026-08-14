#!/usr/bin/env python3
"""Export committed figure-src tables into site/_data JSON.

Reads only committed table sources on this branch.
Does not read uncommitted PDFs or digests.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "manuscripts" / "figures-src"
OUT = ROOT / "site" / "_data"


def write_json(name: str, payload: object) -> None:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(rel: str) -> list[dict[str, str]]:
    path = SRC / rel
    with path.open(newline="", encoding="utf-8") as handle:
        lines = [line for line in handle if line.strip() and not line.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def fnum(value: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"", "NA", "n/a"}:
        return None
    return float(text)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    floors_rows = [
        {"category": "bottle", "n_cal_def": 32, "alpha_min_g1": 0.0303, "g1": "OK", "n_cal_good": 10, "g2": "REFUSE"},
        {"category": "cable", "n_cal_def": 46, "alpha_min_g1": 0.0213, "g1": "OK", "n_cal_good": 29, "g2": "OK"},
        {"category": "capsule", "n_cal_def": 54, "alpha_min_g1": 0.0182, "g1": "OK", "n_cal_good": 12, "g2": "REFUSE"},
        {"category": "carpet", "n_cal_def": 44, "alpha_min_g1": 0.0222, "g1": "OK", "n_cal_good": 14, "g2": "REFUSE"},
        {"category": "grid", "n_cal_def": 28, "alpha_min_g1": 0.0345, "g1": "OK", "n_cal_good": 10, "g2": "REFUSE"},
        {"category": "hazelnut", "n_cal_def": 35, "alpha_min_g1": 0.0278, "g1": "OK", "n_cal_good": 20, "g2": "OK"},
        {"category": "leather", "n_cal_def": 46, "alpha_min_g1": 0.0213, "g1": "OK", "n_cal_good": 16, "g2": "REFUSE"},
        {"category": "metal_nut", "n_cal_def": 46, "alpha_min_g1": 0.0213, "g1": "OK", "n_cal_good": 11, "g2": "REFUSE"},
        {"category": "pill", "n_cal_def": 70, "alpha_min_g1": 0.0141, "g1": "OK", "n_cal_good": 13, "g2": "REFUSE"},
        {"category": "screw", "n_cal_def": 60, "alpha_min_g1": 0.0164, "g1": "OK", "n_cal_good": 20, "g2": "OK"},
        {"category": "tile", "n_cal_def": 42, "alpha_min_g1": 0.0233, "g1": "OK", "n_cal_good": 16, "g2": "REFUSE"},
        {"category": "toothbrush", "n_cal_def": 15, "alpha_min_g1": 0.0625, "g1": "OK", "n_cal_good": 6, "g2": "REFUSE"},
        {"category": "transistor", "n_cal_def": 20, "alpha_min_g1": 0.0476, "g1": "OK", "n_cal_good": 30, "g2": "OK"},
        {"category": "wood", "n_cal_def": 30, "alpha_min_g1": 0.0323, "g1": "OK", "n_cal_good": 10, "g2": "REFUSE"},
        {"category": "zipper", "n_cal_def": 60, "alpha_min_g1": 0.0164, "g1": "OK", "n_cal_good": 16, "g2": "REFUSE"},
    ]
    write_json(
        "floors.json",
        {
            "caption": "Per-category certifiability at alpha_miss=0.10, alpha_fr=0.05 (backbone-invariant; MVTec test split). G1 15/15, G2 4/15 (cable, hazelnut, screw, transistor).",
            "g1_ok": "15/15",
            "g2_ok": "4/15",
            "g2_ok_categories": ["cable", "hazelnut", "screw", "transistor"],
            "rows": floors_rows,
        },
    )

    crc_rows = []
    for row in read_csv("data/crcbaseline.csv"):
        crc_rows.append(
            {
                "benchmark": row["benchmark"],
                "method": row["method"],
                "escaped_pct": round(fnum(row["escaped_pct"]) or 0, 2),
                "false_reject_pct": round(fnum(row["false_reject_pct"]) or 0, 2),
                "deferral_pct": round(fnum(row["deferral_pct"]) or 0, 2),
            }
        )
    write_json(
        "crc.json",
        {
            "caption": "Dual gate vs single-threshold CRC at the same escaped-defect risk (alpha_miss=0.10), pooled over both backbones and five seeds.",
            "published": [
                {"benchmark": "MPDD", "method": "gate", "g1": "50/60", "g2": "0/60", "escaped": "6.6%", "fr": "0.0%", "deferral": "73.1%"},
                {"benchmark": "MPDD", "method": "crc", "g1": "50/60", "g2": "n/a", "escaped": "6.6%", "fr": "36.9%", "deferral": "0.0%"},
                {"benchmark": "VisA", "method": "gate", "g1": "120/120", "g2": "120/120", "escaped": "7.6%", "fr": "3.0%", "deferral": "16.4%"},
                {"benchmark": "VisA", "method": "crc", "g1": "120/120", "g2": "n/a", "escaped": "9.5%", "fr": "16.2%", "deferral": "0.0%"},
                {"benchmark": "MVTec AD", "method": "gate", "g1": "150/150", "g2": "40/150", "escaped": "7.3%", "fr": "0.5%", "deferral": "54.4%"},
                {"benchmark": "MVTec AD", "method": "crc", "g1": "150/150", "g2": "n/a", "escaped": "8.5%", "fr": "3.1%", "deferral": "0.0%"},
            ],
            "raw": crc_rows,
        },
    )

    write_json(
        "deferral.json",
        {
            "caption": "Seed-0 median per-category deferral. Coverage is not a certificate: MVTec median ~70% because G2 refusal empties auto-reject; VisA drops because G2 is live.",
            "rows": [
                {"benchmark": "MVTec AD", "backbone": "PatchCore", "median": "70.0%", "mean": "55.1%", "max": "pill 78.0%", "min": "transistor 2.0%", "tag": "confirmatory"},
                {"benchmark": "MVTec AD", "backbone": "Dinomaly", "median": "69.5%", "mean": "54.2%", "max": "capsule 77.3%", "min": "screw 3.1%", "tag": "confirmatory"},
                {"benchmark": "VisA", "backbone": "PatchCore", "median": "18.7%", "mean": "—", "max": "macaroni2 72.5%", "min": "chewinggum 2.0%", "tag": "exploratory"},
                {"benchmark": "VisA", "backbone": "Dinomaly", "median": "4.2%", "mean": "—", "max": "capsules 21.9%", "min": "candle 2.5%", "tag": "exploratory"},
                {"benchmark": "MPDD", "backbone": "PatchCore", "median": "74.1%", "mean": "—", "max": "connector 100%", "min": "bracket brown 61.8%", "tag": "exploratory"},
                {"benchmark": "MPDD", "backbone": "Dinomaly", "median": "70.9%", "mean": "—", "max": "connector 100%", "min": "bracket white 53.3%", "tag": "exploratory"},
            ],
        },
    )

    floors_by_cat = {row["category"]: row for row in floors_rows}
    benches = [
        ("mvtec", "MVTec AD", "confirmatory", "data/categorymap_mvtec.csv"),
        ("visa", "VisA", "exploratory", "data/categorymap_visa.csv"),
        ("mpdd", "MPDD", "exploratory", "data/categorymap_mpdd.csv"),
    ]
    categorymap = {"benchmarks": []}
    for key, label, tag, rel in benches:
        cats = []
        for row in read_csv(rel):
            item = {
                "id": row["category"],
                "label": row["label"],
                "g1_cert": row["g1_cert"] == "1",
                "g1_rate_pct": fnum(row["g1_rate_pct"]),
                "g2_cert": row["g2_cert"] == "1",
                "g2_rate_pct": fnum(row["g2_rate_pct"]),
            }
            extra = floors_by_cat.get(row["category"])
            if extra:
                item["n_cal_def"] = extra["n_cal_def"]
                item["alpha_min_g1"] = extra["alpha_min_g1"]
                item["n_cal_good"] = extra["n_cal_good"]
                item["g2_floor"] = extra["g2"]
            cats.append(item)
        categorymap["benchmarks"].append({"id": key, "label": label, "tag": tag, "categories": cats})
    write_json("categorymap.json", categorymap)

    write_json(
        "drift.json",
        {
            "caption": "Corruption-drift stress test (post-freeze exploratory). Good-score KS screen; exceedances among accepted axis-certifiable cells.",
            "tag": "post-freeze exploratory",
            "residual": "Good-score KS misses 34% of accepted PatchCore cells above the escaped-defect target; defect-score marginal catches ~5% of those residual cells.",
            "rows": [
                {"corruption": "Brightness", "severity": 1, "ks_refused": "4/66", "escaped": "13/60", "fr": "1/30"},
                {"corruption": "Brightness", "severity": 2, "ks_refused": "5/66", "escaped": "12/59", "fr": "1/27"},
                {"corruption": "Brightness", "severity": 3, "ks_refused": "28/66", "escaped": "9/36", "fr": "1/14"},
                {"corruption": "Contrast", "severity": 1, "ks_refused": "2/66", "escaped": "11/62", "fr": "0/30"},
                {"corruption": "Contrast", "severity": 2, "ks_refused": "8/66", "escaped": "16/56", "fr": "0/25"},
                {"corruption": "Contrast", "severity": 3, "ks_refused": "28/66", "escaped": "13/36", "fr": "2/19"},
                {"corruption": "Gaussian", "severity": 1, "ks_refused": "23/66", "escaped": "10/41", "fr": "0/18"},
                {"corruption": "Gaussian", "severity": 2, "ks_refused": "41/66", "escaped": "8/24", "fr": "0/14"},
                {"corruption": "Gaussian", "severity": 3, "ks_refused": "47/66", "escaped": "11/19", "fr": "1/11"},
                {"corruption": "Defocus", "severity": 1, "ks_refused": "7/66", "escaped": "10/57", "fr": "0/26"},
                {"corruption": "Defocus", "severity": 2, "ks_refused": "18/66", "escaped": "8/46", "fr": "0/20"},
                {"corruption": "Defocus", "severity": 3, "ks_refused": "44/66", "escaped": "13/21", "fr": "2/10"},
            ],
        },
    )

    write_json(
        "latency.json",
        {
            "caption": "Per-image latency. Gate rows measured on this work's hardware. PatchCore backbone row is the authors' published figure, not measured here.",
            "hedge": "this work's hardware",
            "rows": [
                {"component": "Dinomaly (DINOv2-b) backbone — measured, GPU", "cost": "18.9 ms (p95 23.1)", "notes": "53 img/s at batch 1; 17.0 ms/img batched (B=32)"},
                {"component": "PatchCore backbone — authors' figure", "cost": "≲ 200 ms", "notes": "Roth et al. 2022, their hardware; not measured here"},
                {"component": "Routing (per image) — measured, CPU", "cost": "2.8 µs", "notes": "O(1) compare; <0.02% of the Dinomaly forward pass"},
                {"component": "Calibration (one-time) — measured, CPU", "cost": "2.4 ms (p95 2.8)", "notes": "full 3-way gate, 861-image cal half, 15 strata; per refresh"},
            ],
        },
    )

    write_json(
        "crcbackbone.json",
        {
            "caption": "Per-backbone breakdown of the pooled CRC table. CRC has no deferral and no G2 certificate.",
            "rows": [
                {"benchmark": "MPDD", "backbone": "PatchCore", "method": "gate", "escaped": "7.1%", "fr": "0.0%", "deferral": "75.1%"},
                {"benchmark": "MPDD", "backbone": "PatchCore", "method": "crc", "escaped": "7.1%", "fr": "41.9%", "deferral": "0.0%"},
                {"benchmark": "MPDD", "backbone": "Dinomaly", "method": "gate", "escaped": "6.1%", "fr": "0.0%", "deferral": "71.1%"},
                {"benchmark": "MPDD", "backbone": "Dinomaly", "method": "crc", "escaped": "6.1%", "fr": "31.8%", "deferral": "0.0%"},
                {"benchmark": "VisA", "backbone": "PatchCore", "method": "gate", "escaped": "8.8%", "fr": "3.7%", "deferral": "26.3%"},
                {"benchmark": "VisA", "backbone": "PatchCore", "method": "crc", "escaped": "9.7%", "fr": "28.8%", "deferral": "0.0%"},
                {"benchmark": "VisA", "backbone": "Dinomaly", "method": "gate", "escaped": "6.5%", "fr": "2.2%", "deferral": "6.5%"},
                {"benchmark": "VisA", "backbone": "Dinomaly", "method": "crc", "escaped": "9.3%", "fr": "3.7%", "deferral": "0.0%"},
                {"benchmark": "MVTec AD", "backbone": "PatchCore", "method": "gate", "escaped": "7.7%", "fr": "0.7%", "deferral": "54.8%"},
                {"benchmark": "MVTec AD", "backbone": "PatchCore", "method": "crc", "escaped": "8.4%", "fr": "5.2%", "deferral": "0.0%"},
                {"benchmark": "MVTec AD", "backbone": "Dinomaly", "method": "gate", "escaped": "6.9%", "fr": "0.3%", "deferral": "53.9%"},
                {"benchmark": "MVTec AD", "backbone": "Dinomaly", "method": "crc", "escaped": "8.7%", "fr": "0.9%", "deferral": "0.0%"},
            ],
        },
    )

    write_json(
        "glossary.json",
        {
            "items": [
                {"code": "G1", "meaning": "Certified escaped-defect bound."},
                {"code": "G2", "meaning": "Certified false-reject bound."},
                {"code": "CRC", "meaning": "Conformal Risk Control, the single-threshold conformal baseline."},
                {"code": "t_lo, t_hi", "meaning": "Per-category auto-pass / auto-reject thresholds."},
                {"code": "α_miss, α_fr", "meaning": "Target escaped-defect / false-reject rates (frozen 0.10 / 0.05)."},
                {"code": "α_min", "meaning": "Certifiability floor 1/(n_cal+1)."},
                {"code": "n_cal^def, n_cal^good", "meaning": "Per-category defective / good calibration pool sizes."},
                {"code": "refusal", "meaning": "Audited-not-certified: the corresponding auto-action is emptied (threshold ±∞)."},
                {"code": "Mondrian", "meaning": "Per-category (primary) conformal stratification; per-defect-type is exploratory."},
                {"code": "C2", "meaning": "Confirmatory excess-AURC audit (pooled Holm family)."},
            ]
        },
    )

    mondrian_path = SRC / "out" / "mondrian_cells.tsv"
    mondrian_cells = []
    with mondrian_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        for row in reader:
            mondrian_cells.append(
                {
                    "category": row["category"].strip(),
                    "defect_type": row["defect_type"].strip(),
                    "pc_miss": fnum(row["pc_miss"]),
                    "pc_defer": fnum(row["pc_defer"]),
                    "di_miss": fnum(row["di_miss"]),
                    "di_defer": fnum(row["di_defer"]),
                    "pc_n_def": int(float(row["pc_n_def"])),
                    "pc_n": int(float(row["pc_n"])),
                    "di_n_def": int(float(row["di_n_def"])),
                    "di_n": int(float(row["di_n"])),
                }
            )
    write_json("mondrian.json", {"tag": "exploratory appendix", "cells": mondrian_cells})

    g2_mvtec = read_csv("R/g2delta_mvtec.csv")
    g2_mpdd = read_csv("R/g2delta_mpdd.csv")
    write_json(
        "g2delta.json",
        {
            "caption": "G2 train-holdout remedy (PatchCore-only). Not the primary protocol. KS-refused cells stay refused.",
            "tag": "post-hoc · PatchCore-only",
            "summary": "MVTec 4/15 → 13/15 (leather KS-refused); MPDD 0/6 → 4/6.",
            "mvtec": g2_mvtec,
            "mpdd": g2_mpdd,
        },
    )

    samples = [
        {"row": "MPDD · good", "route": "AUTO-PASS", "file": "inspect-sample-mpdd-good-pass.png", "score": 0.02, "gt": False, "note": None},
        {"row": "MPDD · good", "route": "DEFER", "file": "inspect-sample-mpdd-good-defer.png", "score": 0.00, "gt": False, "note": None},
        {"row": "MPDD · good", "route": "AUTO-REJECT", "file": "inspect-sample-mpdd-good-reject.png", "score": 0.57, "gt": False, "note": None},
        {"row": "MPDD · defect", "route": "AUTO-PASS", "file": "inspect-sample-mpdd-def-pass.png", "zoom": "inspect-sample-mpdd-def-pass-gt.png", "score": 0.32, "gt": True, "note": None},
        {"row": "MPDD · defect", "route": "DEFER", "file": "inspect-sample-mpdd-def-defer.png", "zoom": "inspect-sample-mpdd-def-defer-gt.png", "score": 0.52, "gt": True, "note": "floor refusal"},
        {"row": "MPDD · defect", "route": "AUTO-REJECT", "file": "inspect-sample-mpdd-def-reject.png", "zoom": "inspect-sample-mpdd-def-reject-gt.png", "score": 0.57, "gt": True, "note": None},
        {"row": "VisA · good", "route": "AUTO-PASS", "file": "inspect-sample-visa-good-pass.png", "score": 0.29, "gt": False, "note": None},
        {"row": "VisA · good", "route": "DEFER", "file": "inspect-sample-visa-good-defer.png", "score": 0.44, "gt": False, "note": None},
        {"row": "VisA · good", "route": "AUTO-REJECT", "file": "inspect-sample-visa-good-reject.png", "score": 0.68, "gt": False, "note": None},
        {"row": "VisA · defect", "route": "AUTO-PASS", "file": "inspect-sample-visa-def-pass.png", "zoom": "inspect-sample-visa-def-pass-gt.png", "score": 0.42, "gt": True, "note": None},
        {"row": "VisA · defect", "route": "DEFER", "file": "inspect-sample-visa-def-defer.png", "zoom": "inspect-sample-visa-def-defer-gt.png", "score": 0.49, "gt": True, "note": None},
        {"row": "VisA · defect", "route": "AUTO-REJECT", "file": "inspect-sample-visa-def-reject.png", "zoom": "inspect-sample-visa-def-reject-gt.png", "score": 0.57, "gt": True, "note": None},
    ]
    write_json(
        "samples.json",
        {
            "caption": "Three-way decisions on real parts (PatchCore, seed 0). Insets and contours are dataset ground truth, not model localization. Connector defer is floor refusal: escaped-defect cannot certify, so every image defers.",
            "protocol": "MPDD uses the train-holdout rescue arm; VisA uses the primary protocol. Exploratory MPDD / VisA tiles.",
            "tiles": samples,
        },
    )

    print("wrote", sorted(p.name for p in OUT.glob("*.json")))


if __name__ == "__main__":
    main()
