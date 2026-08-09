# inspect-gate — Journal of Intelligent Manufacturing (JIM) submission port

This directory is the JIM/Springer submission package for the inspect-gate paper. It is a
**packaging port** of the source of truth `../paper.tex` (fixed and review-verified 2026-07-13):
every content claim, number, and provenance path is carried over byte-faithfully. Only the
front-matter structure, abstract length, and declarations were adapted to Springer/JIM
requirements, and the red `\todo{}` render blocks were removed (see below).

## Files

| File | Purpose |
|---|---|
| `paper_jim.tex` | Full manuscript port, article class structured to Springer/JIM requirements. |
| `refs.bib` | Bibliography, copied verbatim from `../refs.bib`. |
| `cover_letter.md` | Cover letter to the JIM editors. |
| `README.md` | This checklist. |

## Compile

```sh
latexmk -pdf paper_jim.tex      # produces paper_jim.pdf (15 pp)
# clean:  latexmk -C paper_jim.tex
```

Verified: compiles with zero errors under TeX Live `article` class + `natbib` (plainnat), no
undefined citations or references.

## Template drop-in step (REQUIRED at submission)

The official Springer Nature class **`sn-jnl.cls` is not installed** in the build environment, and a
single fetch attempt of the official template
(`https://static.springer.com/sn-article-template/sn-article-template.zip`, 2026-07-13) returned a
404 HTML page rather than a zip. The port therefore compiles in the standard `article` class. The
sn-jnl drop-in is a **mechanical submission-day step** — no content changes are needed, only markup
swaps:

1. Download the current Springer Nature LaTeX template (`sn-article-template.zip`) from the JIM
   author instructions / "Submission guidelines → LaTeX" page and install `sn-jnl.cls`.
2. Change `\documentclass[11pt]{article}` → `\documentclass[sn-basic]{sn-jnl}` (or
   `[pdflatex,sn-basic]{sn-jnl}`).
3. Move the title/author front matter into the sn-jnl `\title{}` / `\author{}` / `\affil{}` /
   `\email{}` macros (the current `\author{...\thanks{...}}` block is a placeholder).
4. Replace the `\paragraph{Keywords.}` line with the sn-jnl `\keywords{...}` macro.
5. Switch `\bibliographystyle{plainnat}` → `\bibliographystyle{sn-basic}` (Springer numbered style).
   The current plainnat numbered style is an acceptable pre-template stand-in.
6. Move the `Declarations` block under the sn-jnl declarations convention (`\bmhead{Declarations}`
   with the required sub-headings — all six are already present as `\paragraph{}` items).

## TODO-USER items (author completes before submission)

All render as visible italic `[TODO-USER: ...]` in the PDF (never red). Search the `.tex` for
`\userfill`:

- **Author block** — full author list, affiliations, ORCID iD(s), corresponding-author email/postal
  address (title `\thanks`).
- **Funding** — funding sources, or the standard "no funds received" statement.
- **Competing interests** — declaration, or the standard "no relevant interests" statement.
- **Data availability** — mint and insert the **Zenodo DOI** for the frozen score dumps + analysis
  archive (deposit under the author's credentials).
- **Code availability** — public repository URL and open-source license.
- **Author contributions** — CRediT-style statement matching the final author list.
- **Cover letter** — author name(s), affiliation, corresponding-author contact.

## How the red `\todo{}` blocks were resolved

`../paper.tex` uses a red `\todo{}` macro to flag preregistered-but-uncomputed arms. A submission
port must render **no** red TODO blocks, but must **not** delete the underlying disclosures. Each was
converted to honest reviewer-facing prose inside **Section: Limitations and gated arms**, and the
`\todo` macro is neutralised (`\newcommand{\todo}[1]{#1}`) as a safety net. The Limitations narrative
still states, item by item, exactly what remains uncomputed:

| paper.tex `\todo` | Resolution in paper_jim.tex |
|---|---|
| C2 confirmatory pooled audit | **Now computed** (no longer a gap): Results subsection *Confirmatory audit verdict (C2)* + Table (`\label{tab:c2}`). MVTec constructive verdict, four-member per-seed Holm rejects in all 5 seeds (Holm p = 0.002, excess-AURC [0.023, 0.050], CIs exclude 0); seed dimension reported as a robustness check (prereg silent on seeds), cross-seed rollup post-freeze but moot. VisA reported separately as exploratory ([0.044, 0.106]). Source: `c2_tier2_2026-07-13/c2_{mvtec,visa}.json`. |
| B3 (train-good quantile) practice | **Now completed post-hoc for PatchCore** (2026-07-13): a held-out train-good pool exists for PatchCore, so B3 is reported post-hoc in the C2 subsection — constructive in all 5 seeds (excess-AURC [0.053, 0.056], perm p = 0.0005, CIs exclude 0). B3-Dinomaly impossible (no train-side dump), so the full 6-member family cannot run; VisA has no train-good scores. Source: `b3_patchcore_2026-07-13/results.json`. |
| Binding demonstration ("when a fixed threshold over-promises") | **New post-hoc subsection** (`\label{sec:binding}`): 27 certified, cross-seed-stable (backbone, category) cells where a naive fixed threshold's realized escaped/false-reject rate exceeds target while the certified gate holds within it; the cleanest cases pay low deferral (e.g. MVTec Dinomaly-screw escaped 24.2% → 8.0% at 4% deferral). Exploratory label. Source: `binding_demo_2026-07-13/results.json`. |
| V1 tier-2 as a verdict | **Now graded** (no longer a gap): Results subsection *V1 tier-2 verdict* + Table (`\label{tab:tier2}`). MVTec escaped 15 pass / 115 fail / 20 underpowered (A2-expected variance, tier-1 passes 150/150); false-reject structurally ungraded (0/150; A1+A3). VisA partially gradeable. Source: `c2_tier2_2026-07-13/tier2_{mvtec,visa}.json`. |
| K6 (scoop re-scan) | **Now executed** (2026-07-13): fresh pre-submission citation re-scan returned a clear verdict — no scoop; pre-decided pivot not triggered. K6 is a novelty gate (not statistical), so running it after the 2026-07-11 freeze is the intended sequencing. Source: `analysis_2026-07-10/K6-RESCAN-2026-07-13.md`. |
| K4 (audit headroom) | Prose: K4 needs an unimplemented oracle-headroom statistic (still gated). |
| Tables/figures for the above | Confirmatory audit table + tier-2 table **now included**; prose: defect-type Mondrian map and train-holdout G2 delta figure remain to be produced. |
| Latency/practicality table | **Now computed** (no longer a gap): real Results subsection *Latency and deployment cost* + Table (`\label{tab:latency}`). Measured on this hardware: gate routing 2.8 us/image and calibration 2.4 ms (CPU, Intel Core Ultra 9 275HX); Dinomaly backbone 18.9 ms/image (RTX 5090 Laptop GPU). PatchCore row attributed to Roth et al. 2022 (published, not measured). Source: `latency_2026-07-13/{gate,dinomaly}_latency.json`. |
| Zenodo DOI (data availability) | Moved to the **Data availability** declaration as a `[TODO-USER]` placeholder. |

## Content-sync provenance

- Ported from `../paper.tex` state of **2026-07-13** (source of truth), including the 2026-07-13
  red-team fix cycle (B3-PatchCore post-hoc, binding demonstration, K6 re-scan executed, seed
  robustness relabel, latency substrate-mix caveat).
- Abstract is **194 words** (recount 2026-07-13, each math token counted as one word; verbatim to
  `../paper.tex`), well under JIM's ≤250-word limit. Every claim direction preserved; no new claims.
- Keywords (6): industrial visual inspection; conformal prediction; anomaly detection; selective
  prediction; MVTec AD; VisA.
- If `../paper.tex` changes (e.g. a gated arm is computed), re-sync the corresponding body text and
  the Limitations item here before submitting.
