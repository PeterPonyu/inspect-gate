#!/usr/bin/env python3
"""VisA score-schema adapter: box outputs -> canonical scores-JSONL.

Two source schemas from the 2026-07-12 visa_brancha box run:
  * Dinomaly (dinomaly_visa_uni, Branch-A patch): per-category JSON dict
    ``{"/root/autodl-tmp/VisA_pytorch_dino/1cls/<cat>/test/<good|bad>/<stem>.png":
    score}`` -- needs full adaptation (path parse + label join).
  * PatchCore (anomalib on ROOT_A layout): per-category canonical JSONL
    already in the ``inspect_gate.io`` schema -- validated + merged only.

Ground truth for labels/counts is the OFFICIAL spot-diff split
(``visa_staging/1cls.csv``), the same file visa_prep.py built both box
layouts from: label ``normal`` -> good, ``anomaly`` -> bad. The adapter
REFUSES loudly (nonzero exit) on any count mismatch, unknown stem,
duplicate image_id, or category disagreement -- same discipline as
visa_prep.py.

End-to-end validation: recomputes per-category image-AUROC from the
adapted Dinomaly records (inspect_gate.reproduction.image_auroc) and
compares against the box's own final log.txt table -- proving label join
AND sign convention in one check. Everything is written to
ADAPTER-REPORT.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import NoReturn

import numpy as np

IG_ROOT = Path("/home/zeyufu/Desktop/ml-reliability-research/reliability-commons/tools/inspect-gate")
sys.path.insert(0, str(IG_ROOT.parent.parent))  # reliability-commons on path
sys.path.insert(0, str(IG_ROOT))

from inspect_gate import io as _io  # noqa: E402
from inspect_gate import reproduction as _repro  # noqa: E402

PULL = Path("/home/zeyufu/Desktop/ml-reliability-research/orchestration_2026-07-12"
            "/visa_pull/root/autodl-tmp/visa_brancha")
CSV_PATH = IG_ROOT / "visa_staging" / "1cls.csv"
OUT = IG_ROOT / "visa_results_2026-07-12"
CANON = OUT / "canonical"
SEEDS = [0, 1, 2, 3, 4]
CATEGORIES = ["candle", "capsules", "cashew", "chewinggum", "fryum", "macaroni1",
              "macaroni2", "pcb1", "pcb2", "pcb3", "pcb4", "pipe_fryum"]
AUROC_XCHECK_TOL = 1e-3  # box log rounds to 4 dp; rank-tie handling may differ slightly

DINO_PATH_RE = re.compile(r"/1cls/(?P<cat>[^/]+)/test/(?P<sub>good|bad)/(?P<stem>[^/]+)\.png$")


def refuse(msg: str) -> NoReturn:
    print(f"REFUSE: {msg}", file=sys.stderr)
    sys.exit(1)


def load_official_test_split() -> dict:
    """{category: {(sub, stem), ...}} for split==test, sub in {good, bad}."""
    split: dict = {}
    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            if row["split"] != "test":
                continue
            cat = row["object"]
            sub = "good" if row["label"] == "normal" else "bad"
            stem = Path(row["image"]).stem
            key = (sub, stem)
            cell = split.setdefault(cat, set())
            if key in cell:
                refuse(f"1cls.csv duplicate test entry {cat}/{sub}/{stem}")
            cell.add(key)
    if sorted(split) != CATEGORIES:
        refuse(f"1cls.csv categories {sorted(split)} != expected {CATEGORIES}")
    return split


def parse_final_log_table(log_path: Path) -> dict:
    """Last-reported per-category I-AUROC from the box's own log.txt."""
    table: dict = {}
    pat = re.compile(r"^(?P<cat>[a-z0-9_]+): I-Auroc:(?P<auroc>[0-9.]+),")
    with open(log_path) as f:
        for line in f:
            m = pat.match(line.strip())
            if m and m.group("cat") in CATEGORIES:
                table[m.group("cat")] = float(m.group("auroc"))  # later lines overwrite
    return table


def adapt_dinomaly(official: dict) -> dict:
    report: dict = {}
    for seed in SEEDS:
        run_dir = PULL / "dinomaly" / f"seed_{seed}" / "run"
        records = []
        for cat in CATEGORIES:
            scores = json.loads((run_dir / f"scores_{cat}.json").read_text())
            seen = set()
            for raw_path, score in scores.items():
                m = DINO_PATH_RE.search(raw_path)
                if not m:
                    refuse(f"dinomaly seed{seed} {cat}: unparseable path {raw_path!r}")
                if m.group("cat") != cat:
                    refuse(f"dinomaly seed{seed}: path category {m.group('cat')} inside scores_{cat}.json")
                sub, stem = m.group("sub"), m.group("stem")
                if (sub, stem) in seen:
                    refuse(f"dinomaly seed{seed} {cat}: duplicate {sub}/{stem}")
                seen.add((sub, stem))
                records.append({
                    "image_id": f"{cat}_test_{sub}_{stem}",
                    "category": cat,
                    "split": "test",
                    "score": float(score),
                    "label": "good" if sub == "good" else "defect",
                    "defect_type": sub if sub == "bad" else "good",
                })
            if seen != official[cat]:
                missing = official[cat] - seen
                extra = seen - official[cat]
                refuse(f"dinomaly seed{seed} {cat}: split mismatch vs 1cls.csv "
                       f"(missing={sorted(missing)[:5]} extra={sorted(extra)[:5]})")
        out_path = CANON / f"scores_dinomaly_seed{seed}.jsonl"
        _io.write_jsonl(out_path, records)
        _io.load_scores(str(out_path))  # full schema validation round-trip

        # end-to-end AUROC cross-check vs the box's own final log table
        log_table = parse_final_log_table(PULL / "dinomaly" / f"seed_{seed}" / "run" / "log.txt")
        xcheck = {}
        for cat in CATEGORIES:
            recs = [r for r in records if r["category"] == cat]
            auroc = _repro.image_auroc(
                np.array([r["score"] for r in recs], dtype=float),
                np.array([r["label"] == "defect" for r in recs], dtype=bool),
            )
            logged = log_table.get(cat)
            if logged is None:
                refuse(f"dinomaly seed{seed} {cat}: no I-Auroc line in box log.txt")
            diff = abs(auroc - logged)
            xcheck[cat] = {"recomputed": round(auroc, 6), "box_log": logged,
                           "abs_diff": round(diff, 6)}
            if diff > AUROC_XCHECK_TOL:
                refuse(f"dinomaly seed{seed} {cat}: recomputed AUROC {auroc:.5f} vs "
                       f"box log {logged:.5f} (diff {diff:.5f} > {AUROC_XCHECK_TOL})")
        report[seed] = {"n_records": len(records), "auroc_xcheck": xcheck,
                        "max_abs_diff": max(v["abs_diff"] for v in xcheck.values())}
        print(f"dinomaly seed{seed}: {len(records)} records, "
              f"AUROC xcheck max|diff|={report[seed]['max_abs_diff']:.6f} -> {out_path.name}")
    return report


def adapt_patchcore(official: dict) -> dict:
    report: dict = {}
    for seed in SEEDS:
        seed_dir = PULL / "patchcore" / f"seed_{seed}"
        records = []
        for cat in CATEGORIES:
            recs = _io.load_scores(str(seed_dir / f"scores_{cat}.jsonl"))
            for r in recs:
                if r["category"] != cat:
                    refuse(f"patchcore seed{seed}: category {r['category']} inside scores_{cat}.jsonl")
                if r["split"] != "test":
                    refuse(f"patchcore seed{seed} {cat}: unexpected split {r['split']}")
                if r["defect_type"] not in ("good", "bad"):
                    refuse(f"patchcore seed{seed} {cat}: unexpected defect_type {r['defect_type']}")
            n_good = sum(1 for r in recs if r["label"] == "good")
            n_bad = sum(1 for r in recs if r["label"] == "defect")
            want_good = sum(1 for sub, _ in official[cat] if sub == "good")
            want_bad = sum(1 for sub, _ in official[cat] if sub == "bad")
            if (n_good, n_bad) != (want_good, want_bad):
                refuse(f"patchcore seed{seed} {cat}: counts good={n_good} bad={n_bad} "
                       f"vs 1cls.csv good={want_good} bad={want_bad}")
            records.extend(recs)
        ids = [r["image_id"] for r in records]
        if len(ids) != len(set(ids)):
            refuse(f"patchcore seed{seed}: duplicate image_ids in merged table")
        out_path = CANON / f"scores_patchcore_seed{seed}.jsonl"
        _io.write_jsonl(out_path, records)
        _io.load_scores(str(out_path))
        per_cat_auroc = {}
        for cat in CATEGORIES:
            recs = [r for r in records if r["category"] == cat]
            per_cat_auroc[cat] = round(_repro.image_auroc(
                np.array([r["score"] for r in recs], dtype=float),
                np.array([r["label"] == "defect" for r in recs], dtype=bool)), 6)
        report[seed] = {"n_records": len(records),
                        "per_category_auroc_descriptive": per_cat_auroc}
        print(f"patchcore seed{seed}: {len(records)} records (counts vs 1cls.csv OK) -> {out_path.name}")
    return report


def main() -> None:
    CANON.mkdir(parents=True, exist_ok=True)
    official = load_official_test_split()
    n_test = {cat: len(v) for cat, v in official.items()}
    print(f"official 1cls.csv test split: {sum(n_test.values())} images, {len(n_test)} categories")
    dino = adapt_dinomaly(official)
    pc = adapt_patchcore(official)
    report = {
        "csv": str(CSV_PATH),
        "official_test_counts": n_test,
        "auroc_xcheck_tolerance": AUROC_XCHECK_TOL,
        "dinomaly": dino,
        "patchcore": pc,
    }
    (OUT / "ADAPTER-REPORT.json").write_text(json.dumps(_io.to_jsonable(report), indent=2))
    print(f"wrote {OUT / 'ADAPTER-REPORT.json'}")
    print("ADAPTER_OK")


if __name__ == "__main__":
    main()
