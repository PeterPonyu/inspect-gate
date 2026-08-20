# Three-way defect triage gate

Anomaly detectors rank defects; they do not define a safe operating decision.

This repository holds the protocol and frozen records for a pre-deployment
**three-way gate** on visual-inspection anomaly scores: auto-pass, human-defer,
or auto-reject. Two finite-sample split-conformal certificates travel with the
band.

- **G1 (escaped-defect):** P(auto-pass | defective) ≤ α_miss.
- **G2 (false-reject):** P(auto-reject | good) ≤ α_fr.

When the calibration floor α_min = 1/(n_cal+1) is unmet, that auto-action is
emptied and the axis is **audited-not-certified**. Refusal is a result, not an
empty cell. Score convention: higher = more anomalous.

Frozen archive: Zenodo concept
[10.5281/zenodo.21392290](https://doi.org/10.5281/zenodo.21392290)
(v0.4.1 record [10.5281/zenodo.21854312](https://doi.org/10.5281/zenodo.21854312)).
Code license: MIT.

## Confirmatory evidence (MVTec AD)

Primary protocol, α_miss = 0.10, α_fr = 0.05:

| Quantity | Value |
| --- | --- |
| G1 certified | 15/15 categories |
| G2 certified | 4/15 (cable, hazelnut, screw, transistor) |
| Dual-gate pooled | escaped 7.3% · false-reject 0.5% · deferral 54.4% |
| Single-threshold CRC | escaped 8.5% · false-reject 3.1% · deferral 0% |
| α_miss = 0.01 | 0/33 categories certified (need n_cal^def ≥ 99) |

G2 is the scarce certificate: the good-pool floor is tighter than the defect
pool. Coverage (deferral %) is a staffing number, not a quality badge.

## Exploratory pool-size extremes

VisA and MPDD are tagged exploratory. They are not a second confirmatory claim.

- **VisA:** both-axis certification 12/12; gate false-reject 3.0% at 16.4%
  deferral versus CRC 16.2% (escaped-defect 7.6% vs 9.5%).
- **MPDD:** G2 0/6 under the primary protocol. Reported 0.0% false-reject at
  73.1% deferral is a high-review diagnostic (empty auto-reject band), not a
  dual-certificate success.

## Honesty

Calibrated gates do not transfer across detectors (160/165 G1 violations
PatchCore → Dinomaly; same-detector diagonal 30/30). Synthetic good-score
drift screening misses 34% of accepted PatchCore cells above the escaped-defect
target; a defect-score marginal test catches about 5% of those residual cells.
Temporal production drift is untested.

Evidence supports a calibration/refusal protocol on academic AD benchmarks,
not a portable production-line certificate.
