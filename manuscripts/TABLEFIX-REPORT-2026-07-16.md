# TABLEFIX report — inspect-gate manuscripts — 2026-07-16

Scope: `paper.tex` (canonical), `jim/paper_jim.tex` (JIM/Springer fallback kit),
`aei/paper_aei.tex` (AEI/Elsevier primary kit), and `figures-src/{fig-overview,fig-crcbaseline,
fig-categorymap}.tex`, per `docs/records/REVIEW-DIRECTIVE-2-2026-07-16.md` (including the
2026-07-16 mid-task clarification: EXPAND is the preferred remedy for small tables, ahead of
merge/prose/keep).

Backups: `*.bak-pre-tablefix2` next to every edited file (root, `jim/`, `aei/`, `figures-src/`).

## 1. Table verdicts

| Table | Rows before | Verdict | Rows after |
|---|---|---|---|
| `tab:repro` (reproduction gate) | 6 | KEEP — already ≥5 | 6 |
| `tab:floors` (per-category certifiability) | 15 + 1 summary | KEEP — already ≥5 | unchanged |
| `tab:v1` (V1 tier-1 kill-gates) | 10 | KEEP — already ≥5 | unchanged |
| `tab:c2` (confirmatory excess-AURC audit) | 4 | **EXPAND** | 8 |
| `tab:tier2` (V1 tier-2 grading) | 2 | **EXPAND** | 27 + 2 totals |
| `tab:crcbaseline` (CRC baseline) | 6 | KEEP — already ≥5 | unchanged |
| `tab:latency` (latency/deployment cost) | 4 | **KEEP with justification** | 4 |

Only `tab:c2`, `tab:tier2`, and `tab:latency` were flagged (<5 data rows). No table was merged or
converted to prose in the final state — all-frozen expansion data was found for two of the three,
and the third genuinely has none.

### tab:c2 — EXPANDED (4 → 8 rows)
The table only showed the MVTec confirmatory family (4 rows: {B1,B2}×{PatchCore,Dinomaly}). The
VisA post-freeze exploratory counterpart was already computed
(`c2_tier2_2026-07-13/c2_visa.json`) and only summarized in prose. Added its 4 rows
(PatchCore/Dinomaly × B1/B2, excess-AURC seed ranges $0.044$–$0.106$), verified against the JSON's
`per_seed_raw` records — every added number traces exactly; the pooled range matches the
pre-existing prose statement `[0.044, 0.106]` verbatim. Caption/column header updated
(added a `Benchmark` column, noted MVTec=confirmatory vs. VisA=exploratory). `\ref{tab:c2}` is
cited from both the MVTec and VisA paragraphs, in existing first-occurrence order.

### tab:tier2 — EXPANDED (2 → 27 data rows + 2 totals rows)
The table only showed 2 rows: axis-level aggregate pass/fail/excluded totals for MVTec AD. The
underlying `tier2_mvtec.json`/`tier2_visa.json` `per_cell` records carry a verdict
(pass/fail/unpowered/refused) for every (backbone, category, seed) cell — genuinely
per-category detail that had been summarized away into two rows. Aggregated per category
(10 cells = 2 backbones × 5 seeds per category for MVTec's 15 categories and VisA's 12), the
table now shows one row per category for both benchmarks, plus two totals rows. All totals were
cross-checked programmatically against the pre-existing aggregate numbers already cited in the
surrounding prose (MVTec escaped 15/115/20, false-reject 110-refused+40-unpowered; VisA escaped
17/103/0, false-reject 4/66/50/0) — exact match in every case. No number was invented; every row
traces to the frozen `per_cell` dict. AEI's version wraps the tabular in `\resizebox` (its 360pt
preprint column can't fit the natural width of a 3-column table with these labels).

Earlier in this same session I had first converted `tab:tier2` to prose (its 2-row aggregate content
was already narrated almost verbatim in the surrounding paragraph); after the user's
EXPAND-preferred clarification arrived, I checked for expansion data, found the per-cell
records, and rebuilt it as the expanded table above instead — the intermediate prose-only version
never reached a final compiled state that was reported anywhere.

### tab:latency — KEPT with justification (4 rows, unchanged)
Checked `latency_2026-07-13/gate_latency.json` and `dinomaly_latency.json` for per-category or
per-seed rows to surface: none exist. Both are single measured operating points (`calibrate_gate`,
`route_gate` for the gate; one 250-image batch-1 run + one batched run for Dinomaly) with only
descriptive statistics (median/mean/min/max/p95/std) of the *same* measurement, not separate
per-class/per-dataset/per-seed entities — there is nothing to expand into more rows without
duplicating noise samples as fake "rows." No merge partner exists (no other latency table in the
paper). The content is 8 distinct numbers, too many for the directive's "1–3 numbers" prose
criterion, so conversion to prose was reverted (I had tried it, then reverted once the no-expansion
finding was confirmed and re-read the narrowed prose criterion). This is a venue-conventional
cost/latency comparison table (backbone forward-pass budget vs. gate overhead) — load-bearing
as-is. Future data that would grow it: a per-category calibration-time breakdown, if ever measured
per MVTec/VisA/MPDD stratum instead of pooled over the calibration half; none is currently frozen.
A `% KEEP (directive #2 remedy d): ...` comment recording this was added directly above the table
in all three files.

All `\ref{tab:*}` sites remain in first-occurrence text order; no table was removed, so no
`\ref` had to be redirected except the two brief round-trips on `tab:tier2`/`tab:latency`
described above (both fully restored).

## 2. Figure typography — before / after effective size

Native PDF widths (unchanged by the font edits — node geometry uses fixed absolute
coordinates/text-widths, not font-size-driven boxes): `fig-overview.pdf` 308.7pt,
`fig-crcbaseline.pdf` 280.5pt, `fig-categorymap.pdf` 446.8pt → 451.2pt (widened slightly by the
larger fonts).

Column widths: canonical/JIM `\textwidth` = 469.8pt (article, 11pt, 1in margins — identical for
both). AEI (`elsarticle[preprint,11pt]`) `\textwidth` = 360.0pt — narrower preprint-review column,
not a defect, but it means AEI needs different `\includegraphics` width fractions than
canonical/JIM to land in the same effective-size band.

| Figure | Venue | Include width | Scale | Native font (pt) | Effective before | Effective after |
|---|---|---|---|---|---|---|
| fig-overview | canonical/JIM | 0.8→0.8\linewidth | 1.218 | 8/7.2/7.5 → 6.8/6.2/6.4 | 8.77–9.74 | **7.55–8.28** |
| fig-overview | AEI | 0.8→**1.0**\linewidth | 0.933→1.166 | (same) | 6.72–7.46 (**below 7pt floor**) | **7.23–7.93** |
| fig-crcbaseline | canonical/JIM | 0.62→0.62\linewidth | 1.038 | 7–8 (unchanged) | 7.27–8.31 | 7.27–8.31 (no change needed) |
| fig-crcbaseline | AEI | 0.62→**0.84**\linewidth | 0.796→1.078 | (same) | 5.57–6.37 (**below 7pt floor**) | **7.55–8.63** |
| fig-categorymap | canonical/JIM | 1.0→1.0\linewidth | 1.051→1.041 | 6.8–8.6 → 9/9.2 | 7.15–9.04 | 9.37–9.58 |
| fig-categorymap | AEI | 1.0→1.0\linewidth | 0.806→0.798 | (same) | 5.48–6.93 (**below 7pt floor**) | **7.18–7.34** |

All three floor violations were in the AEI (primary venue) kit — its narrower preprint column,
combined with the canonical-tuned `\includegraphics` fractions, put every figure below 7pt
effective there even before considering the family-inconsistency problem. Fixed by (a) unifying
the native font family per figure (fig-overview shrunk since it was over-scaling at 1.22× vs. the
other two; fig-categorymap's 6.8pt floor and 8.6pt bold title raised/unified to 9–9.2pt), and (b)
widening AEI's `fig-overview`/`fig-crcbaseline` include fractions to compensate for its narrower
column (fig-categorymap was already at `\linewidth` — its only lever was the font-family fix,
which by itself was enough since AEI's post-fix effective floor is 7.18pt). Post-fix, canonical/JIM
sit in a tight 7.27–9.58pt band and AEI sits in an even tighter 7.18–8.63pt band — both comfortably
clear the 7pt floor and land close to the ~8–9pt target.

fig-categorymap's `\swatchx` legend anchor was moved 5.9→8.0 (in TikZ units) because the larger
9pt legend text at the old anchor collided with the "Refused" hatch swatch — caught via a rendered
PNG check, fixed, re-verified.

## 3. Bold/italic sweep

Figure sources:

| File | textbf/textit/bfseries before | after |
|---|---|---|
| `fig-overview.tex` | 6 (5× `\textbf{...}` node headers + `\textit{...}` interchangeable-backbone aside, 2 separate `\textit` uses) | **0** |
| `fig-categorymap.tex` | 1 (`\bfseries` panel title) | **0** |
| `fig-crcbaseline.tex` | 0 | 0 (no change needed) |

Removed: bold on the G1/G2 gate-box headers and the auto-pass/defer/auto-reject outcome-box
headers (decorative node-title emphasis, not an established target-line convention); italic on
the "(PatchCore / Dinomaly — interchangeable backbone)" aside; bold on the three panel titles in
the category map. All three now render at normal weight/shape.

Main text: re-swept `\textbf`/`\emph`/`\textit` counts before vs. after in all three files.
`\textbf` counts: paper.tex 9→10, aei 9→10 (both +1: a new `\textbf{Totals}` row-header in the
expanded `tab:tier2`, matching the paper's one existing kept-bold table-summary convention,
`\textbf{Certifiable}` in `tab:floors`, already ratified in the 2026-07-16 REVIEWPASS report).
jim 9→9 (net zero: -1 from removing a decorative `\textbf{measured}` that had crept into JIM's
(JIM-only) latency table caption row — caught incidentally while porting the table edits — and +1
from the same new `Totals` header). No other decorative bold/italic was found; `\emph` counts
dropped by 2 in each file (36→34 canonical/JIM, 38→36 aei) as a side effect of restructuring two
caption sentences, not a new addition. Captions carry no bold beyond the class-emitted "Table N:"
label and no italic emphasis (checked all 7 table captions and 3 figure captions).

## 3b. Figure content audit (new directive item)

All three figures already show the full available breadth of the frozen records — no
placeholder/sparse figure was found:
- `fig-overview`: symbolic method schematic, no data plotted — not a results figure, exempt.
- `fig-crcbaseline`: plots all 3 rates (escaped/false-reject/deferral) × 2 methods (gate/CRC) × 3
  benchmarks (MPDD/VisA/MVTec AD) = 18 points, matching `tab:crcbaseline` exactly. Nothing summarized
  away.
- `fig-categorymap`: shows all 33 categories (6 MPDD + 12 VisA + 15 MVTec) × both G1/G2 axes —
  the full per-category detail the paper has. Nothing summarized away.

Directness: no ornamental frames, gradients, drop shadows, or redundant legends in any of the
three; `fig-crcbaseline`'s light `gray!15` horizontal gridlines are a legitimate cross-row reading
aid (not decorative — they help align rates across the six benchmark/method rows) and were kept.

## 4. Rails compliance

- Zero result-number changes: every number added (VisA `tab:c2` rows, per-category `tab:tier2`
  rows) was independently recomputed from the frozen JSONs and cross-checked against numbers
  already stated in the surrounding prose — exact match in all cases (see sections above).
- Backups: `paper.tex.bak-pre-tablefix2`, `jim/paper_jim.tex.bak-pre-tablefix2`,
  `aei/paper_aei.tex.bak-pre-tablefix2`, and matching `.bak-pre-tablefix2` for all three
  `figures-src/*.tex` sources — all present before any edit in this pass.
- Diff vs. backups: reviewed in full for all three `.tex` files; every changed line falls into one
  of the announced edit classes (table expand/keep, figure font/bold fixes, `\ref` updates,
  AEI-specific `\includegraphics` width / `\resizebox` additions). No unrelated content drift.
- `latexmk` exit 0 on canonical + both venue kits; zero undefined references in any of the three
  `.log` files.

## 5. Compile status and page counts

| Build | Exit | Overfull hboxes | Pages before | Pages after |
|---|---|---|---|---|
| canonical (`paper.tex`) | 0 | 1 (12.9pt, pre-existing, unrelated to this pass) | 22 | 24 |
| JIM (`jim/paper_jim.tex`) | 0 | 1 (12.9pt, pre-existing) | 23 | 24 |
| AEI (`aei/paper_aei.tex`) | 0 | 4 (2.4/38.9/32.7/30.9pt, all pre-existing) | 34 | 36 |

All pre-existing overfull hboxes were verified byte-identical (same magnitude, same paragraph
range) against a from-backup rebuild — none originate from this pass. One new large overfull
(402pt, then 105pt, then 58pt) appeared transiently while iterating on `tab:c2`'s expanded
multicolumn note and AEI's added `Benchmark` column; resolved by wrapping the note in a
`p{0.95\linewidth}` cell and wrapping AEI's `tab:c2` tabular in `\resizebox{\linewidth}{!}{...}`
(AEI-only; canonical/JIM did not need it). Final state: zero overfull hboxes attributable to this
pass in any of the three builds.

## Files changed
- `paper.tex`, `jim/paper_jim.tex`, `aei/paper_aei.tex`
- `figures-src/fig-overview.tex`, `figures-src/fig-categorymap.tex`
  (`figures-src/fig-crcbaseline.tex` audited, no change needed)
- Rebuilt: `figures-src/{fig-overview,fig-categorymap,fig-crcbaseline}.pdf`,
  `paper.pdf`, `jim/paper_jim.pdf`, `aei/paper_aei.pdf`
