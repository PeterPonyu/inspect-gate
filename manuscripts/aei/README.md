# inspect-gate — Advanced Engineering Informatics (AEI) submission port

This directory is the *Advanced Engineering Informatics* (Elsevier) submission package for the
inspect-gate paper. It is a **venue port** of the source of truth `../paper.tex`: every result
number, claim, and provenance path is carried over unchanged. The only content change relative to
the canonical is a **reference expansion** woven into Related Work / Discussion (AEI norms run
materially longer than the canonical's baseline list); the front-matter structure, citation style,
and declarations were adapted to Elsevier/AEI requirements, and the red `\todo{}` render blocks were
neutralised.

The canonical `../paper.tex` remains the source of truth; the `../jim/` package (Springer JIM) is
untouched and retained as a fallback venue.

## Files

| File | Purpose |
|---|---|
| `paper_aei.tex` | Full manuscript port, `elsarticle` class, AEI/Elsevier front matter. |
| `refs.bib` | Bibliography (42 entries): canonical 23 + 19 live-verified additions. Identical superset shared with `../refs.bib` and `../jim/refs.bib`. |
| `highlights.txt` | Standalone Highlights artifact (5 bullets, each ≤ 85 chars) for the Elsevier portal upload. Also rendered in the PDF. |
| `cover_letter.md` | Cover letter to the AEI editors (engineering-informatics deployment framing). |
| `README.md` | This checklist. |

## Compile

```sh
latexmk -pdf paper_aei.tex      # produces paper_aei.pdf
# clean:  latexmk -C paper_aei.tex
```

Verified 2026-07-16: compiles with **exit 0**, zero undefined citations/references, under TeX Live
`elsarticle` + `elsarticle-num` (numbered, AEI's live reference style). Figures are pulled from
`../figures-src/` (shared with the canonical; this port does not duplicate them). Page count:
**34 pp** in the single-column `preprint` layout (the initial-submission format; AEI sets no hard
page limit at submission under Elsevier "Your Paper Your Way", and the typeset two-column version is
substantially shorter).

## GATE-0: AEI / Elsevier mandatory-submission checklist

Verified live against the AEI guide-for-authors and Elsevier author resources on 2026-07-16
(ScienceDirect guide-for-authors returned HTTP 403 to automated fetch; requirements corroborated via
the Elsevier Highlights spec, the Elsevier declarations tool, and cross-referenced guide snippets).

| Requirement | AEI/Elsevier rule (live) | Status in this kit |
|---|---|---|
| Document class | `elsarticle` (Elsevier LaTeX class) | **Met** — `\documentclass[preprint,11pt]{elsarticle}`. |
| Reference style | `elsarticle-num` (numbered) | **Met** — `\bibliographystyle{elsarticle-num}`. |
| Abstract | ≤ 250 words | **Met** — 248–249 words (math tokens as one word), verbatim to canonical. |
| Keywords | 1–7 | **Met** — 6 keywords in the `keyword` environment. |
| Highlights | 3–5 bullets, ≤ 85 chars each incl. spaces; optional at submission, **required at final-files stage** | **Met** — 5 bullets (73–77 chars) in `highlights.txt` and rendered in the PDF. |
| Declaration of competing interest | Mandatory statement (via the Elsevier declarations tool) | **Draft present** — standard "no competing interests" statement; **TODO-USER** to confirm/amend and submit via declarations.elsevier.com. |
| Data availability statement | Mandatory | **Draft present** — **TODO-USER** to insert the Zenodo DOI + GitHub URL. |
| CRediT author statement | Required | **Draft present** — **TODO-USER** to fill matching the final author list. |
| Funding declaration | Required (state "none" if none) | **Draft present** — **TODO-USER**. |

## TODO-USER items (author completes before submission)

All render as visible italic `[TODO-USER: ...]` in the PDF (never red), except the front-matter
author fields, which use plain `[TODO-USER: ...]` text (elsarticle's `\ead`/`\affiliation` macros
reject the italic placeholder macro). Search the `.tex` for `TODO-USER`:

- **Author block (front matter)** — full author list, affiliation(s), corresponding-author email
  and postal address (`\author`/`\ead`/`\affiliation` macros), ORCID iD(s).
- **Declaration of competing interest** — confirm or amend the standard statement, and complete the
  Elsevier declarations tool at submission.
- **Funding** — funding sources, or the standard "no specific grant" statement.
- **CRediT authorship contribution statement** — a CRediT statement matching the final author list.
- **Data availability** — mint and insert the **Zenodo DOI** for the frozen score dumps + analysis
  archive, and the public **GitHub** URL.
- **Cover letter** — author name(s), affiliation, corresponding-author contact.

## Content-sync provenance

- Ported from `../paper.tex` (source of truth; preregistration frozen 2026-07-11), carrying the
  three-benchmark state (MVTec AD + VisA + MPDD), the CRC single-threshold baseline table, and the
  latency table.
- **Reference expansion (2026-07-16):** 19 references added, every one DOI- or arXiv-resolved live
  against Crossref / the arXiv API — no fabricated identifiers. The AEI in-venue industrial
  visual-inspection cluster is represented: Liu et al. 2023 (component-aware inspection,
  10.1016/j.aei.2023.102161), Shang et al. 2023 (defect-aware transformer, 10.1016/j.aei.2023.101882),
  and Tsai & Jen 2021 (autoencoder surface inspection, 10.1016/j.aei.2021.101272). The rest span the
  anomaly-detection method landscape (PaDiM, SPADE, uninformed students, reverse distillation, DRÆM,
  CutPaste, FastFlow, SimpleNet), manufacturing/inspection deployment and surveys (Tabernik et al.,
  Liu et al. survey, Czimmermann et al.), and the conformal / selective-prediction line (inductive
  conformal, least-ambiguous set-valued classifiers, adaptive coverage, covariate-shift conformal,
  SelectiveNet). All are woven substantively into Related Work / Discussion, not appended.
- The three `refs.bib` copies (canonical, jim, aei) are kept **byte-identical supersets**; the 19
  additions are cited only in this AEI port, so the canonical and jim compiled PDFs are unchanged
  (their `.bbl` files still carry exactly the 23 cited entries).
- If `../paper.tex` changes (e.g. a gated arm is computed), re-sync the corresponding body text here
  before submitting.
