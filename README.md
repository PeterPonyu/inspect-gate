# inspect-gate

Inspect / dual-gate reliability research theme: package code, orchestration,
tests, frozen experiment statistics, and manuscripts needed to regenerate the
writeup and figures.

Code archive: Zenodo DOI [10.5281/zenodo.21392291](https://doi.org/10.5281/zenodo.21392291)
(reserved; draft record, activates on publish).

A conformal three-way triage gate for industrial visual inspection on
MVTec AD, VisA, and MPDD. Given per-image anomaly scores from any backbone,
`inspect-gate` routes each image to `{auto-pass, auto-reject, defer}` with a
**certified escaped-defect rate** (P(auto-pass | truly defective) ≤ alpha_miss)
and a **certified false-reject rate** (P(auto-reject | truly good) ≤ alpha_fr),
plus an excess-AURC audit of whether field-standard threshold practice beats
honest random deferral.

This repository is the theme home (same pattern as `materials-mlip-research`).
`reliability-commons` may symlink here for portfolio glue; it does not own the
Inspect manuscript statistics.

## Layout

| Path | Contents |
|------|----------|
| `inspect_gate/` | Python package (calibrate / route / audit / certify / report) |
| `orchestration/` | Pilot and full-score runners |
| `tests/` | CPU-only pytest suite (no torch/anomalib required) |
| `manuscripts/rie/` | RiE venue manuscript |
| `manuscripts/aei/` | AEI mirror |
| `manuscripts/jim/` | JIM venue variant |
| `manuscripts/figures-src/` | Pure R + TikZ figure SSOT (`make all`) |
| `*_YYYY-MM-DD/` | Frozen `results.json` / analysis slices used by figures and tables |

Large staging trees and model weights (`visa_staging`, `mpdd_staging`, Dinomaly
weight dumps) are **not** tracked here. See `DATA_MANIFEST.md` for external
inputs.

Desktop portfolio shortcuts (under `ml-reliability-research/papers/`):

- `inspect-canonical` → `inspect-gate/manuscripts`
- `inspect-rie` → `inspect-gate/manuscripts/rie`
- `inspect-aei` → `inspect-gate/manuscripts/aei`

## Quickstart (package)

```bash
# From this repo root (sibling of reliability-commons):
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../reliability-commons   # provides relmetrics
pip install -e .
pip install -e '.[test]'

python -m pytest   # torch/anomalib-free, no GPU
```

```bash
inspect-gate calibrate --scores cal.jsonl --alpha-miss 0.10 --alpha-fr 0.05 -o gate.json
inspect-gate route     --gate gate.json --scores new.jsonl -o routing.json
inspect-gate audit     --cal-scores cal.jsonl --eval-scores eval.jsonl \
                        --train-good-scores train_good.jsonl --gate gate.json -o audit.json
inspect-gate certify   --pairs gate0.json:eval0.jsonl gate1.json:eval1.jsonl ... -o certify.json
inspect-gate report    --gate gate.json --audit audit.json --certify certify.json -o report.md
```

Box-side pilot chain: `orchestration/next_boot_inspect_gate.sh`.

## Build figures / manuscript

```bash
cd manuscripts/figures-src
make r-data
make all
make sync-rie sync-aei
```

R scripts resolve frozen JSON via `../../../<artifact>/results.json` from
`figures-src/R/`.

```bash
cd manuscripts/rie
ln -sfn ../refs.bib refs.bib
latexmk -pdf paper_rie.tex
```

## Notes

- Score convention: **HIGHER = MORE ANOMALOUS** (opposite of `asr-gate`).
- `calfraction_sweep_2026-07-19/results.json` may be absent. When it is, FRACS
  and the six `out/calfraction-*-{cert,def}.tex` fragments are regenerated from
  the frozen SSOT `manuscripts/figures-src/data/frozen/calfraction_data.csv`
  (copied into `R/calfraction_data.csv` by `process_calfraction.R`). That frozen
  path sits outside `make clean-data`'s wipe of `R/*.csv` / `out/*.tex`. This is
  a **calfraction-JSON-absent** rebuild path only — other `process_*.R`
  generators still require their local JSON digests.
- Sibling portfolio glue: `reliability-commons/tools/inspect-gate` → this repo.
