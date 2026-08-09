# MPDD manuscript hooks + 3-benchmark comparison skeleton (JIM)

**Date:** 2026-07-13. **Author:** t1-inspect (Tier-1 local). **Status:** pre-box draft —
certifiability columns are pre-filled (count-only, final); AUROC/audit/deferral columns are
`TBD(box)` fill-ins. MPDD is **post-freeze exploratory** (identical status to VisA; no re-freeze,
never in the confirmatory Holm family). Do NOT edit manuscripts until box scores land — this is
the fill-in map so integration is mechanical.

---

## 3-benchmark comparison table skeleton (extends `visa_results_2026-07-12/MVTEC-VS-VISA.md`)

Same protocol on all three: 5 seeds, R=20 stratified repeats, α_miss=0.10, α_fr=0.05, primary
(--good-cal test), exploratory audit fixed+tuned, n_perm=2000, per-cell Holm.

| Benchmark | Backbone | mean I-AUROC (5 seeds) | repro target | repro pass | G1 cert. | G2 cert. (primary) | V1 tier-1 cells | K1+K2 seed trips | audit Holm rejects | median deferral |
|---|---|---|---|---|---|---|---|---|---|---|
| MVTec-AD | patchcore | 0.9820 ± 0.0004 | 0.991 | 5/5 | 15/15 | 4/15 | 75/75 | 0+0 | 48/150 | 0.707 |
| MVTec-AD | dinomaly | 0.9960 ± 0.0003 | 0.996 | 5/5 | 15/15 | 4/15 | 75/75 | 0+0 | 4/150 | 0.694 |
| VisA | patchcore | 0.9054 ± 0.0018 | n/a* | n/a* | 12/12 | 12/12 | 60/60 | 0+0 | 64/120 | 0.194 |
| VisA | dinomaly | 0.9870 ± 0.0004 | 0.987 | 5/5 | 12/12 | 12/12 | 60/60 | 0+0 | 42/120 | 0.040 |
| **MPDD** | **patchcore** | `TBD(box)` | n/a* | n/a* | **5/6** | **0/6** | `TBD` /30 | `TBD` | `TBD` /30 | `TBD` |
| **MPDD** | **dinomaly** | `TBD(box)` | **0.972** | `TBD(box)` | **5/6** | **0/6** | `TBD` /30 | `TBD` | `TBD` /30 | `TBD` |

\* PatchCore has no repo-confirmed published image-AUROC on VisA or MPDD → descriptive row
(target n/a), per the no-guessed-target rule.

- **V1 tier-1 cells** denominator for MPDD = 6 categories × 5 seeds = **30** per backbone.
- **K1+K2 seed trips**: kill-gate thresholds SCALE to 6 categories (K1 max_violations=2,
  K2 min_categories=4; design ratios 5/15 and 8/15 → ceil at n=6). Disclosed in
  `run_mpdd_analysis.py` docstring; raw counts recorded so any threshold is re-derivable.
- **G1 5/6 / G2 0/6 are FINAL** (count-only floors; see `FLOOR-PREDICTION.md`).

### Certifiability trend row (the honesty-figure headline — corrected)

| Benchmark | test-good pool (per cat) | G2-certifiable (primary) |
|---|---|---|
| **MPDD** | small, uniform 26–32 | **0/6** |
| MVTec-AD | mixed | 4/15 |
| VisA | large 50–100 | 12/12 |

Monotone in test-good pool size: **MPDD 0/6 → MVTec 4/15 → VisA 12/12**. MPDD is the *stingy*
extreme, NOT the intermediate point the plan hypothesised. Optional train-holdout arm (free,
same scores): MPDD G2 floor clears for 5/6 (KS-gated) — the 0/6→up-to-5/6 contrast is the
strongest single demonstration of the calibration-efficiency lever.

---

## Manuscript hook list (file: `manuscripts/jim/paper_jim.tex`)

Each is a small fill-in; line numbers are as of 2026-07-13 (verify before editing).

| # | Location (approx line) | Current | Change |
|---|---|---|---|
| H1 | title, L54 | "…on MVTec AD and VisA" | "…on MVTec AD, VisA, and MPDD" |
| H2 | abstract, L71–88 | "two complementary benchmarks"; per-benchmark result sentences | "three…"; add one MPDD sentence: metal-parts realism; G1 5/6, G2 **0/6 at primary** (stingy extreme — small test-good pools), reproduction-gated Dinomaly vs published 0.972 |
| H3 | teaser list, L93 | "MVTec AD · VisA" | "MVTec AD · VisA · MPDD" |
| H4 | intro, L124–125 | "two complementary benchmarks by design: MVTec AD… and VisA" | "three…: … and MPDD (real painted-metal-parts fabrication, uniformly small good pools → the stingiest certifiability point)" |
| H5 | §Setup Data, L314 | "Two public benchmarks." | "Three public benchmarks." + MPDD paragraph: 6 metal-part categories, 888 train-good / 458 test (176 normal + 282 defect), native MVTec layout, source + sha256 (see DATA_MANIFEST) |
| H6 | exploratory-status note, L168 | "second benchmark (VisA — not part of the frozen preregistration)" | add MPDD as a *third* post-freeze-exploratory benchmark, identical discipline; never in the confirmatory Holm family |
| H7 | Related Work industrial AD, L186–217 | MVTec + VisA framing | add one sentence citing MPDD (Jezek et al., ICUMT 2021) as the metal-parts realism benchmark |
| H8 | Results (new short ¶, near §repro/§certify) | — | MPDD results paragraph: reproduction (Dinomaly vs 0.972; PatchCore descriptive) + floors (G1 5/6, G2 0/6 primary; train-holdout 5/6 floor KS-gated) + V1 + audit headroom |
| H9 | `MVTEC-VS-VISA.md` → rename/extend | 2-benchmark table | 3-benchmark table (skeleton above); update "Reading" bullets with the corrected MPDD-stingy trend |
| H10 | Limitations | — | one sentence: MPDD is post-freeze exploratory (identical to VisA); its 0/6 primary G2 is the honest data-limited behaviour, not gate conservatism |

**Narrative correction to carry everywhere:** every place the plan drafted "MPDD is the
intermediate point on the certifiability spectrum" must instead say "MPDD is the stingy extreme
(0/6), with MVTec (4/15) and VisA (12/12) above it — the trend is monotone in good-pool size."
This is a stronger honesty story, not a weaker one, but it is the OPPOSITE ordering, so the
wording cannot be copied from the plan verbatim.
