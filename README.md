# inspect-gate

A conformal three-way triage gate for industrial visual inspection on
MVTec AD. Given per-image anomaly scores from any backbone, `inspect-gate`
routes each image to `{auto-pass, auto-reject, defer}` with a **certified
escaped-defect rate** (P(auto-pass | truly defective) ≤ alpha_miss) and a
**certified false-reject rate** (P(auto-reject | truly good) ≤ alpha_fr),
plus an excess-AURC audit of whether field-standard threshold practice
beats honest random deferral at all. A thin wrapper over
[`relmetrics`](../../relmetrics) -- see
`apps-design/01-APP-mvtec-triage.md` (including its 2026-07-10 ADDENDUM)
for the full design spec this package implements.

## Quickstart

```bash
# From reliability-commons/tools/inspect-gate:
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../../                 # relmetrics (editable, from reliability-commons root)
pip install -e .                      # inspect-gate itself
pip install -e '.[test]'              # + pytest

python -m pytest                      # torch/anomalib-free, no GPU
```

```bash
# Canonical scores-JSONL in, at every downstream step (image_id, category,
# split, score [HIGHER = more anomalous], label [good|defect], defect_type).
inspect-gate calibrate --scores cal.jsonl --alpha-miss 0.10 --alpha-fr 0.05 -o gate.json
inspect-gate route     --gate gate.json --scores new.jsonl -o routing.json
inspect-gate audit     --cal-scores cal.jsonl --eval-scores eval.jsonl \
                        --train-good-scores train_good.jsonl --gate gate.json -o audit.json
inspect-gate certify   --pairs gate0.json:eval0.jsonl gate1.json:eval1.jsonl ... -o certify.json
inspect-gate report    --gate gate.json --audit audit.json --certify certify.json -o report.md
```

Box-side pilot chain: `orchestration/next_boot_inspect_gate.sh` (see below).

## Sign convention (load-bearing, stated once)

**Score = anomaly score, HIGHER = MORE ANOMALOUS** (PatchCore/Dinomaly/
anomalib's own convention). This is the OPPOSITE of the sibling
`asr-gate` package's "higher = more confident" convention -- do not port
sign assumptions across the two tools.

## The gate: zero new math

Both guarantees reduce EXACTLY to `relmetrics.conformal.SplitConformal`
-- G2 (false-reject) directly, G1 (escaped-defect) via score negation, an
exact order-statistic identity proved in `inspect_gate/gate.py`'s module
docstring (not an approximation -- checked against the design's own
floor(alpha*(n+1)) formula in `tests/test_gate.py`). The certifiability
floor (design §2.3: alpha_min = 1/(n_cal+1)) falls out of
`SplitConformal.threshold`'s existing `+inf` convention for free -- no
separate refusal branch needed in the threshold arithmetic itself.

## Honest-uncertainty rules (design §2.3)

| Rule | Exit state | Meaning |
|---|---|---|
| stratum's certifiability floor > requested alpha | certificate refused for that stratum (`t_lo`/`t_hi` = ±inf) | never silently rounds |
| category absent from calibration | `defer`, `out_of_support=True` | always-defer, loud banner |
| `--good-cal-holdout` given, per-category KS gate fails | `g2_mode="audited-not-certified"` | G1 unaffected |
| defect-type Mondrian stratum, n_def < min_defect_type_n | falls back to category-level `t_lo` | disclosed via `fallback_reason` |
| no defective calibration data at all | `no_defective_calibration=True`, G1 refused everywhere | cold-start factory case |
| crossed thresholds (t_lo >= t_hi) | overlap band defers | both guarantees survive |

## Design notes / what each module does

- `io.py` -- canonical scores-JSONL schema + validation (the ONLY
  schema-aware code in the tool).
- `splits.py` -- repeated stratified 50/50 calibration/evaluation splits
  of the MVTec test set (design §3.2, R=20, split-seed=repeat index) +
  the train-good 80/20 holdout split for the calibration-efficiency arm.
- `gate.py` -- G1 + G2 conformal calibration, Mondrian per-category (+
  optional per-defect-type) stratification, the KS exchangeability gate,
  and `route_gate` (the three-way routing decision + out-of-support
  handling).
- `certify.py` -- Clopper-Pearson intervals (textbook formula), the
  two-tier V1 pass criterion (design §1 C1), and the K1/K2 kill-gate
  statistics.
- `baselines.py` -- B1 (global fixed threshold), B2 (per-category tuned),
  B3 (train-good quantile), and the matched-deferral ambiguity band.
- `audit.py` -- excess-AURC audit of B1/B2/B3 vs `relmetrics.aurc.random_aurc`
  (B4, closed-form, never scored), matched-abstention permutation p-value
  (category-stratified), category-blocked bootstrap CI, roster-derived
  Holm correction (never hardcoded to 6).
- `reproduction.py` -- the Phase-0 image-AUROC reproduction gate
  (SOTA-REPRODUCTION-PLAN-2026-07-10.md §3): named, env-overridable
  target constants, never a hardcoded literature number trusted blindly.
- `report.py` / `cli.py` -- compact Markdown+JSON report; `inspect-gate
  {score,calibrate,route,audit,certify,report}` (see `cli.py`'s module
  docstring for the two documented deviations from the design's literal
  §2.1 CLI listing).

## Orchestration

- `mvtec_layout.py` -- the only on-disk-layout-aware code (shared by
  `phase0.py` and both `score_*.py` scripts).
- `score_patchcore.py` -- PatchCore via anomalib (lazy torch/anomalib
  imports; UNVERIFIED against a real install, see its module docstring).
- `score_dinomaly.py` -- Dinomaly, `dump-ingest` mode (robust,
  torch/repo-free, ingests a score dump the real checkout's own eval
  script produced) + `direct` mode (refuses with an actionable message --
  the exact Dinomaly API is unconfirmed at build time, see its docstring).
- `phase0.py` -- stage the MVTec tarball, freeze per-category counts, run
  the binding reproduction gate.
- `run_pilot_cell.py` -- the full calibrate/route/certify/audit loop for
  one (backbone, seed, category) cell.
- `next_boot_inspect_gate.sh` -- the Phase-0 + Phase-1 PILOT boot chain
  (3 categories x 2 backbones x 2 seeds), sourcing
  `reliability-commons/tools/boxkit/chain_lib.sh`'s
  `chain_prologue`/`chain_epilogue`, marker `INSPECT_GATE_PILOT_ALL_DONE`.
- `run_main_grid.sh` -- the FULL 15-category x 5-seed x 2-backbone grid,
  a structure-only skeleton behind `REQUIRES_PREREG_FREEZE=confirmed`
  (mirrors `asr-gate`'s `run_expansion.sh` precedent exactly).

## Deviations from the design doc's literal CLI listing

See `cli.py`'s module docstring for the full rationale: (1) `score
--backbone patchcore|dinomaly` is not in this CLI (lazy-import discipline
-- run the orchestration scripts directly, they emit canonical
scores-JSONL); (2) `certify` is an added subcommand (not in the design's
literal §2.1 listing) needed to aggregate R repeated calibrate+evaluate
cells into the V1 two-tier pass table.
