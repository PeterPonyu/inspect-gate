# Canonical Sample Assets for fig-samples.pdf

## Provenance

These images were extracted from the canonical frozen `fig-samples.pdf`
published in the v0.3.0 archive and then promoted to the R pipeline's
versioned source assets:
- Extraction date: 2026-08-06
- Extraction method: `pdfimages -png`
- Total extracted PDF image objects: 18
- Full sample tiles: 12
- Ground-truth zoom insets: 6

## Content

The objects reconstruct the frozen four-row gate-decision grid:
- 12 full sample tiles spanning MPDD/VisA, good/defect, and pass/defer/reject
- 6 ground-truth zoom insets for the two defective rows

## Layout

Grid: 4 rows × 3 columns
- Rows: MPDD good, MPDD defect, VisA good, VisA defect
- Columns: Auto-Pass, Defer, Auto-Reject

These PNGs are the **image objects only** (tiles + GT zooms). Borders,
column headers, row labels, scores, `floor refusal`, and `GT zoom` captions
are drawn by `../R/samples.R` using geometry from `../R/_samples_layout.R`.

## Verification

See `manifest.txt` for SHA256 hashes of all extracted images.
Rebuild: `cd .. && Rscript R/test_samples_layout.R && Rscript R/samples.R`
Sync: `make -C .. sync-paper` (or copy `fig-samples.pdf` into
`rie/figures/` and `aei/figures/`).
