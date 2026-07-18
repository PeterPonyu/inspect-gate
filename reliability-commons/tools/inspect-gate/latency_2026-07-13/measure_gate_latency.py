#!/usr/bin/env python3
"""TIER 1 latency: inspect-gate's own per-decision cost, CPU-only.

Measures, on THIS machine, the two operations that constitute the gate's
deployment overhead on top of any backbone:

  (a) calibrate_gate  -- one-time (per calibration refresh) cost of fitting
      the three-way conformal gate on a realistic calibration half.
  (b) route_gate      -- the per-image amortized decision cost on the
      evaluation half (total route-call time / number of images).

Data: canonical MVTec Dinomaly seed0 scores, partitioned into the
calibration/evaluation halves EXACTLY as the paper's protocol does, via
inspect_gate.splits.stratified_cal_eval_split(repeat_seed=0) (design 3.2,
"split-seed = repeat index"; repeat 0). alpha_miss/alpha_fr are the design
C1 defaults (0.10 / 0.05), mondrian per-category.

Honesty: every number here is MEASURED on the recorded hardware. Median of
>= N_RUNS timed runs after warmup; also p95 and raw runs are saved.
"""
from __future__ import annotations

import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from inspect_gate.io import load_scores
from inspect_gate.gate import calibrate_gate, route_gate
from inspect_gate.splits import stratified_cal_eval_split

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SCORES = REPO / "dinomaly_brancha_2026-07-10" / "canonical" / "scores_dinomaly_seed0.jsonl"

ALPHA_MISS = 0.10   # design C1 escaped-defect target
ALPHA_FR = 0.05     # design C1 false-reject target
MONDRIAN = "category"
REPEAT_SEED = 0

N_RUNS = 31         # timed runs (odd -> clean median); > 5 as required
N_WARMUP = 5


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def _mem_total_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                kb = int(line.split()[1])
                return round(kb / (1024 ** 2), 1)
    except Exception:
        pass
    return float("nan")


def _summary(times_s):
    arr = np.asarray(times_s, dtype=float)
    return {
        "n_runs": int(arr.size),
        "median_s": float(np.median(arr)),
        "mean_s": float(np.mean(arr)),
        "min_s": float(np.min(arr)),
        "max_s": float(np.max(arr)),
        "p95_s": float(np.percentile(arr, 95)),
        "std_s": float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0,
        "raw_runs_s": [float(x) for x in arr],
    }


def main() -> None:
    records = load_scores(SCORES)
    test_records = [r for r in records if r["split"] == "test"]
    cal, ev = stratified_cal_eval_split(test_records, repeat_seed=REPEAT_SEED, frac=0.5)
    n_cal, n_eval = len(cal), len(ev)

    # --- (a) calibrate_gate ---
    for _ in range(N_WARMUP):
        gate = calibrate_gate(cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                              mondrian=MONDRIAN, backbone="dinomaly", seed=0)
    cal_times = []
    for _ in range(N_RUNS):
        t0 = time.perf_counter()
        gate = calibrate_gate(cal, alpha_miss=ALPHA_MISS, alpha_fr=ALPHA_FR,
                              mondrian=MONDRIAN, backbone="dinomaly", seed=0)
        cal_times.append(time.perf_counter() - t0)

    # --- (b) route_gate over the whole eval half (N images per call) ---
    for _ in range(N_WARMUP):
        _ = route_gate(gate, ev)
    route_call_times = []
    for _ in range(N_RUNS):
        t0 = time.perf_counter()
        res = route_gate(gate, ev)
        route_call_times.append(time.perf_counter() - t0)
    assert res["n"] == n_eval

    cal_sum = _summary(cal_times)
    route_sum = _summary(route_call_times)
    per_image_amortized_ms = 1000.0 * route_sum["median_s"] / n_eval

    out = {
        "measured": True,
        "date": "2026-07-13",
        "machine": {
            "cpu_model": _cpu_model(),
            "logical_cores": __import__("os").cpu_count(),
            "ram_total_gb": _mem_total_gb(),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "data": {
            "scores_file": str(SCORES.relative_to(REPO)),
            "backbone": "dinomaly",
            "dataset": "MVTec-AD",
            "seed": 0,
            "repeat_seed": REPEAT_SEED,
            "n_test_records": len(test_records),
            "n_calibration_half": n_cal,
            "n_evaluation_half": n_eval,
            "n_categories": len(gate["categories_seen"]),
        },
        "config": {
            "alpha_miss": ALPHA_MISS,
            "alpha_fr": ALPHA_FR,
            "mondrian": MONDRIAN,
            "n_warmup": N_WARMUP,
            "n_timed_runs": N_RUNS,
        },
        "calibrate_gate": {
            "description": "one-time fit of the 3-way conformal gate on the calibration half",
            **cal_sum,
            "median_ms": 1000.0 * cal_sum["median_s"],
            "p95_ms": 1000.0 * cal_sum["p95_s"],
        },
        "route_gate": {
            "description": "route the full evaluation half (N images) through the calibrated gate, per call",
            **route_sum,
            "median_ms_per_call": 1000.0 * route_sum["median_s"],
            "per_image_amortized_ms": per_image_amortized_ms,
            "per_image_amortized_us": 1000.0 * per_image_amortized_ms,
        },
    }

    out_path = HERE / "gate_latency.json"
    out_path.write_text(json.dumps(out, indent=2))

    print(f"machine: {out['machine']['cpu_model']} | {out['machine']['logical_cores']} cores | "
          f"{out['machine']['ram_total_gb']} GB")
    print(f"split (repeat {REPEAT_SEED}): n_cal={n_cal}  n_eval={n_eval}  "
          f"categories={len(gate['categories_seen'])}")
    print(f"calibrate_gate: median={1000*cal_sum['median_s']:.3f} ms  "
          f"p95={1000*cal_sum['p95_s']:.3f} ms  (n={N_RUNS})")
    print(f"route_gate (whole eval half, {n_eval} imgs): "
          f"median={1000*route_sum['median_s']:.3f} ms/call  p95={1000*route_sum['p95_s']:.3f} ms")
    print(f"route_gate per-image amortized: {per_image_amortized_ms:.5f} ms "
          f"({1000*per_image_amortized_ms:.3f} us)")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
