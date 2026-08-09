# Review pass report — inspect-gate — 2026-07-16

Executed per `docs/records/REVIEW-DIRECTIVE-2026-07-16.md`. Applies to both
`paper.tex` (canonical, Journal of Intelligent Manufacturing target per its own
header) and `jim/paper_jim.tex` (JIM Springer venue kit), kept in lockstep.
Both files have their own `refs.bib` (identical content); both were checked
and fixed identically.

Backups made before any edit: `paper.tex.bak-pre-reviewpass`,
`jim/paper_jim.tex.bak-pre-reviewpass` (alongside the pre-existing
`.bak-pre-baseline`/`.bak-pre-mpdd`/`.bak-pre-redteam2` history).

## 1. Style / tone

| | before | after |
|---|---|---|
| `\textbf{}` occurrences | 22 (both files) | 9 (both files) |
| `\emph{}` occurrences | 56 (both files) | 38 (both files) |

13 bold instances removed: the manually-bolded title (redundant — `\maketitle`
already bolds it), and 12 mid-sentence "AI-tone" bolded verdicts/numbers
(e.g. "**G1 and G2 both certify in 12/12 categories**", "**MPDD 0/6 → MVTec AD
4/15 → VisA 12/12**", "**The constructive arm of C2 publishes...**"). Kept: the
`\todo` macro's functional red-bold (intentional, documented in the file's own
header), the three Introduction contribution-bullet lead phrases and the four
matching Limitations-list lead phrases (a standard, non-AI-tone academic
convention — bold run-in headers for itemized contributions), and one table
summary-row label ("Certifiable").

18 italic instances removed: repeat/generic-emphasis words no longer serving a
first-use definitional purpose (e.g. a second `\emph{train}`-good disambiguation,
repeat `\emph{refused}`/`\emph{refuses}`/`\emph{post-freeze}`/`\emph{realized}`
occurrences, and rhetorical emphasis on ordinary words — "decision", "visible",
"cannot", "and", "does", "all five", "certified", "escape", "order of
magnitude", "practice", "exactly"). Kept: genuine first-use term definitions
(escaped defect / false reject / auto-pass / auto-reject / defer / triage
layer / refused / negated / validity audit / naive fixed threshold / binds /
structurally ungraded) and a small number of load-bearing contrastive pairs
used once (three-way / coupled; global vs. per-category; measured-here vs.
authors'-figure in the latency table).

Prose was not otherwise restructured; no list-like fragments were identified
beyond the itemize environments already present by design (contributions,
limitations), which are conventional, not AI-tone artifacts.

## 2. Source-code leakage

`\texttt{}` instances in main-text prose (comments and the Availability
statement's dataset-identifier hashes are out of scope per the directive):
**15 → 5** (both files; identical fix set applied to both).

Naturalized (10 removed): a CLI script name (`gate.py` → "the gate module's
implementation"), an official split-file name (`1cls.csv` → "the official
one-class split file"), a torchvision architecture identifier and layer names
(`wide_resnet50_2`, `layer2,layer3` → "a Wide ResNet-50-2 backbone, features
from the second and third stages"), two CLI flags (`--good-cal train-holdout`,
`--holdout-frac 0.2` → "the flag-gated train-holdout calibration mode, 20%
holdout fraction"), and six MPDD category-folder-style identifiers with
underscores rendered in monospace (`connector`×2, `metal_plate`, `tubes`,
`bracket_black`×2 incl. one table cell pair, `bracket_brown`, `bracket_white`)
→ de-monospaced, underscores replaced with spaces, matching how the paper
already writes every MVTec category name elsewhere (toothbrush, hazelnut,
etc.).

Retained as a judgment call (5 locations, all external dataset-provenance
identifiers, not internal pipeline artifacts): two sha256 hash literals, the
official versioned VisA archive name (`VisA_20220922`) and split-protocol name
(`spot-diff`), and the HuggingFace mirror identifier (`meksamiao/mpdd`,
appearing once in Experimental Setup's data-provenance paragraph and once in
the Availability statement, the latter explicitly exempted by the directive).
These are external, verifiable, publication-standard identifiers needed for
exact reproducibility (akin to a DOI), not leaked internal script/variable
names — flagging for user sign-off rather than silently deciding either way.

`% source: ...` provenance comments were left untouched throughout (invisible
in the compiled PDF, explicitly permitted).

## 3. No appendix; compactness

No appendix existed in either file before this pass (confirmed: zero
`\appendix`/"Appendix" matches) — all results were already merged into the
main body by prior work, so there was nothing to merge. No `\clearpage` in
either file (confirmed: zero matches); floats use `[t]` placement only, no
gratuitous whitespace found.

## 4. Figures

Neither file contains any figure (`\begin{figure}`, `\includegraphics`, or
`tikzpicture`): confirmed zero matches in both. The paper is table-only. The
R/TikZ-to-PDF figure workflow (`figures-src/` + Makefile) required by the
directive therefore has nothing to build here — no figure exists to rebuild,
so no silent skip occurred; this is stated explicitly rather than assumed.

## 5. Tables and floats — column-span discipline

Both files compile under the generic `article` class (single-column) as a
documented stand-in for the real Springer `sn-jnl` class, which is not
installed locally (see the file's own front-matter note: a single fetch of the
official template zip 404'd on 2026-07-13). The one-column vs. two-column
(`table` vs. `table*`) decision is therefore a mechanical step deferred to the
`sn-jnl` drop-in at submission, not a live decision to make now; no
`\resizebox` is used anywhere (confirmed zero matches), so no float is
shrunk below readability in the meantime.

Float/reference audit: every `\ref{tab:*}`/`\ref{sec:*}` and every `\citep`
resolves (latexmk log shows zero "undefined"/"multiply defined" warnings on
either file). Six of seven tables have float source position after their
first in-text reference, in the same relative order as their first reference
(floors < v1 < c2 < tier2 < crcbaseline < latency, all consistent). One
exception, flagged rather than silently restructured: `tab:floors` is first
referenced from an Introduction contributions-bullet aside ("on our own
substrate (Table~\ref{tab:floors})") before `tab:repro` is first referenced in
the Results section, even though `tab:repro`'s float sits first in source
order (both floats still individually satisfy "placed after its own first
reference"). This is a common, intentional forward-reference / foreshadowing
pattern from an itemized contributions list; reordering the physical floats
would separate `tab:floors` from its Section 4.3 discussion by several pages
for a stylistic technicality, so it was left as-is and reported rather than
silently changed — flagging for user sign-off.

## 6. References — live verification

Delegated to a research pass with live web/DOI/arXiv checks (retrieved
2026-07-15/16). **22 of 23 bib entries verified clean** (authors, title,
venue, year, volume/pages, DOI/arXiv ID all match the live record) in both
`refs.bib` files (identical content, checked and fixed in both):
bergmann2019mvtec, roth2022patchcore, guo2025dinomaly, akcay2022anomalib,
batzner2024efficientad, vovk2005algorithmic, lei2018distribution,
bates2021rcps, angelopoulos2021ltt, angelopoulos2023gentle, clopper1934use,
holm1979simple, geifman2017selective, laxhammar2011sequential,
laxhammar2015inductive, hennhofer2026nonconform (arXiv:2605.13642 confirmed
real — May 2026, not a hallucinated future ID), shen2025conformal (confirmed
published MDPI Mathematics 13(15):2430, not just the arXiv preprint),
bai2025crcsgad, kumar2025beyond, zou2022spot, you2022unified, jezek2021mpdd.

**1 fixed**: `angelopoulos2022crc` ("Conformal Risk Control") was cited as a
bare 2022 arXiv preprint but has since been published as a spotlight paper at
ICLR 2024 (proceedings.iclr.cc/paper_files/paper/2024/hash/f3549ef9…) — updated
to `@inproceedings`, ICLR 2024, with the arXiv ID retained as a note, in both
`refs.bib` files. The bibkey itself (`angelopoulos2022crc`) was left unchanged
to avoid a blanket rename of every in-text `\citep` in both manuscripts; noting
this as a minor key/year cosmetic mismatch for awareness, not a correctness
issue (BibTeX keys are just labels).

0 entries unverifiable/fabricated.

**Separately caught and fixed**: JIM's live submission guidelines
(link.springer.com/journal/10845/submission-guidelines, retrieved 2026-07-15)
specify parenthetical author-year in-text citation (e.g. "(Thompson, 1990)"),
but both files loaded natbib with the `numbers` option, which renders numeric
`[1]`-style citations against a `plainnat` bibliography style built for
author-year — a real, compiling-but-wrong citation-style bug. Fixed in both
files: `\usepackage[numbers,round]{natbib}` → `\usepackage[round]{natbib}`.
Verified by compiling and extracting text: citations now render as
"(Bergmann et al., 2019)" as required. A stale internal comment in
`paper_jim.tex` asserting the `sn-jnl` drop-in should switch to
"`sn-basic` (Springer numbered style)" was also corrected to reflect the
live-verified author-year requirement.

## 7. Code archiving

`docs/records/CODE-ARCHIVE-POLICY-2026-07-16.md` existed by the time this pass
reached the availability statement (confirmed present, read in full). Its JIM
row states: Data Availability Statement mandatory; GitHub alone is **not**
sufficient per Springer Nature's live code policy ("providing a GitHub link
only is not sufficient as it does not assign a permanent identifier to the
code") — must pair with a Zenodo or Code Ocean DOI.

Applied in both files: the Data/Code availability text was restructured to
name GitHub explicitly as the development mirror and Zenodo explicitly as the
DOI-bearing archive (previously it said only "archived alongside the code...
will be released with a persistent DOI" without naming either platform). The
JIM kit's `Declarations` → `Code availability` paragraph was updated
identically. Both retain an explicit `\todo`/`\userfill` placeholder for the
actual GitHub URL and Zenodo DOI (pending — user credentials required to
mint), so nothing is silently presented as already archived.

## 8. Integrity rails

- Backups made before any edit: `paper.tex.bak-pre-reviewpass`,
  `jim/paper_jim.tex.bak-pre-reviewpass`.
- `latexmk -pdf -halt-on-error` exit code: **0** for both `paper.tex` and
  `jim/paper_jim.tex`.
- Zero undefined/multiply-defined references or citations in either compile
  log (grepped explicitly).
- Page count: **20 → 20** pages for both files (compiled the backups
  independently to confirm; no page-count drift from the edits).
- Diff against backups reviewed line-by-line for both files: only the
  intended edit classes landed (natbib option, title bold removal, abstract
  trim/comment, bold/italic declutter, code-leakage naturalization,
  availability-statement restructure, one bib-entry venue fix). No numeric
  result value, count, percentage, or p-value was altered anywhere in either
  diff.

## Abstract / keyword limits (live-verified)

Source: `https://link.springer.com/journal/10845/submission-guidelines`,
retrieved 2026-07-15/16 (direct fetch with browser user-agent succeeded,
HTTP 200; live page, not a stale snippet).

- Abstract: JIM requires **150–250 words**. Before this pass both files' abstracts
  were 260 words (over the limit). Trimmed to **248 words** (both files) by
  cutting parenthetical asides and connective words only — every reported
  number, count, and percentage in the abstract is unchanged.
- Keywords: JIM requires **4–6**. The JIM kit (`jim/paper_jim.tex`) had 7;
  trimmed to **6** by dropping "Selective prediction" (already covered by
  "Conformal prediction" as the methodological anchor), keeping all three
  benchmark names since they are standard reader-facing index terms for this
  literature.
- Reference style: JIM requires author-year parenthetical citation (see
  §6 above) — fixed, not merely verified, since the files previously violated
  this.
- No hard page-count/word-count limit found for the full manuscript body
  (only formatting guidance); no appendix-permission statement found beyond an
  implicit figure-numbering convention for appendices, not applicable here
  since neither file has an appendix.
- Figure format guidance (EPS/TIFF, dpi minimums, 84mm/174mm column widths)
  recorded for future reference; not applicable now since no figures exist in
  either file.
- Data/Code availability: JIM mandates a Data Availability Statement on all
  original research articles; a Code Availability Statement is expected under
  Springer Nature's company-wide code policy wherever custom code underlies
  the results — both addressed in §7 above.

## Judgment calls flagged for user sign-off (not silently resolved)

1. Five external-identifier `\texttt{}` instances (sha256 hashes, VisA archive
   version tag, spot-diff split name, HuggingFace mirror ID) kept in monospace
   as legitimate reproducibility metadata rather than naturalized — see §2.
2. `tab:floors`/`tab:repro` float-vs-first-reference ordering left as an
   intentional Introduction-level forward reference rather than restructured
   — see §5.
3. `angelopoulos2022crc` bibkey left unchanged despite the venue/year update
   (2022 preprint → 2024 ICLR) to avoid a blanket citation-key rename across
   both manuscripts — see §6.
