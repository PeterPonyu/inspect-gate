# inspect-gate preregistration — DRAFT 2026-07-10

**Paper:** certified escaped-defect triage on MVTec AD (`apps-design/01-APP-mvtec-triage.md`, incl.
its 2026-07-10 ADDENDUM). **Status:** DRAFT — not yet frozen. Freeze requires (a) the K6 citation
re-scan, (b) the Dinomaly branch resolution of §1, (c) sign-off on the three preregistered
amendments in §9.

Every count in this document is traced to a pilot artifact under
`pilot_results_2026-07-10/root/autodl-tmp/inspect_gate_pilot_results/` or derived by stated
arithmetic from `phase0_staging.json`. Nothing is quoted from the design doc as measured fact.
Genuinely unknown quantities are marked **[TO BE MEASURED AT MAIN RUN]**.

---

## 1. Frozen roster — and the two-branch Dinomaly prereg

| Backbone | Status as of 2026-07-10 | Evidence |
|---|---|---|
| **PatchCore** (Roth et al., arXiv:2106.08265) via anomalib 2.5.0 | **ANCHOR, scored, reproduction gate PASSED** | `phase0_reproduction.json`: `reproduction_gate_pass: true`; markers `SCORE_patchcore_seed{0,1}.marker = OK`, `CELL_patchcore_{bottle,screw,carpet}.marker = OK` |
| **Dinomaly** (Guo et al., CVPR 2025) | **NOT SCORED.** Its `score_dinomaly.py` path is `dump-ingest` (default mode: ingest a score dump the Dinomaly repo's own eval script produced). The checkpoint was **not obtained** on the pilot box; the `direct` mode is explicitly UNVERIFIED and raises rather than guessing the repo API. | markers `SCORE_dinomaly_seed{0,1}.marker = SKIPPED_DISCLOSED`, `CELL_dinomaly_{bottle,screw,carpet}.marker = SKIPPED_DISCLOSED`; no `cell_dinomaly_*.json` exists |
| EfficientAD | **DROPPED from the confirmatory roster** (ADDENDUM). Optional Phase-3 exploratory arm only. | `SOTA-REPRODUCTION-PLAN-2026-07-10.md` §2: "EfficientAD has NO official code" |

**The two branches are preregistered now, before the main run, so the choice cannot be made after
seeing results.** Let `B` = number of backbones whose scores exist at main-run launch.

- **Branch A (B = 2)** — Dinomaly scores obtained (checkpoint downloaded, its eval script run, dump
  ingested through `score_dinomaly.py --mode dump-ingest`, and its **own** reproduction gate passed
  against the official-repo MVTec image-AUROC, tolerance frozen at Phase 0 exactly as PatchCore's
  was) **before** any gate calibration on Dinomaly scores.
- **Branch B (B = 1)** — Dinomaly scores not obtained by launch. The paper becomes a **disclosed
  single-backbone study**. It is published as such; Dinomaly is named in the limitations section as
  the missing second backbone and the reason (checkpoint not obtained), not silently omitted.

The design's own rules generate the family sizes; nothing is hardcoded (see §4). Branch B is a
*weaker* paper, not an invalid one: C1's certificate and C3's tool stand on one backbone; C2's
audit loses the cross-backbone replication and its Holm family shrinks. Branch B must additionally
soften C1's "across 2 backbones" wording.

**No third option is preregistered.** If Dinomaly scores arrive mid-run, the run restarts under
Branch A from scratch; partial-roster mixing is forbidden.

---

## 2. Frozen targets, split protocol, and PatchCore configuration

| Item | Frozen value | Source |
|---|---|---|
| α_miss (escaped-defect, per category) | **0.10** | design §1 C1; pilot `alpha_miss: 0.1` in all three cell JSONs |
| α_fr (false-reject, per category) | **0.05** | design §1 C1; pilot `alpha_fr: 0.05` |
| Tolerance for V1 tier-1/tier-2 | **+3pp** (thresholds 0.13 / 0.08) | pilot `tolerance_pp: 0.03` |
| CP interval confidence | **95% one-sided** | pilot `confidence: 0.95` |
| Audit α (Holm) | **0.05** | pilot `audit.alpha: 0.05` |
| Permutations per audit test | **2000** | pilot `n_perm: 2000` |
| Mondrian strata (confirmatory) | **category** only | pilot `mondrian: "category"` |
| G2 good-calibration source (primary) | **`--good-cal test`** (test-side calibration half) | pilot `good_cal_mode: "test"`; design §3.2 "primary protocol" |
| Repeated splits | **R = 20**, stratified 50/50 by (category, label), `split-seed = repeat index` (0…19) | design §3.2/§3.3; `splits.py::repeated_stratified_splits` |
| Split rounding | `n_cal = round(0.5 · n_stratum)`, Python round-half-to-even | `splits.py:136` (`int(round(frac * n))`) — reproduces every pilot `n_cal_defect`/`n_cal_good` exactly |
| Backbone seeds | **5** per (backbone, category), seeds 0–4 | design §3.3 |
| KS exchangeability gate α | 0.05, BH across 15 categories (train-holdout arm only) | design §2.3; pilot `ks_alpha: 0.05`, `ks_gate: {}` (unused under `good_cal=test`) |
| defect-type Mondrian floor | `min_defect_type_n = 10` | pilot `min_defect_type_n: 10` |

**PatchCore configuration actually used (read from `orchestration/score_patchcore.py:58-60`):**
`backbone = wide_resnet50_2`, `layers = (layer2, layer3)`, `coreset_sampling_ratio = 0.10`,
`device = cuda`. The seed is applied via `torch.manual_seed(seed)` at `score_patchcore.py:161`;
**no seed kwarg is passed to `Patchcore(...)`** (line 164). Whether coreset subsampling actually
consumes the global torch RNG — i.e. whether seeds 0–4 produce genuinely distinct coresets — is
**[TO BE MEASURED AT MAIN RUN]** by diffing `scores_patchcore_seed0.jsonl` against
`scores_patchcore_seed1.jsonl`. If the score tables are bit-identical, PatchCore has **zero** seed
variance and the paper reports it as a deterministic backbone (5 seeds → 1 effective cell), which
is a disclosure, not a defect.

**Data provenance:** `mvtec_anomaly_detection.tar.xz`,
`sha256 = cf4313b13603bec67abb49ca959488f7eedce2a9f7795ec54446c649ac98cd3d`
(`phase0_staging.json`). Enumerated counts reconcile exactly with the design's aggregate facts:
train-good sum = **3,629**; test sum = 467 good + 1,258 defective = **1,725**; defect types = **73**.

---

## 3. Per-category certifiability floors at the frozen α (computed, not assumed)

Rule (design §2.3): `α_min = 1/(n_cal + 1)`; a stratum is certifiable iff `α_min ≤ α`.
`n_cal_good` and `n_cal_defect` are derived from `phase0_staging.json` by the frozen split rule
`round-half-to-even(n/2)`. Verified against the pilot: bottle (10, 32), carpet (14, 44),
screw (20, 60) — the table below reproduces all six numbers, and the pilot's
`alpha_min_g1`/`alpha_min_g2` to the last digit.

| Category | test good | test defect | n_cal_good | n_cal_def | α_min(G1)=1/(n_cal_def+1) | G1 @0.10 | α_min(G2)=1/(n_cal_good+1) | G2 @0.05 | n_eval_good | n_eval_def |
|---|---|---|---|---|---|---|---|---|---|---|
| bottle | 20 | 63 | 10 | 32 | 0.030303 | OK | **0.090909** | **REFUSE** | 10 | 31 |
| cable | 58 | 92 | 29 | 46 | 0.021277 | OK | 0.033333 | OK | 29 | 46 |
| capsule | 23 | 109 | 12 | 54 | 0.018182 | OK | **0.076923** | **REFUSE** | 11 | 55 |
| carpet | 28 | 89 | 14 | 44 | 0.022222 | OK | **0.066667** | **REFUSE** | 14 | 45 |
| grid | 21 | 57 | 10 | 28 | 0.034483 | OK | **0.090909** | **REFUSE** | 11 | 29 |
| hazelnut | 40 | 70 | 20 | 35 | 0.027778 | OK | 0.047619 | OK | 20 | 35 |
| leather | 32 | 92 | 16 | 46 | 0.021277 | OK | **0.058824** | **REFUSE** | 16 | 46 |
| metal_nut | 22 | 93 | 11 | 46 | 0.021277 | OK | **0.083333** | **REFUSE** | 11 | 47 |
| pill | 26 | 141 | 13 | 70 | 0.014085 | OK | **0.071429** | **REFUSE** | 13 | 71 |
| screw | 41 | 119 | 20 | 60 | 0.016393 | OK | 0.047619 | OK | 21 | 59 |
| tile | 33 | 84 | 16 | 42 | 0.023256 | OK | **0.058824** | **REFUSE** | 17 | 42 |
| toothbrush | 12 | 30 | 6 | 15 | 0.062500 | OK | **0.142857** | **REFUSE** | 6 | 15 |
| transistor | 60 | 40 | 30 | 20 | 0.047619 | OK | 0.032258 | OK | 30 | 20 |
| wood | 19 | 60 | 10 | 30 | 0.032258 | OK | **0.090909** | **REFUSE** | 9 | 30 |
| zipper | 32 | 119 | 16 | 60 | 0.016393 | OK | **0.058824** | **REFUSE** | 16 | 59 |

### 3.1 The headline floor result (frozen before the main run)

- **G1 (escaped-defect) at α_miss = 0.10: certifiable in 15/15 categories.** Worst floor is
  toothbrush, α_min = 1/16 = 0.0625 ≤ 0.10. **K5 does not fire** (it requires α_min > 0.10 for ≥ 3
  categories; it fires for zero).
- **G2 (false-reject) at α_fr = 0.05 under the primary `--good-cal test` protocol: certifiable in
  only 4/15 categories** — cable, hazelnut, screw, transistor. **11 categories are REFUSED:**
  bottle, capsule, carpet, grid, leather, metal_nut, pill, tile, toothbrush, wood, zipper.
  Certification needs `n_cal_good ≥ 19`, i.e. `n_test_good ≥ 38`; only those four clear it.
  The pilot confirms this on real data: `g2_certified: false` for bottle (`alpha_min_g2 = 0.0909`)
  and carpet (`0.0667`), `true` for screw (`0.047619`).
- **Secondary remedy, preregistered:** the `--good-cal train-holdout` arm (20% of train-good,
  `n_hold = round(0.2·n_train_good)`) lifts the G2 floor everywhere **except toothbrush**
  (n_train_good = 60 → n_hold = 12 → α_min = 1/13 = 0.076923 > 0.05). Floors under that arm range
  from 0.012658 (hazelnut) to 0.023256 (bottle). **Toothbrush's G2 is refused under both arms and
  is preregistered as permanently uncertifiable at α_fr = 0.05.** This arm remains *secondary*: it
  is admitted per category only through the KS exchangeability gate, and any category failing KS
  downgrades to `audited-not-certified` (measured false-reject rate + CI, no certificate).

**Consequence for C1, stated now:** under the primary protocol the paper certifies G1 in every
category and G2 in four. The remaining 11 categories report G2 as **audited-not-certified**. This
is the paper's honesty figure (F6) doing its job, not a failure to be repaired after the fact.

---

## 4. Family sizes — arithmetic for both branches

Design rules (verbatim): V1 = *15 categories × B backbones*; confirmatory Holm = *3 practices
{B1 fixed, B2 tuned, B3 quantile} × B backbones*; exploratory BH = *3 × 15 × B*.

| Family | Branch A (B = 2) | Branch B (B = 1) |
|---|---|---|
| **V1 validity cells** | 15 × 2 = **30** | 15 × 1 = **15** |
| **Confirmatory Holm** | 3 × 2 = **6** | 3 × 1 = **3** |
| Exploratory BH (FDR 0.10) | 3 × 15 × 2 = **90** | 3 × 15 × 1 = **45** |

**Sub-branch on B3.** The pilot could not run B3: all three cell JSONs carry
`skipped: [{practice: "quantile", skipped_reason: "no train_good_records supplied -- B3 needs a
held-out train-good pool"}]`, and `holm_family_size: 2`. The main run **must** dump train-good
scores so B3 runs. If, at launch, train-good scores are unavailable, the confirmatory Holm family
degrades to *2 practices × B*: **4** (Branch A) or **2** (Branch B), disclosed in T4 with B3 moved
to future work. Preregistering this now removes any post-hoc freedom over the family size.

V1 is **not** a Holm family (it is a certificate-validity audit, per design §1) and is never
multiplicity-corrected.

---

## 5. Pilot evidence (three PatchCore cells, R = 5 repeats, seed 0)

**Reproduction gate** (`phase0_reproduction.json`): target 0.991, tolerance 0.02, over
{bottle, carpet, screw}: per-category image-AUROC **1.000 / 0.986758 / 0.955934**,
mean **0.980897**, min **0.955934**, `pass: true`, `reproduction_gate_pass: true`.
The gate as implemented tests the **mean** (|0.980897 − 0.991| = 0.0101 ≤ 0.02); screw alone sits
0.0351 below target. **K3 (backbone floor, mean AUROC ≥ 0.90) is satisfied with margin** — marker
`K3_BACKBONE_FLOOR.marker = OK`.

| Cell | tier-1 mean escaped | tier-1 mean FR | `pass_tier1` | tier-2 escaped UB | `pass_escaped` | tier-2 FR UB | `pass_false_reject` | mean deferral | G1 cert | G2 cert |
|---|---|---|---|---|---|---|---|---|---|---|
| bottle | 0.083871 | 0.000000 | **true** | 0.130037 | **false** | 0.058155 | true | 0.692683 | true | **false** |
| screw | 0.084746 | 0.047619 | **true** | 0.116352 | **true** | 0.097514 | **false** | 0.185000 | true | true |
| carpet | 0.106667 | 0.000000 | **true** | 0.146723 | **false** | 0.041893 | true | 0.681356 | true | **false** |

**K-criteria status from the pilot:**
- **K1 (coverage sanity)** — SATISFIED. `pass_tier1 = true` in 3/3 cells; the split/exchangeability
  construction produces empirical escaped-defect rates inside α_miss + 3pp everywhere. Note carpet's
  tier-1 mean escaped rate is 0.1067, *above* α_miss = 0.10 but inside the 3pp tolerance — exactly
  the behaviour the two-tier criterion was designed to absorb.
- **K2 (vacuity)** — NOT TRIGGERED on the pilot (deferral 0.185 / 0.681 / 0.693, none > 0.80), but
  **at risk**: bottle and carpet defer ~68–69% *because* their G2 is refused, so `t_hi = +inf` and
  the auto-reject region is empty. K2 must be re-evaluated at the main run over 15 categories.
- **K3 (backbone floor)** — SATISFIED (above).
- **K5 (calibration floor)** — NOT TRIGGERED, and cannot be: §3.1 shows α_min(G1) ≤ 0.0625 < 0.10 in
  every category.
- **K4 (audit headroom)**, **K6 (scoop re-scan)**, **K7 (compute guard)** — **[TO BE MEASURED AT
  MAIN RUN]** / pre-freeze.

**Pilot audit outcomes** (per-category, family size 2, B3 skipped): screw rejects the random-deferral
null for both practices (excess-AURC 0.069874, permutation p = 0.0009995, `p_holm = 0.001999`,
`reject_holm: true`); carpet does not (excess 0.094191, p = 0.062469, `p_holm = 0.124938`); bottle is
degenerate (AUROC 1.0 ⇒ `aurc_method = aurc_random = 0.0`, excess 0, p = 1.0). These are
**exploratory per-category readouts, not the confirmatory family** — see §6-D5.

---

## 6. Disclosed deviations from the design doc (as of 2026-07-10)

- **D1 — EfficientAD → Dinomaly.** Reason: EfficientAD has **no official code release**; every
  implementation is a community reimplementation (`SOTA-REPRODUCTION-PLAN-2026-07-10.md` §2), and a
  certified-triage paper cannot anchor a binding reproduction gate on numbers that are not
  independently re-derivable. EfficientAD-via-anomalib is demoted to an optional Phase-3 exploratory
  arm with an explicit "community reimplementation, not independently verifiable" banner.
- **D2 — anomalib 2.5.0 adaptation, three API drifts, all fixed in `score_patchcore.py` with on-box
  evidence dated 2026-07-10:**
  1. `MVTec` → `MVTecAD` rename (`ImportError: cannot import name 'MVTec' ... Did you mean:
     'MVTec3D'?`) — handled by a try/except import at `score_patchcore.py:139-157`.
  2. **`Split` enum zero-filter bug:** the stock `_setup` compares `Split.TRAIN`/`Split.TEST` enums
     against the samples DataFrame's *string* `split` column, silently yielding **0 rows** (raw
     `make_*_dataset(root, split="train")` returns 209 bottle rows; the datamodule returned 0).
     Worked around by a subclass passing string splits (`score_patchcore.py:150-155`).
  3. **`ImageBatch` flattening:** `Engine.predict` yields `ImageBatch` dataclasses whose `items` is a
     *property*, not a dict method; treating a batch as one record made `float()` fail on the
     multi-element `pred_score` tensor (verified on-box: 83 bottle images → 3 batches → `n_failed=3`).
     Fixed at `score_patchcore.py:183-191`.
- **D3 — PatchCore settings were never named in the design.** Frozen here from the script's defaults:
  `wide_resnet50_2`, layers `layer2,layer3`, `coreset_sampling_ratio = 0.10` (§2).
- **D4 — Pilot ran R = 5 repeats, not R = 20** (`n_repeats: 5` in all three cell JSONs). The main run
  binds R = 20. Pilot numbers are therefore *not* the paper's numbers.
- **D5 — The pilot audit is not the confirmatory construction.** It ran per-category
  (`n = 41 / 59 / 80` items, `holm_family_size: 2`, Holm applied *within* a category). The
  confirmatory family is 3 practices × B backbones with **categories as blocked bootstrap units** and
  the matched-abstention permutation p-value computed within category and combined across the 15
  categories. Two consequences visible in the pilot: (a) B1 (global fixed) and B2 (per-category tuned)
  are **numerically identical in every cell** — identical `band_width`, `aurc_method`, `p_value` —
  because with one category a global threshold *is* the per-category threshold; B1 must be tuned on
  the **pooled 15-category** calibration half; (b) `excess_aurc_ci` is degenerate (`[x, x]`) because a
  category-blocked bootstrap over one block has zero width.
- **D6 — B3 (train-good quantile) did not run in the pilot** (no train-good score dump). See §4.
- **D7 — Dinomaly scores do not exist.** See §1.
- **D8 — Tier-2 interval construction.** `certify.py` pools escaped/false-reject counts **across the
  R repeats** and computes one Clopper-Pearson upper bound on the pooled counts (e.g. bottle
  `n_eval_def_total = 155 = 31 × 5`, `n_eval_good_total = 50 = 10 × 5`). The design specifies the
  power floor on "the per-category **eval-half** defective count" — i.e. per repeat. The repeats
  resample one finite test set and are **correlated**, so pooling inflates n and yields an
  anticonservative interval. See the amendment in §9-A1.

---

## 7. Analysis plan (order is binding)

1. **Stage + verify.** Untar from `/root/autodl-pub`, confirm `tarball_sha256`, re-enumerate
   `category_counts`, assert equality with §3's table. Any mismatch halts the run.
2. **Reproduction gate (binding, per SOTA-plan §3.3).** Score all 15 categories per backbone; gate on
   published MVTec image-AUROC within the frozen tolerance (PatchCore: 0.991 ± 0.02). A backbone that
   fails is **removed from the roster** and the branch of §1 recomputed. No gate calibration runs
   before this passes.
3. **K3 check** (mean image-AUROC ≥ 0.90 per backbone). Failure halts.
4. **Score caching.** 15 categories × B backbones × 5 seeds. Then verify the seed-variance question
   of §2 by score-table diff.
5. **Gate calibration + V1.** For each (backbone, category, seed): R = 20 stratified 50/50 splits,
   `split-seed = repeat index`. Per stratum print `n_cal_defect`, `n_cal_good`, `α_min(G1)`,
   `α_min(G2)`, `g1_certified`, `g2_certified`. **Refusals are emitted, never rounded away.**
   V1 tier-1 over all 15·B cells; V1 tier-2 only where the per-repeat power floor is met (§9-A1).
6. **K1, K2, K5 gates.** Halt-and-fix on K1; K2/K5 trigger their preregistered remedies (K5's remedy
   order: cal fraction 50% → 60%, then per-category α raise, disclosed in F6).
7. **Audit (C2, confirmatory).** For each of the 3 practices × B backbones: matched-abstention
   permutation p-value within category (`n_perm = 2000`), pooled excess-AURC vs
   `relmetrics.aurc.random_aurc` (closed form, never Monte-Carlo'd), category-blocked bootstrap CI
   (`block_ids = category`). Holm at α = 0.05 across the family of §4. Deferral budgets matched to
   the gate's realized rate via a symmetric band.
8. **K4 check** (oracle-deferral headroom ≥ 0.02 in ≥ 4/15 categories). Failure reframes C2 as a
   saturation finding.
9. **Exploratory (BH, FDR 0.10, watermarked EXPLORATORY):** per-category audit breakdown, defect-type
   Mondrian coverage-debt map (`min_defect_type_n = 10`), train-holdout G2 arm deltas.

**Exclude-and-count convention (portfolio standard).** Every record dropped anywhere in the chain is
counted and reported, never silently discarded: `score_patchcore.py` returns `n_failed` for
unextractable predictions; `audit.py` reports `n_excluded` per practice (pilot: `n_excluded: 0` in
all six practice-cells); `skipped` practices carry a `skipped_reason` string. Denominators in every
table are the roster-derived counts of §3/§4, never the post-exclusion counts.

### 7.1 Falsification conditions (what kills each finding)

| Finding | Falsified if |
|---|---|
| **F1 / C1 (certificate holds)** | tier-1 mean escaped rate > 0.13 (or mean FR > 0.08 in a G2-**certified** category) in ≥ 5 of the 15·B V1 cells → K1 fires, construction is broken, no result is reportable |
| **C1 (non-degenerate)** | median deferral > 0.80 in ≥ 8/15 categories on **all** backbones → K2, certificate is vacuous, C1 is killed or α re-targeted |
| **F2 / C1 tier-2** | pooled-across-seeds CP upper bound > target + 3pp in any *adequately powered* cell → that cell fails tier-2 and is reported as failing (see the bottle/carpet warning, §9-A2) |
| **F3 / C2 (practice has skill)** | after Holm, no practice × backbone test rejects the analytic random-deferral null → the **debunking arm** publishes ("standard practice carries no deferral skill beyond random") |
| **F3 / C2 (debunking)** | all 6 (or 3) tests reject with excess-AURC CIs excluding zero → the **constructive arm** publishes; C2 is verdict-symmetric and cannot be falsified into non-publication |
| **C2 (discriminable at all)** | oracle headroom < 0.02 in ≥ 12/15 categories → K4, reframe as saturation |
| **C3 (tool)** | golden-file tests fail to reproduce the paper's result JSONs bit-for-bit |

---

## 8. What is NOT preregistered (exploratory; no confirmatory claim may rest on these)

- The **defect-type Mondrian** analysis in full. There are **73** defect-type strata (raw counts range
  8 to 30); after the frozen 50/50 split, **43 of 73** have a calibration half below
  `min_defect_type_n = 10` and are refused outright, falling back to category level with a
  coverage-debt note. (Illustrative: all 8 of cable's types have ≤ 14 images; transistor's 4 sit at
  exactly 10; wood's `color` at 8.) BH, FDR 0.10, watermarked EXPLORATORY.
- The **train-holdout G2 arm** and its per-category deltas, including the KS exchangeability gate
  outcomes. Secondary by construction (design §3.2).
- The **EfficientAD-via-anomalib robustness arm** (D1), if run at all.
- **Deferral-rate frontier sweeps** over (α_miss, α_fr) — F4 is descriptive, no test.
- Any **pooled-across-category** marginal coverage claim. Per design §6 these are the only way to
  speak about α tighter than 0.10, and they must be labelled as pooled, never per-category.
- All **pilot numbers in §5**. They are R = 5, one seed, three categories, and one backbone. They
  motivate the amendments of §9; they support no claim in the paper.

---

## 9. Preregistered amendments requested before freeze

**A1 — Tier-2 power floor is per-repeat, and it bites.** Under the design-literal per-repeat reading,
the thresholds are `n_eval_def ≥ 22` (from `1 − 0.05^(1/n) ≤ 0.13`) and `n_eval_good ≥ 36` (from
`1 − 0.05^(1/n) ≤ 0.08`) — both confirmed by the pilot's own `min_n_def_required: 22` and
`min_n_good_required: 36`. Applying them to the real per-repeat eval counts of §3:

- **Escaped-defect tier-2:** UNDERPOWERED in **toothbrush** (n_eval_def = 15) and **transistor**
  (n_eval_def = 20). Powered in the other 13.
- **False-reject tier-2:** **UNDERPOWERED in all 15 categories.** The largest per-repeat eval-good
  count on MVTec AD is transistor's 30, below the required 36. *No category on this dataset can
  support a tier-2 false-reject check under the primary protocol.*

The implementation currently hides this by pooling over repeats (D8), which manufactures power from
correlated resamples of one fixed eval set. **Preregistered decision:** report tier-2 escaped-defect
using the per-repeat floor (13 powered categories); report tier-2 false-reject as **structurally
underpowered on MVTec AD** and rely on tier-1 plus the F6 floor table for the α_fr axis. The pooled
interval may be shown as a clearly-labelled secondary readout, never as the tier-2 verdict.

**A2 — Tier-2's +3pp tolerance is near-unpassable by construction.** Split conformal targets α_miss
*exactly* (the order statistic `k = floor(α·(n+1))` yields an expected miss rate of ≈ α), so a
one-sided 95% Clopper-Pearson upper bound sits well above it — at the pilot's pooled n = 155 the gap
between bottle's realized rate and its CP upper bound is **+4.6pp**, already larger than the 3pp
tolerance (the normal approximation `1.645·√(α(1−α)/n)` = 4.0pp understates it; CP is wider). This is
exactly what the pilot shows: bottle's realized rate 0.083871
gives UB **0.130037** — failing the 0.13 threshold by 3.7 × 10⁻⁵ — and carpet's 0.106667 gives
0.146723. Both `pass_escaped: false` **under the most generous (pooled) interval available**. The
tolerance was chosen so a *zero-miss* cell at n = 22 passes; it was never checked against a cell whose
miss rate equals the target it was calibrated to hit. **Preregistered decision:** keep the 3pp
tolerance (it is frozen and the criterion is honest), and state in F2/T3 that tier-2 is a *stringent*
check a correctly-calibrated gate is expected to fail near the target — reporting tier-2 failures as
evidence about the *estimator's variance*, not about the certificate's validity, whose test is tier-1.
Any alternative (widening the tolerance after seeing bottle's 0.130037) is forbidden as post-hoc.

**A3 — V1's false-reject cells are vacuous wherever G2 is refused.** When `g2_certified = false`,
`t_hi = +inf`, the auto-reject region is empty, and the measured false-reject rate is identically 0 —
so `pass_false_reject: true` is guaranteed without evidence. The pilot shows exactly this for bottle
and carpet (`mean_false_reject_rate: 0.0`, `t_hi: Infinity`, `g2_certified: false`, yet
`pass_false_reject: true`). Under §3.1 this affects **11 of 15 categories**, i.e. 22 of Branch A's 30
V1 cells. **Preregistered decision:** V1's false-reject axis is evaluated **only over G2-certified
cells** (4·B cells: cable, hazelnut, screw, transistor); the other 11·B cells are reported as
`G2-REFUSED (α_min > α_fr)` and are **excluded from every pass/fail count** — never counted as passes.
The design's K5 as written only trips on the G1 floor (`α_min > 0.10`) and would let this through
silently; this amendment closes that gap.

---

## 10. K6 scoop note

The design's §1 citation block (conformal anomaly detection; `nonconform`; CRC-SGAD; Shen & Liu;
Kumar et al.) was last scanned at design time. **The K6 re-scan and the full network
citation-verification pass — including CRC-SGAD's author list and the Laxhammar & Falkman FUSION-2011
bibliographic details, both venue-verified but not author-verified — must run before this document is
frozen.** If a published certified three-way triage on MVTec AD appears, the pre-decided pivot is
C2 + C3 primary, C1 demoted to replication-with-floors.
