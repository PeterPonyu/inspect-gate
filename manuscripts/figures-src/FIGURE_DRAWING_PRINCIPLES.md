# Figure drawing principles

A standing checklist for every manuscript figure in this portfolio (Inspect/RiE
first, then the other five papers). Derived from the 2026-08-07 figure-quality
review. Apply all of these on every figure; the per-figure notes at the bottom
record how each Inspect figure was brought into compliance.

**R implementation contract (open issues → script fixes):** see
[`R/R_REFINEMENTS_POLICY.md`](R/R_REFINEMENTS_POLICY.md).

## Layout / containment
1. **No text overflow.** Text must fit inside its container (schematic boxes,
   panels, cells). If it spills, shrink the font or widen the box — never let a
   label cross the box edge.
2. **Axis range encloses the data.** The plotting range must contain every
   statistical/graphical element with padding. Points, bars, whiskers, CI bands
   must not sit on or past the axis edge; the axes should visibly *cover* the
   data, not clip it.
3. **Panel footprint includes text + legend.** When arranging panels, compute
   each panel's true footprint — the axis box PLUS its tick/row labels PLUS its
   legend. Lay panels out by that footprint, not by the bare axis box. This is
   what stops left-column row labels from colliding with the neighbour panel.
4. **Panel labels (a,b,c,d) go top-left** of each panel, outside the data.

## Arrows / lines
5. **Every intended arrowhead is present** and every path connects the intended
   anchors. Check each arrow individually — a symmetric-looking set often has
   one or two heads silently missing.
6. **Dashed vs solid is deliberate and uniform.** A line that should be dashed
   must be dashed along its whole length; watch for renderer bugs that leave a
   segment (often a corner) solid.

## Legends
7. **No background fill.** Legends must be transparent — a white/opaque legend
   box occludes the data underneath it.
8. **No border/frame** around the legend.
9. **Legend lives outside the plotting area.** Place it in the whitespace
   *between* panels or below the row, never inside the axes.
10. **Prefer a single horizontal row** for the legend. Vertical stacks waste
    horizontal space and force excess vertical whitespace.
11. **Share one legend across panels** when the key is common: a single legend,
    centred in the shared whitespace between the panels it serves, instead of a
    duplicate per panel.
12. **Small inline legends are OK only in a single-panel standalone figure.**
    In any multi-panel figure the legend goes outside per (9).

## Colour / text
13. **No decorative colour.** Colour must carry meaning (encode a data
    dimension). Don't recolour a column/mark that is already identified by
    position or an all-black text label. Neutral grey for non-semantic marks.
14. **Titles short; verbose text → caption.** Keep in-figure titles terse
    (abbreviate). Move any long explanation or redundant annotation (e.g.
    "scores shown below each image") out of the figure body and into the LaTeX
    caption.

## Scientific appropriateness
15. For figures flagged science-only (Inspect 4,5,6,14,15,16), verify the
    encoding is an appropriate representation of the underlying evidence and the
    stated conclusion actually follows, before touching layout.

---

## Per-figure remediation log (Inspect / RiE)

### fig-samples (Figure 3) — 2026-08-07
- **Defect:** left-margin row labels (`MPDD - good/defect`, `VisA - defect`)
  were overprinted by the AUTO-PASS tile column; GT-zoom captions sat on the
  inset crop in white and read as clipped.
- **Fix:** shared geometry in `R/_samples_layout.R` — wider canvas, right-shifted
  columns with an explicit label/tile gap test, GT-zoom label placed *below*
  the inset in dark text. Regenerated via `R/samples.R`.
- **Assets synced:** `figures-src/fig-samples.pdf`, `rie/figures/`, and
  `aei/figures/`.
- **Verified:** `Rscript R/test_samples_layout.R` PASS (label/tile gap 0.263 in;
  zoom pad 0.035 in); full row labels visible in 220 dpi raster; LM fonts
  embedded.

### Panel-label / title rule (all multi-panel figures)
- Panel letters via `\panellabel{axname}{a}` **after** `\end{axis}` (axis clip
  swallows in-axis nodes at `rel axis cs:…,1.1`).
- Park letters in the **left gutter** of the axis frame; titles use
  `inspect/centertitle` (centered over the plot box only). Never put the
  letter on the title baseline.

### fig-alphafrontier (Figure 5) — 2026-08-07
- **Sci bug:** R key used `am%.2f` (`am0.20_…`) but JSON stores `am%g`
  (`am0.2_…`), so α∈{0.2,0.1} points were silently dropped. Fixed in
  `process_alphafrontier.R`; all five grid points now plot.
- **Sci true:** MPDD both-certified flat at 0 is a measured floor refusal
  (not a render failure); annotated in panel f.
- **Layout:** shared top legend; centered titles; gutter panel labels a–f.

### fig-calfraction (Figure 6) — 2026-08-07
- **Sci bug:** TikZ emitter did `cert_mean * n_cats` even though `cert_mean`
  is already a category **count** → MVTec 4 became 60, VisA 12 became 144
  (off-scale). Fixed in `process_calfraction.R`. X ticks match frozen fracs
  `{0.5,0.3,0.2,0.15,0.1}` (no 0.4 in sweep).
- **Sci true:** MPDD both-certified ≡ 0 and deferral→1.0 at frac 0.10 are
  real floor refusals (6/6); annotations kept, no longer clipped.
- **Layout:** column titles only on top row; gutter panel labels; shared legend.

### fig-jointmon (Figure 15) — 2026-08-09
- **Defect:** TikZ SSOT had only panels a+d (skipped letters); panel d was a
  collapsed single catch-rate line instead of the captioned catch/FA heatmap;
  a/b chrome had bottom-right in-axis legend and sparse categorical rows.
- **Fix (R → CSV/TeX fragments → hand-authored TikZ):** `R/jointmon.R` emits
  panels a–d digests + `out/jointmon-panel-{a,b,c,d}.tex` (never hand-edit
  fragments). `tikz/fig-jointmon.tex` is 3-row layout (a|b, c full, d full)
  with gutter `\panellabel`, shared horizontal a/b legend above titles,
  tight a–b gap, compact ARM_DY, and 2×12 heatmap with `brig-1…defo-3` ticks.
- **Build:** `Rscript R/jointmon.R && make fig-jointmon.pdf` then copy to
  `rie/figures` + `aei/figures` (or `make sync-paper` when full suite green).
- **Verified:** LM/CM-only fonts; panel-d catch rates match frozen 11/15…18/18;
  `paper_rie.pdf` recompiled with synced figure.

### fig-calplanning / crcbaseline / opcost / g2delta (Figures 7–10) — 2026-08-07
- **Defect:** Incomplete TikZ PDFs — panel letters clipped inside axes,
  titles entangled with letters, fig-opcost / fig-g2delta missing panels
  c–d, calplanning panel c plotted certifiable fraction (caption needs
  *non*-certifiable shortfall).
- **Fix (production path = R → CSV → TikZ → pdflatex):**
  - `process_calplanning.R`: panel c emits $1-$certifiable; panel d adds
    required-$n_{\mathrm{cal}}$ marks. `tikz/fig-calplanning.tex` uses
    `\panellabel` + centered titles.
  - `process_crcbaseline.R`: hollow gate / filled CRC with `forget plot` on
    filled marks; `\panellabel` + centered titles.
  - `process_opcost.R`: panels c–d from `economic_v1_2026-07-21` +
    `latency_2026-07-13`; 2×2 `tikz/fig-opcost.tex`.
  - `process_g2delta.R`: panels c–d from `remedy_pricing_2026-07-19` +
    seed rollups; 2×2 `tikz/fig-g2delta.tex`.
- **Build:** `make fig-calplanning.pdf fig-crcbaseline.pdf fig-opcost.pdf fig-g2delta.pdf`
  then `make sync-rie` (Creator must be TeX, not Matplotlib).
- **Assets synced:** `rie/figures/`, `aei/figures/`, `figures-src/*.pdf`.
