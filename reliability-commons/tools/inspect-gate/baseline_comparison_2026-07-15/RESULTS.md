# External-baseline comparison (EXPLORATORY / POST-HOC) — 2026-07-15

EXPLORATORY / POST-HOC external-baseline comparison (WORKLOAD-BENCHMARK-2026-07-15.md #2). Not confirmatory; edits no manuscript.

**Protocol** (identical to the frozen gate analysis): alpha_miss=0.1, alpha_fr=0.05, R=20 repeated stratified 50/50 cal/eval splits, seeds [0, 1, 2, 3, 4], both backbones (PatchCore, Dinomaly). Our gate numbers are READ from the frozen `gate_calibration/v1_*.json`; baseline numbers are computed on the same canonical score dumps through the same library code.

## Baselines

- **CRC** — single-threshold Conformal Risk Control (Angelopoulos et al., *Conformal Risk Control*, ICLR 2024, arXiv:2208.02814), controlling the escaped-defect (miss) risk at alpha_miss=0.10 with ONE per-category threshold and no deferral. For the 0/1 miss loss this threshold is exactly our G1 split-conformal threshold (equivalence proved in `gate.py`), so CRC and our gate share the same risk-control guarantee — the contrast is purely in what each does with the ambiguous middle: CRC must reject it (false-rejects), our gate defers it.

- **Selective prediction** — textbook risk-coverage curve (Geifman & El-Yaniv 2017): a per-category best-F1 threshold classifies each image, and the margin |score − threshold| drives abstention; we report AURC and selective risk at swept coverage.

## Headline comparison table (per benchmark, pooled over backbones × seeds × categories)

| Benchmark | Method | Cells | G1 (escaped) certified | G2 (false-reject) certified | Mean escaped-defect rate | Mean false-reject rate | Mean deferral |
|---|---|---|---|---|---|---|---|
| MPDD | **Our dual gate** (published) | 60 | 50 | 0 | 0.0663 | 0.0000 | 0.7309 |
| MPDD | CRC single-threshold (escaped@α) | 60 | 50 | n/a (no FR control) | 0.0663 | 0.3685 | 0.0000 |
| VisA | **Our dual gate** (published) | 120 | 120 | 120 | 0.0764 | 0.0296 | 0.1639 |
| VisA | CRC single-threshold (escaped@α) | 120 | 120 | n/a (no FR control) | 0.0949 | 0.1624 | 0.0000 |
| MVTec-AD | **Our dual gate** (published) | 150 | 150 | 40 | 0.0725 | 0.0046 | 0.5436 |
| MVTec-AD | CRC single-threshold (escaped@α) | 150 | 150 | n/a (no FR control) | 0.0855 | 0.0306 | 0.0000 |

*Cells = backbone × seed × category. "G1 certified" = per-cell conformal escaped-defect threshold is finite (certifiable at α given the calibration defect count); the SAME certifiability floor applies to CRC and to our G1. "G2 certified" is our false-reject conformal certification — CRC has no false-reject control, hence n/a. Escaped/false-reject rates are realized on the evaluation halves (mean of the per-cell tier-1 means over R repeats).*

## Selective-prediction risk-coverage (AURC, lower = better)

| Benchmark | Backbone | AURC | Risk @ cov=1.0 | Risk @ cov≈0.8 | Risk @ cov≈0.5 | N eval items |
|---|---|---|---|---|---|---|
| MPDD | patchcore | 0.0315 | 0.1105 | 0.0625 | 0.0246 | 1140 |
| MPDD | dinomaly | 0.0089 | 0.0667 | 0.0154 | 0.0000 | 1140 |
| VisA | patchcore | 0.0849 | 0.1828 | 0.1315 | 0.0776 | 5410 |
| VisA | dinomaly | 0.0139 | 0.0627 | 0.0180 | 0.0152 | 5410 |
| MVTec-AD | patchcore | 0.0066 | 0.0498 | 0.0095 | 0.0046 | 4320 |
| MVTec-AD | dinomaly | 0.0019 | 0.0322 | 0.0026 | 0.0000 | 4320 |

## Per-backbone detail

### MPDD

| Backbone | Method | G1 cert | Tier-2 escaped-pass | Escaped | False-reject | Deferral |
|---|---|---|---|---|---|---|
| patchcore | our gate | 25 | 26 | 0.0714 | 0.0000 | 0.7506 |
| patchcore | CRC | 25 | 26 | 0.0714 | 0.4188 | 0.0000 |
| dinomaly | our gate | 25 | 28 | 0.0612 | 0.0000 | 0.7112 |
| dinomaly | CRC | 25 | 28 | 0.0612 | 0.3182 | 0.0000 |

### VisA

| Backbone | Method | G1 cert | Tier-2 escaped-pass | Escaped | False-reject | Deferral |
|---|---|---|---|---|---|---|
| patchcore | our gate | 60 | 56 | 0.0880 | 0.0368 | 0.2627 |
| patchcore | CRC | 60 | 51 | 0.0970 | 0.2878 | 0.0000 |
| dinomaly | our gate | 60 | 60 | 0.0647 | 0.0224 | 0.0652 |
| dinomaly | CRC | 60 | 53 | 0.0928 | 0.0370 | 0.0000 |

### MVTec-AD

| Backbone | Method | G1 cert | Tier-2 escaped-pass | Escaped | False-reject | Deferral |
|---|---|---|---|---|---|---|
| patchcore | our gate | 75 | 69 | 0.0765 | 0.0066 | 0.5482 |
| patchcore | CRC | 75 | 69 | 0.0838 | 0.0521 | 0.0000 |
| dinomaly | our gate | 75 | 75 | 0.0685 | 0.0026 | 0.5390 |
| dinomaly | CRC | 75 | 68 | 0.0871 | 0.0091 | 0.0000 |

## Reading of the contrast

Both our gate's G1 and the CRC baseline control escaped-defect risk with the *same* conformal threshold and the same finite-sample guarantee, so they certify the same escaped-defect cells and realize comparable escaped-defect rates (≈ α). The difference is entirely in the ambiguous band: CRC has one cut and must send every non-passed image to auto-reject, paying the whole escaped-risk budget in FALSE-REJECTS (no abstention); our dual gate spends it on DEFERRAL, keeping false-rejects near zero at the cost of an explicit abstention rate — and additionally offers a certified false-reject (G2) guarantee that the single-threshold CRC has no mechanism to provide. The selective-prediction AURC is the field-standard reference line for that accuracy-vs-coverage trade, reported here so the paper carries a named selective baseline as well.

_All numbers traceable: our gate from `gate_calibration/v1_*.json`; baselines recomputed from the canonical scores via `runner.py`._
