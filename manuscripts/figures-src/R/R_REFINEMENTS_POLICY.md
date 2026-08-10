# R Code Refinements Policy — Inspect / RiE Figures

**Date:** 2026-08-07
**Scope:** All 18 production figures in `manuscripts/rie/figures/` (synced to `aei/figures/` and `figures-src/`).
**Pipeline:** R digests (`R/*.R`) → CSV / TeX fragments → TikZ (`tikz/*.tex`) → PDF; raster figures via R/Cairo (`samples.R`, `scoreanatomy.R`).
**Companion:** `../FIGURE_DRAWING_PRINCIPLES.md` (layout rules). This file is the **issue → R fix** contract.

---

## How to use this policy

1. Every open issue below is **blocking** for the next figure regen unless marked `ACCEPT` (science-true / intentional).
2. Fix in the **R emitter first** (`process_*.R`, `*.R`); only touch TikZ when the defect is layout-only (panel letters, shared legend geometry).
3. After edits: `make <fig>.pdf && make sync-rie sync-aei` then re-raster at 200 dpi under `review/audit/`.
4. Do not invent labels, dodge values, or drop points to hide empty science (e.g. MPDD both-cert ≡ 0). Annotate; do not invent.

---

## Global rules (apply to every R script)

| ID | Rule | R enforcement |
|---|---|---|
| G1 | Titles must disambiguate **backbone × benchmark × category** when any two panels share a category | `sprintf("%s / %s / %s", backbone, benchmark, category)` — never omit `backbone` |
| G2 | Shared legend once, **outside** axes, horizontal, no fill/border | Emit one legend block; TikZ/Cairo must not draw per-panel legend boxes |
| G3 | When two series coincide, keep both readable | Prefer hollow vs filled marks + slight x-dodge in categorical panels; never hide a series |
| G4 | Log / categorical axes need readable tick labels | Emit explicit tick labels in CSV/TeX; never leave bare tick marks |
| G5 | Benchmark strings are canonical | `MVTec AD`, `VisA`, `MPDD` — never `MVTec-AD` / `mvtec` / mixed case in one figure |
| G6 | Panel letters `(a),(b),…` 9 pt bold black in left gutter, after axis ends | TikZ `\panellabel` / `\panellabelshift`; Cairo: `panel_label_text()` + `PANEL_LABEL_PT` from `_figconst.R` |
| G7 | Annotation contrast | Status / ovlp / callout text ≥ grey35; never near-white on white |
| G8 | Color semantics are single-purpose per figure | Do not reuse “certified green” as a dataset color in the same multi-panel figure |
| G9 | Percent rates stay in `[0, 100]` (or `[0, 1]` if fractional) with padding | `xlim` / `coord_cartesian` with pad; values exactly 100 must not sit on the spine |
| G10 | Sync targets after every regen | `rie/figures/`, `aei/figures/` (= `papers/inspect-aei/figures`), `figures-src/*.pdf` |

---

## Per-figure issues (current assets, 2026-08-07 audit)

Severity: **H** = blocks submission polish · **M** = clarity / consistency · **L** = nice-to-have · **ACCEPT** = science-true, keep with annotation

### fig-overview (TikZ-only; not R)
| Sev | Issue | Action |
|---|---|---|
| M | “floor unmet: REFUSE” arrow lands on DEFER — nomenclature clash | Clarify label → `floor unmet → DEFER (refuse certify)` in `tikz/fig-overview.tex` |
| L | Stage box heights uneven (CERTIFY taller) | Balance node heights; out of R scope |

### fig-scoreanatomy — `R/scoreanatomy.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Panels **(b)** and **(d)** both title as `VisA pcb1 / G1 + G2 certified` — (b)=`patchcore`, (d)=`dinomaly` but backbone omitted | Change `title(main=...)` to include `cell$backbone` (e.g. `VisA pcb1 · dinomaly`) |
| **H** | Panel (d): `t_lo` / `t_hi` labels collide (band width ~0.008) | When `hi-lo < 0.05 * span`, stack labels (lo left/below, hi right/above) or use callouts with leader lines |
| M | Overlapping hist bars muddy to brown | Keep alpha; draw good then defect with hatch or outline on top series |
| M | Panel (c) y-ticks show decimals (`0.0…`) vs integer counts elsewhere | Force integer y breaks when `ymax >= 1` via `pretty(..., n=4)` + `as.integer` |
| L | Unequal x-scales across panels | ACCEPT if caption states per-panel autoscaling; else shared x only within certified/refusal groups |

### fig-samples — `R/samples.R`, `R/_samples_layout.R`
| Sev | Issue | R refinement |
|---|---|---|
| ACCEPT | AUTO-PASS of GT-defect tiles (escaped examples) | Keep — figure is illustrative of three-way decisions; caption already owns interpretation |
| M | “floor refusal” overlay on DEFER tile | Ensure overlay never covers score `s=` or GT-zoom; keep contrast ≥ WCAG-ish dark-on-light or white-on-dark with stroke |
| L | Cross-row score thresholds look inconsistent | ACCEPT — thresholds are per category/backbone |

### fig-categorymap (TikZ + data CSV)
| Sev | Issue | R refinement |
|---|---|---|
| M | Cell widths stretch with category count (MPDD wide, MVTec narrow) | If regenerating digests: emit fixed cell aspect hint; TikZ: equal cell width across panels or accept with caption |
| M | Truncated names (`caps.`, `hazel.`) | Prefer longer abbreviations from the shared lookup in `data/gen_categorymap_tex.R` |
| L | Certified 0.0 (solid) vs refused 0.0 (hatch) subtle | Keep hatch; strengthen legend wording |

### fig-alphafrontier — `R/process_alphafrontier.R`
| Sev | Issue | R refinement |
|---|---|---|
| M | Coincident patchcore/dinomaly marks hide one series | Emit dodge column or dual mark styles (circle hollow / square filled) in CSV for TikZ |
| M | `op.` annotation only on panel (a) | Emit `op_label` once for top row or for every panel; never silent on some panels |
| ACCEPT | Panel (f) flat zero + “floor refuse” note | Keep annotation; do not invent non-zero points |
| L | Repeated axis labels on every panel | TikZ: outer labels only (bottom row / left column) |

### fig-calfraction — `R/process_calfraction.R`
| Sev | Issue | R refinement |
|---|---|---|
| M | Markers overlap on 5/6 panels | Same as frontier: dodge or dual mark style in emitted coordinates |
| ACCEPT | Panel (e) all-zero both-cert + floor-refusal notes | Keep |
| L | X positions categorical-equidistant for `{0.5,0.3,0.2,0.15,0.1}` | ACCEPT if caption says “sweep points”; optional true numeric spacing |

### fig-calplanning — `R/process_calplanning.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Panel (c) legend large and inside data | Move legend outside (top gutter / below panel); shrink keys; TikZ `legend style={draw=none,fill=none}` |
| M | Panels (b)/(d) legends inside axes | Outside per G2 |
| M | Panel (d) dashed/dotted pool marks unexplained in legend | Emit legend entries for required-$n_{cal}$ / observed marks from R |

### fig-crcbaseline — `R/process_crcbaseline.R`
| Sev | Issue | R refinement |
|---|---|---|
| M | Panel (a) markers cluster near 0 — hard to separate rates | Small vertical dodge by rate type within each benchmark row |
| M | Panel (c) MPDD bars ≈ 0 invisible | State that CRC certifies zero cells on every benchmark/backbone; add `0` text on near-zero bars if the expanded profile is rebuilt |
| L | Legend positions inconsistent across a/b/c | Standardize outside-top / outside-bottom |

### fig-opcost — `R/process_opcost.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Naming inconsistency: `MVTec-AD` vs `MVTec AD`; `gate` vs `Gate` | Canonicalize in R before emit (G5); title-case method keys once |
| **H** | Panel (d) log y-axis nearly unlabeled (`10^{-2}`, `10` only) | Emit full log tick set in TeX fragment (`10^{-3}…10^{1}`) |
| M | Panel (b) value labels overlap lines | Offset labels by series (above/below) or use leader offsets in TikZ from R-supplied anchors |
| M | Panel (a) repeats `low/mid/high` thrice | Prefer facet-style group labels (dataset strip + one low/mid/high cycle) |

### fig-g2delta — `R/process_g2delta.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Green overloaded: certified (a/b), remedy (c), MPDD (d) | Split palettes: status greens in a/b; remedy uses distinct hue; datasets use Okabe–Ito blue/orange in (d) |
| M | Excess top whitespace / floating legends in (c)/(d) | Tighten `yshift` / legend anchors; shared top legend for a–b only |
| M | Panel (c) primary at 100% sits on right spine | Pad xlim to ~105 or inset mark; data value 100 is valid |
| L | Vertical class codes hard to read | 45° ticks or two-line short codes from R `short` column |

### fig-binding-escaped / fig-binding-fr — `R/binding.R`
| Sev | Issue | R refinement |
|---|---|---|
| M | Legend inside plot; deferral % column feels detached | Place legend below; emit deferral as aligned extra axis column with fixed `x` in TeX |
| M | Dense 33-row FR panel | Keep sort key explicit in R (`order(-b1_rate)`); optional thin horizontal guides |
| L | Green/orange vs red-green CVD | Already Okabe-ish; keep; do not switch to red/green |

### fig-jointmon — `R/jointmon.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Panel (d) x-axis “corruption + level” has **ticks but no labels** | **FIXED 2026-08-09:** short labels `brig-1…defo-3` in TikZ; heatmap cells from R |
| **H** | Figure shows only panels **a** and **d** (labels skip b/c) | **FIXED 2026-08-09:** restored full a–d (ROC points, $z$ cloud, 2×12 catch/FA heatmap) via `jointmon.R` → `out/jointmon-panel-*.tex` |
| M | “defect KS” packs 4 arms on one y-tick | **FIXED 2026-08-09:** per-arm `yoff` ±0.16 + PC○/DM□ × G1/G2 encoding |
| M | Legend inside left panel | **FIXED 2026-08-09:** shared horizontal a/b legend above titles |

### fig-mondrian-1 / fig-mondrian-2 — `R/normalize_mondrian.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Colorbar overlaps bottom rows (`zipper / …`); “rate (%)” floats | Increase bottom margin in TikZ; R must not emit rows into colorbar band; verify with bbox audit |
| M | White cell vs 0% vs missing ambiguous | Encode missing as hatch or `NA` glyph; 0% as lightest scale color (not empty) |
| M | Repeated `category / type` on every row | Emit grouped labels (category once, types indented) in row TeX |
| L | Underscored type names | Prettify in R: `broken_large` → `broken large` |

### fig-deferral — `R/deferral.R`, `R/process_deferral.R`
| Sev | Issue | R refinement |
|---|---|---|
| M | Heavy mark overlap (esp. MVTec / MPDD) | Vertical dodge by backbone within category |
| M | “K2 vacuity 0.80” vertical label collides with points | Move label to top of line; shorten to `K2 0.80` |
| L | Abbreviated MPDD names (`br. black`) | Use shared short-name table consistent with g2delta / categorymap |

### fig-validity — `R/validity.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Panel (b) MPDD empty — looks like a bug | Keep if G2 refused; **must** annotate (e.g. existing “G2: 0/6 refused” should sit at MPDD column, not only top-right) |
| M | Overplotting in (a)/(b) | Alpha + jitter width capped; or beeswarm via R then fixed coords to TikZ |
| M | Mixed tick notation (`0.1` vs `5·10^{-2}`) | Uniform decimal or scientific in emitted tick labels |
| M | Panels (c)/(d) count labels overlap / float | `ggrepel`-style offsets: precompute non-overlapping label coords in R CSV |

### fig-xdet — `R/xdet.R`
| Sev | Issue | R refinement |
|---|---|---|
| **H** | Panel (a) repeats `DM to PC` / `PC to DM` without benchmark grouping on axis | Emit hierarchical x labels: top strip `MVTec AD | VisA | MPDD`, bottom direction |
| M | Panel (b) benchmark names parked far right | Group labels in left margin (like Mondrian categories) |
| M | Panel (c) `ovlp …%` too faint | Emit with `col=grey35` minimum (G7) |
| M | Panel (d) tiny marks, heavy corner overplot | Larger marks + alpha; optional jitter &lt; 1 pp |

---

## Script → figure ownership

| R script | Outputs / figures |
|---|---|
| `_figconst.R` | Shared fonts + route colors (G5/G8) |
| `samples.R` + `_samples_layout.R` | `fig-samples.pdf` |
| `scoreanatomy.R` | `fig-scoreanatomy.pdf` |
| `process_alphafrontier.R` | `fig-alphafrontier.pdf` |
| `process_calfraction.R` | `fig-calfraction.pdf` |
| `process_calplanning.R` | `fig-calplanning.pdf` |
| `process_crcbaseline.R` | `fig-crcbaseline.pdf` |
| `process_opcost.R` | `fig-opcost.pdf` |
| `process_g2delta.R` | `fig-g2delta.pdf` |
| `binding.R` | `fig-binding-escaped.pdf`, `fig-binding-fr.pdf` |
| `jointmon.R` | `fig-jointmon.pdf` |
| `normalize_mondrian.R` | `fig-mondrian-1.pdf`, `fig-mondrian-2.pdf` |
| `deferral.R` + `process_deferral.R` | `fig-deferral.pdf` |
| `validity.R` | `fig-validity.pdf` |
| `xdet.R` | `fig-xdet.pdf` |
| (TikZ-only) | `fig-overview.pdf`, `fig-categorymap.pdf` |

---

## Priority fix queue (R first)

1. **scoreanatomy.R** — backbone in titles; crowded `t_lo`/`t_hi` on panel d
2. ~~**jointmon.R** + TikZ — x tick labels; restore a–d~~ **DONE 2026-08-09**
3. **process_opcost.R** — canonical names; full log ticks on latency panel
4. **process_g2delta.R** — split color semantics; pad 100% marks
5. **xdet.R** — hierarchical benchmark×direction labels
6. **validity.R** — MPDD empty-state annotation placement; label collision
7. **normalize_mondrian.R** + TikZ — colorbar margin; NA vs 0 encoding
8. **process_calplanning.R** / **process_crcbaseline.R** / frontier+calfraction — legends out; dual-mark dodge
9. **binding.R** / **deferral.R** — legend/guides polish

---

## Definition of done (per figure)

- [ ] Visual 200 dpi audit: no clipped text, no legend on data, no colliding labels
- [ ] `pdffonts` LM/CM only (Makefile `verify`)
- [ ] Present in `rie/figures/`, `aei/figures/`, `figures-src/` with identical bytes
- [ ] Issue row in this file flipped to **FIXED** with date + script commit note

---

## Asset sync commands

```bash
cd manuscripts/figures-src
make fig-scoreanatomy.pdf   # example
make sync-rie sync-aei      # after verify
# papers/inspect-aei/figures ← aei/figures (symlink)
# papers/inspect-rie/figures ← rie/figures (symlink)
```
