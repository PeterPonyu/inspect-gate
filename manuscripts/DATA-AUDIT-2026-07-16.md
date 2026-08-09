# Inspect-gate manuscript audit — 2026-07-16

Scope: `manuscripts/paper.tex` (1120 lines) and `manuscripts/jim/paper_jim.tex` (1187 lines,
the JIM/Springer submission port), including the new CRC-baseline section
(`sec:crcbaseline`, Table `tab:crcbaseline`, Figure `fig:crcbaseline`) and the category-map
figure (Figure `fig:categorymap`). Every path-cited number was traced to its source JSON;
every `figures-src/data/*.csv` row was recomputed from the underlying `gate_calibration/v1_*.json`
/ `baseline_comparison_2026-07-15/results.json` files and diffed programmatically (not just
eyeballed).

Coverage: 100% of paper.tex read end to end; jim/paper_jim.tex diffed line-by-line against
paper.tex (front matter / Declarations / phrasing differ, body content is byte-identical —
confirmed no divergent numbers survived the port); all 4 CSVs in `figures-src/data/`
recomputed from source JSON and compared programmatically (0 mismatches across 33
category rows + the CRC-baseline pooled table); both `figures-src/fig-*.tex` TikZ sources
checked for hardcoded numbers against the CSVs; ~40 distinct headline/table numbers traced to
`analysis_2026-07-10/`, `visa_results_2026-07-12/`, `mpdd_results_2026-07-13/`,
`g2_promotion_2026-07-12/`, `c2_tier2_2026-07-13/`, `b3_patchcore_2026-07-13/`,
`baseline_comparison_2026-07-15/`, and `binding_demo_2026-07-13/`.

## Severity counts

- CRITICAL: 1
- MINOR: 2

## Findings

### CRITICAL-1 — Certifiability-floor range "$0.09$–$0.14$" is internally inconsistent with Table 2's own data

**Location:** `paper.tex:129-130` (Introduction, second contribution bullet) and identically
`jim/paper_jim.tex:165-166` (same sentence, ported verbatim).

> "...a non-refusing baseline that issues an auto-reject threshold and claims the requested
> false-reject rate $\alpha_{\text{fr}}=0.05$ in the $11$ categories the gate refuses would be
> asserting a guarantee the calibration pool cannot support --- the achievable floor there is
> $0.09$--$0.14$ (e.g.\ toothbrush $1/7=0.14$), two- to three-fold looser than claimed..."

The paper's own floor formula is $\alpha_{\min} = 1/(n_{\text{cal}}+1)$ (Section 3.2,
`paper.tex:255`), and Table 2 (`tab:floors`, `paper.tex:449-472`) lists $n_{\text{cal}}^{\text{good}}$
for every category. Applying the stated formula to the $n_{\text{cal}}^{\text{good}}$ values of
the 11 REFUSE-marked categories in that same table gives:

| category | $n_{\text{cal}}^{\text{good}}$ | $\alpha_{\min}=1/(n+1)$ |
|---|---|---|
| leather | 16 | **0.0588** |
| tile | 16 | **0.0588** |
| zipper | 16 | **0.0588** |
| carpet | 14 | 0.0667 |
| pill | 13 | 0.0714 |
| capsule | 12 | 0.0769 |
| metal_nut | 11 | 0.0833 |
| bottle | 10 | 0.0909 |
| grid | 10 | 0.0909 |
| wood | 10 | 0.0909 |
| toothbrush | 6 | 0.1429 |

The true range across the 11 refused categories is **$[0.0588, 0.1429]$**, not $[0.09, 0.14]$ as
stated — three categories (leather, tile, zipper, all $n^{\text{good}}=16$) sit at $1/17\approx0.059$,
well below the claimed $0.09$ lower bound, and carpet ($1/15\approx0.067$) and pill
($1/14\approx0.071$) are also below it. Only bottle/grid/wood (at exactly $1/11=0.0909$) support
the stated lower bound.

This also undermines the immediately-following "two- to three-fold looser than claimed" claim
relative to $\alpha_{\text{fr}}=0.05$: $0.0588/0.05 = 1.18\times$, not "two-fold" — so the actual
spread is closer to $1.2\times$–$2.9\times$, not "two- to three-fold." The toothbrush example
itself ($1/7=0.14\to2.9\times$) is correct in isolation; the range statement wrapped around it is not.

**Minimal fix:** replace "$0.09$–$0.14$ ... two- to three-fold looser than claimed" with the
correct range, e.g. "$0.06$–$0.14$ ($1.2\times$–$2.9\times$ looser than claimed)", in both
`paper.tex` and `jim/paper_jim.tex` (identical sentence in both files, so both need the fix).

---

### MINOR-1 — Unsupported behavioral/causal claim about operator behavior

**Location:** `paper.tex:86` and identically `jim/paper_jim.tex:122`.

> "...rejecting a good part (a *false reject*) wastes yield and, at high rates, erodes trust in
> the system until operators disable it."

This is a specific causal/behavioral assertion (that high false-reject rates cause operators to
disable the system) presented as established fact, with no citation and no supporting data from
this paper's own experiments (which measure certified rates and deferral, not operator behavior
or system-disablement events). It reads as plausible domain motivation, but as written it asserts
more than the paper — or any cited source — establishes.

**Suggested rewording:** soften to a hedged motivating claim, e.g. "...wastes yield and, at high
rates, is widely reported to erode operator trust in automated inspection" (with a citation, if one
exists), or "...wastes yield and, at high rates, risks eroding operator trust in the system,"
removing the unqualified "until operators disable it" causal chain.

### MINOR-2 — "Industrial-realism" framing for MPDD precedes the academic-data caveat by ~900 lines

**Location:** e.g. `paper.tex:100-106` (Introduction), `paper.tex:174-176` (Related work),
`paper.tex:488-499` (§4.4 heading "MPDD: the stingy extreme..."), abstract line 63
("MPDD (painted-metal parts)"), vs. the caveat at `paper.tex:1051-1055` (Limitations, §7):
"all three benchmarks are academic: no production-line, temporal-drift, or real-factory data
backs the industrial framing here ... the paper's claims are about certified triage on the
standard inspection benchmarks, not about a deployed line." Identical text in
`jim/paper_jim.tex:1088-1092` — confirmed **not** softened or dropped in the JIM port (the
specific risk flagged in the audit brief).

This is not a factual error — MPDD genuinely is built from photographs of real painted-metal
parts, and the Limitations section does correctly and plainly disclose that no production-line
or deployment data was used anywhere. But the paper repeatedly calls MPDD a "deliberately harsher
industrial-realism stress test," "real painted-metal-part categories," and "the stingiest
certifiability point" across the abstract, introduction, related work, and results sections
before that framing is qualified, ~900 lines later, as still purely an academic benchmark. A
reader stopping before §7 could come away thinking the industrial-deployment claims are stronger
than the paper actually supports. Recommend a one-clause pointer at first use (e.g. in the
abstract or intro, "MPDD... an academic benchmark of real parts, not production-line data — see
Limitations") rather than relying on the Limitations section alone to carry the caveat.

## What checked out clean (no issues found)

- **Table `tab:crcbaseline` (CRC baseline)**: all 18 cells (3 benchmarks × 2 methods × 3 metrics,
  plus G1/G2 cert counts) traced exactly to `baseline_comparison_2026-07-15/results.json`
  (`our_gate_published` / `crc_baseline`, pooled). The headline MPDD contrast — our gate 0.0%
  vs. CRC 36.9% false-reject at matched 6.6% escaped-defect — is exact
  (`mean_false_reject_rate: 0.3685229700854701` → 36.9%; `0.0` → 0.0%).
- **`figures-src/data/crcbaseline.csv`** and **`fig-crcbaseline.tex`**: the 18 hardcoded plot
  coordinates match the CSV/JSON exactly (36.85, 6.63, 73.09, etc.).
- **`figures-src/data/categorymap_{mvtec,visa,mpdd}.csv`**: recomputed pooled means (2 backbones
  × 5 seeds) from `gate_calibration/v1_*_seed*.json` per category for all 33 categories across
  the three benchmarks — 0 mismatches against the CSVs' `g1_cert`/`g2_cert`/rate columns.
  `fig-categorymap.tex` reads these CSVs via generated macros with no hardcoded numbers.
- **Table `tab:floors`** (per-category $n_{\text{cal}}$/certifiability): exact match against
  `certifiability_floors` in the frozen `v1_patchcore_seed0.json`.
- **Table `tab:repro`** (reproduction gate): mean-AUROC ranges and weakest-category ranges for
  both backbones on all three benchmarks recomputed from `SUMMARY.json`/`MVTEC-VS-VISA.json` —
  exact match, including the correct identification of Dinomaly's weakest MVTec category as
  capsule (not toothbrush, which is PatchCore's weakest).
- **Table `tab:c2`** (confirmatory excess-AURC audit) and the post-hoc B3 completion: per-seed
  excess-AURC ranges for all 4 (backbone × practice) cells recomputed from
  `c2_tier2_2026-07-13/c2_mvtec.json`; B3 range from `b3_patchcore_2026-07-13/results.json`.
  Both match the stated ranges and Holm $p$-values ($5\times10^{-4}$ per test,
  $2\times10^{-3}$/$2.5\times10^{-3}$ Holm-adjusted) exactly.
- **Exploratory excess-AURC counts** (§`sec:auditres`): seed-0 single-category rejection/degenerate
  counts (MVTec PatchCore 10/30 rejects, 6/30 degenerate; Dinomaly 0/30, 14/30 degenerate; VisA
  PatchCore 14/24, 0 degenerate; Dinomaly 16/24, 0 degenerate) and the all-seed totals (MVTec
  PatchCore 48/150, Dinomaly 4/150; VisA PatchCore 64/120, Dinomaly 42/120) all recomputed exactly
  from `analysis_2026-07-10/audit/` and `visa_results_2026-07-12/audit/` + `MVTEC-VS-VISA.json`.
- **Binding demonstration** (§`sec:binding`): the "27 cells" total and its 3/3/4/17 breakdown match
  `binding_demo_2026-07-13/results.json`'s `certified_stable_binding` arrays exactly (note: the
  JSON's separate `counts` field, 3/14/4/19=40, is a looser seed-0-only definition that the paper
  correctly does *not* use — it explicitly restricts to the cross-seed-stable subset, which is the
  27-cell set). The specific screw/capsules numeric examples (24.2% vs 8.0%/4% deferral;
  19.5% vs 5.0%/14% deferral; 96.8% vs 3.7%) all match to the JSON's precision, with one very
  minor rounding looseness: the gate's screw deferral is 3.6% (`0.03625`) but the prose rounds
  it to "just 4%" — not wrong, just a looser round than the rest of the paper's convention.
- **G2 train-holdout promotion** (§`sec:g2promo`): `G2-PROMOTION-RESULT.json` confirms 13/15
  certified in seeds 0–3, 12/15 in seed 4, with leather KS-failing in all 5 seeds and screw
  additionally failing only in seed 4 — exact match.
- **MPDD train-holdout rescue** (§`sec:mpddholdout`): `HOLDOUT-RESULTS.json` confirms 4/6
  certified in all 5 seeds, tubes KS $p_{BH}=1.245\times10^{-5}$, metal_plate $n=11<19$,
  connector $n_{\text{cal}}^{\text{def}}=7$ (matching the "$7<9$" claim), min Spearman
  $\rho=0.9186$, max $|\Delta\text{AUROC}|=0.0399$ — all exact.
- **Selective-prediction reference curve** (end of §`sec:crcbaseline`): AURC extremes
  (0.0019 MVTec/Dinomaly, 0.0849 VisA/PatchCore) and all six coverage=0.8 risk values match
  `baseline_comparison_2026-07-15/results.json`'s `selective_baseline` blocks exactly.
- **Abstract vs. body vs. conclusion**: the recurring headline sequence "$0/6 \to 4/15 \to 12/12$"
  (MPDD $\to$ MVTec AD $\to$ VisA, in that specific order across three different benchmarks with
  three different category counts) is used consistently in the abstract, §4.4, Limitations, and
  Conclusion — same order, same numbers, every time. "$12$–$13/15$" (G2 promotion range) is also
  consistent everywhere it's repeated (abstract, §4.5, Conclusion).
- **jim/paper_jim.tex vs. paper.tex**: diffed the full files. All differences are structural
  (Springer front matter, Declarations section, `\todo` neutralization, relative figure paths,
  minor prose rewording for a "manufacturing reader") — no numeric value differs between the two
  files anywhere in the body text, including the CRC-baseline table/figure and every table checked
  above. The CRITICAL-1 and MINOR-1/2 findings above are present identically in both files (i.e.
  the port did not introduce or fix any inconsistency; it faithfully copied the one that already
  existed in `paper.tex`).

## Not independently re-verified (out of practical scope for this pass)

- The underlying `inspect_gate` gate/certify/baselines Python implementation was not re-derived
  from first principles (e.g., re-running the split-conformal math by hand) — only the reported
  JSON outputs were cross-checked against the manuscript's transcribed numbers.
- `refs.bib` citation-key correctness (e.g., whether `angelopoulos2022crc` / `angelopoulos2023gentle`
  actually resolve to the papers described) was not checked; this audit focused on numeric/data
  consistency and assumption-based claims, not bibliography accuracy.
