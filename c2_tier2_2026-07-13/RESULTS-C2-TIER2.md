# C2 pooled audit + V1 tier-2 grading — results (2026-07-13)

Compute-only run on cached scores (CPU). No manuscript edited. Scripts and result
JSONs live beside this file. MVTec AD (in-prereg, confirmatory) and VisA (post-freeze,
exploratory) are kept in **separate pooled families and never pooled across benchmarks.**

---

## HEADLINE VERDICTS

1. **C2 pooled audit = CONSTRUCTIVE arm, decisively, and it is WITH the paper's current
   framing** (not against it). Standard threshold practice (B1 fixed, B2 tuned) *does* carry
   deferral skill beyond honest random deferral. Every confirmatory test rejects the
   random-deferral null at the permutation floor **p = 0.0005 = 1/(2000+1)**, Holm-adjusted
   **p = 0.002 < 0.05**, in **all 5 seeds**, both backbones, on **both** benchmarks; every
   excess-AURC bootstrap CI excludes zero. This fills the manuscript's explicit open hole
   (paper.tex: "the confirmatory pooled audit verdict (C2) remains the one [outstanding]").

2. **V1 tier-2 false-reject axis is structurally ungraded on MVTec** — exactly as amendments
   A1+A3 predict. 0 of 150 cells graded: 110 G2-REFUSED (A3), 40 per-repeat-underpowered (A1).

3. **V1 tier-2 escaped axis fails in most powered MVTec cells (115/130), and this is the
   PREREGISTERED-EXPECTED outcome, not a certificate failure.** A2 pins tier-2 as a stringent
   variance check a correctly-calibrated gate is expected to fail near the target. The
   certificate-validity test is **tier-1, which passes 150/150 on MVTec.**

Nothing in these results contradicts the paper's framing; both analyses fill `\todo` holes
already scaffolded in paper.tex (lines 604–626) with the outcome the manuscript anticipated.

---

## PART 1 — C2 pooled audit

### Frozen vs authored determination

| Component | Status | Basis |
|---|---|---|
| Per-(practice,backbone) pooled-category audit construction (excess-AURC vs analytic random null; matched-abstention permutation p, n_perm=2000, strata=category; category-blocked bootstrap CI; B1 on pooled cal, B2 per-category) | **FROZEN** | PREREG §7 step 7, §5 D5; design 01-APP §3.5 |
| Confirmatory family = {fixed, tuned} × {patchcore, dinomaly} = **4** (B3/quantile skipped — no held-out train-good pool; the canonical dumps carry test scores only) | **FROZEN** | PREREG §4 preregisters the 3→2 practice degradation explicitly ("6 → 4"), removing post-hoc freedom |
| Holm α = 0.05 across the family | **FROZEN** | PREREG §7 step 7 |
| Split: audit uses the repeat-0 50/50 stratified cal/eval split | **AUTHORED (minor)** | Mirrors the shipped Stage-4 exploratory audit's own choice — the only frozen precedent. Not independently pinned in prereg text. |
| **Cross-seed reduction** (5 backbone seeds → 1 verdict per practice×backbone) | **AUTHORED post-freeze, one-shot** | The frozen family names **no seed dimension**; Stage D of run_main_grid.sh that would combine seeds is an unfilled TODO. |

**Authored cross-seed rule (stated once, no tuning, per-cell results already known when
authored):** the confirmatory p-value per (practice, backbone) is the **seed-max** (least
significant seed) of the 5 per-seed pooled permutation p-values — a rejection must survive in
the worst seed. Rationale: the design treats the 5 backbone seeds as a robustness dimension
(§3.3), not a family dimension, and the paper's own A1/D8 stance forbids pooling correlated
resamples (the 5 seeds share the test images), so pooling seed-records is barred; seed-max is
the simplest conservative "present in every seed" reduction. seed-min and seed-median are also
computed for transparency.

### The verdict does not depend on the authored piece at all

Because **every** (practice, backbone, seed) cell already hits the permutation floor
p = 0.0005 with a strictly positive excess-AURC whose CI excludes zero, the seed reduction is
**moot**: seed-max, seed-min, and seed-median all give reduced p = 0.0005 and unanimous
rejection. The **per-seed frozen 4-member Holm verdict is confirmatory-grade on its own terms
and rejects in all 5 seeds** (p_holm = 0.002 each). The single-number cross-seed rollup is
authored but changes nothing.

### Numbers

| Benchmark | Status | Family | Per-seed 4-member Holm | excess-AURC range | Verdict |
|---|---|---|---|---|---|
| **MVTec AD** | in-prereg, **confirmatory** | fixed,tuned × pc,dm (4) | reject ×4 in **all 5 seeds**, p_holm=0.002 | [0.0235, 0.0499] | **CONSTRUCTIVE** |
| **VisA** | post-freeze, **exploratory** | fixed,tuned × pc,dm (4) | reject ×4 in **all 5 seeds**, p_holm=0.002 | [0.0444, 0.1055] | constructive (exploratory) |

VisA's larger excess-AURC is consistent with the manuscript's note that MVTec's near-saturated
backbones leave the *per-category* audit little headroom, whereas VisA has more. Note that the
**pooled** MVTec test still rejects decisively despite that per-category saturation — pooling
recovers power across the 15 categories, which is the whole point of the confirmatory
construction vs the exploratory per-category readout (10–16 / 24–30 cells at seed 0).

Per the F3 falsification table: "all tests reject with excess-AURC CIs excluding zero → the
constructive arm publishes." That is what happened. C2 is verdict-symmetric and remains
publishable either way; the constructive direction is the one realized.

Raw per-seed / per-practice numbers: `c2_mvtec.json`, `c2_visa.json`.

---

## PART 2 — V1 tier-2 grading (amendments A1 / A2 / A3)

Grading re-reads the cached tier-2 blocks (`gate_calibration/v1_*.json`) and applies the
frozen amendments; it does not recompute the gate. Cell = (backbone, category, seed).

**A1 override (per-repeat power floor):** the cached `underpowered_*` flags use pooled-over-R
totals (anticonservative per A1/D8). We override with per-repeat counts
(`n_eval_*_total / n_repeats`); escaped powered iff per-repeat n_eval_def ≥ 22, false-reject
powered iff per-repeat n_eval_good ≥ 36.

**A1/A2 interval:** the pooled CP UB is "never the tier-2 verdict" (A1), so for powered
escaped cells we grade on a per-repeat one-sided 95% Clopper–Pearson UB reconstructed at
n = per-repeat n_eval_def with k = round(rate·n) via the codebase's own `clopper_pearson_upper`.
The power partition and false-reject buckets below are **exact** (deterministic from counts);
only the pass/fail split *within* powered escaped cells depends on this reconstruction (the
exact verdict would need the raw per-repeat records; the pooled rate is used as the per-repeat
point estimate). Sanity check: pilot bottle (rate 0.0839, n=31) → per-repeat UB 0.2315,
well above 0.13 — confirming A2's "expected to fail near the target," and wider than the pooled
0.1300 it reported.

**A3:** false-reject graded only over G2-certified cells; non-certified → G2-REFUSED-excluded,
never counted as a pass.

### MVTec AD — 150 cells (15 cats × 2 backbones × 5 seeds)

**Escaped axis**

| Bucket | Count | Cells |
|---|---|---|
| underpowered-excluded (A1) | **20** | toothbrush, transistor (per-repeat n_eval_def = 15, 20 < 22) × 2 × 5 |
| pass | 15 | dinomaly·cable, dinomaly·hazelnut, patchcore·hazelnut (the near-zero-miss cells) |
| fail | 115 | the remaining powered cells |

Power partition = **13 powered / 2 underpowered categories**, matching paper.tex's stated
expectation ("per-repeat underpowered in 2/15 categories"). Per A2 the 115 fails are the
expected stringent-variance behaviour near the target, **not** certificate failures —
**tier-1 passes 150/150** (the certificate-validity statistic).

**False-reject axis — 0 of 150 graded (structurally underpowered on MVTec)**

| Bucket | Count | Categories |
|---|---|---|
| G2-REFUSED-excluded (A3) | **110** | bottle, capsule, carpet, grid, leather, metal_nut, pill, tile, toothbrush, wood, zipper (11) × 2 × 5 |
| underpowered-excluded (A1) | **40** | cable, hazelnut, screw, transistor (4 G2-certified, but per-repeat n_eval_good ≤ 30 < 36) × 2 × 5 |

This is exactly the A1+A3 preregistered outcome: even the 4 G2-certified categories cannot
support a per-repeat tier-2 false-reject check on MVTec (max per-repeat eval-good = 30 < 36).

### VisA — 120 cells (12 cats × 2 backbones × 5 seeds), POST-FREEZE exploratory

**Escaped axis:** 17 pass, 103 fail, 0 underpowered (all VisA categories per-repeat powered ≥22).
**False-reject axis:** 4 pass, 66 fail, **50 underpowered-excluded, 0 G2-refused** — all VisA
cells are G2-certified (more good images per category), so unlike MVTec the false-reject axis
is partially gradeable here. Exploratory only; kept out of the MVTec confirmatory family.

Per-cell detail: `tier2_mvtec.json`, `tier2_visa.json`.

---

## Reproduce

```
cd reliability-commons/tools/inspect-gate
PYTHONPATH=$(pwd)/../.. .venv/bin/python c2_tier2_2026-07-13/run_c2_pooled_audit.py
PYTHONPATH=$(pwd)/../.. .venv/bin/python c2_tier2_2026-07-13/run_tier2_grading.py
```
