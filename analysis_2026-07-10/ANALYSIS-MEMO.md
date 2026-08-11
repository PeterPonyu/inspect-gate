# inspect-gate post-analysis memo — 2026-07-10

**Scope:** post-analysis of the local GPU substrate (PatchCore fullscore, PatchCore train-good
holdout, Dinomaly Branch-A canonical scores) against `PREREG-DRAFT-2026-07-10.md`. That document's
own status line is authoritative: **DRAFT — not yet frozen**; freeze requires the K6 citation
re-scan, the Dinomaly branch resolution, and sign-off on amendments A1–A3 (§9). Nothing below is a
confirmatory paper result. Everything is a larger-N extension of the PREREG's own §5 pilot table
(3 categories, R=5, one backbone) to the full local substrate (15 categories, R=20, two backbones,
5 seeds each), run entirely under the **primary protocol** (`--good-cal test`, no train-holdout).

**Script:** `analysis_2026-07-10/scripts/run_analysis.py` (self-contained, reads only
`fullscore_results_2026-07-10/` and `dinomaly_brancha_2026-07-10/canonical/`, writes only under
`analysis_2026-07-10/`). Run log: `analysis_2026-07-10/run.log`. Raw JSON outputs: `reproduction/`,
`seed_stability/`, `gate_calibration/`, `audit/`, `SUMMARY.json`.

---

## 0. What ran vs. what is gated

**Ran (non-gated):**
- Phase-0-style reproduction gate, independently re-derived from local scores (not trusted from any
  log), for both backbones × all 5 seeds × 15 categories.
- Cross-seed stability (score-table diffs for PatchCore; per-category AUROC spread for both).
- G1 (escaped-defect) + G2 (false-reject) conformal gate calibration, **primary protocol only**
  (`good_cal_holdout=None`), R = 20 stratified repeats (design's frozen split protocol), per
  (backbone, seed) — 15 categories each, 10 cells total (2 backbones × 5 seeds).
- V1 tier-1 (mean-rate) pass/fail per cell (this *is* K1's own statistic) and V1 tier-2 (Clopper-
  Pearson UB) computed but reported **descriptively only**, per PREREG §9 A1/A2 (below).
- K1 (coverage sanity) and K2 (vacuity) per (backbone, seed).
- Exploratory per-category excess-AURC audit (practices `fixed`, `tuned` only — see §4), repeat-0
  halves, mirroring the PREREG §5 pilot's own per-category methodology (disclosed there as D5:
  "exploratory per-category readouts, not the confirmatory family").
- Full `tests/` suite before/after (untouched by this work — see §6).

**Explicitly NOT run (gated / structurally unavailable):**
- **The train-good holdout G2 "promotion" arm.** `holdout_results_2026-07-10/` was inspected only
  to characterize its schema (per-category `.holdout_provenance.json` + a 20%-of-train-good
  `scores_patchcore_*_seed*.jsonl`) and was **not loaded into any calibration call**. This is the
  PREREG §3.1 "secondary remedy" / §8 "not preregistered" train-holdout arm — the one the task
  brief named as the gated item. Unlocking it as anything beyond exploratory needs: (a) the
  per-category KS exchangeability gate to actually run (`gate.calibrate_gate(good_cal_holdout=...)`),
  and (b) sign-off that a category failing KS reports `audited-not-certified`, never a silent
  promotion.
- **B3 (train-good quantile) audit practice.** Not merely deferred — structurally impossible with
  the local substrate: neither `fullscore_results_2026-07-10/` nor
  `dinomaly_brancha_2026-07-10/canonical/` contains any `split="train"` record (verified directly;
  both are `{'test'}`-only). B3 needs a held-out train-good pool that only exists inside the gated
  `holdout_results_2026-07-10/` tarball.
- **Any cross-seed or cross-category pooled Holm-corrected confirmatory family (C2).** Design's own
  `run_main_grid.sh` Stage D ("combine the per-seed audit Holm families into ONE global family") is
  itself still a TODO skeleton in that script — there is no frozen pooling rule to reproduce. Every
  audit cell below stays scoped to one (backbone, seed, category), Holm-corrected only within its
  own 2-practice family, exactly like the PREREG's own pilot.
- **V1 tier-2 as a pass/fail verdict.** Computed (see §3) but reported as numbers only, per PREREG
  §9 A1 ("the pooled-across-repeats interval... manufactures power from correlated resamples...
  never as the tier-2 verdict") and A2 (the 3pp tolerance is a stringent estimator-variance check,
  not a certificate-validity test).
- **The K6 citation re-scan and Dinomaly-target literature confirmation as an *external* act** — I
  independently re-derived Dinomaly's image-AUROC from local scores and cross-checked it against
  the training log's own eval (§1), but did not perform a fresh literature/citation scan; that is
  explicitly out of scope for a CPU analysis pass.

---

## 1. Reproduction gate (both backbones, 15 categories, 5 seeds)

Recomputed independently via `inspect_gate.reproduction.image_auroc()` (Mann–Whitney rank-sum
identity) directly on the local canonical scores — never trusted from a log or the literature.

| Backbone | Target | Tolerance | Seeds | Mean I-AUROC range | Min-category range | Gate |
|---|---|---|---|---|---|---|
| PatchCore | 0.991 (design §3.1, `PATCHCORE_TARGET_AUROC`) | ±0.02 | 0–4 | 0.9817–0.9826 | 0.9111–0.9167 (toothbrush) | **PASS, 5/5 seeds** |
| Dinomaly | 0.996 (Guo et al., CVPR 2025, published mean MVTec I-AUROC — independently re-derived here, not literature-trusted) | ±0.02 | 0–4 | 0.9957–0.9965 | 0.9765–0.9824 (capsule) | **PASS, 5/5 seeds** |

My independent recomputation reproduces the Dinomaly training logs' own reported `Mean: I-Auroc`
line **exactly**, seed-for-seed (0.9965/0.9960/0.9960/0.9960/0.9957 —
`dinomaly_brancha_2026-07-10/root/autodl-tmp/dinomaly_branchA/train_seed{0..4}.log`), which is the
"0.9957–0.9965 across seeds" the task brief referenced. K3 (backbone floor, mean AUROC ≥ 0.90) is
satisfied with wide margin for both backbones.

Per-category weak points: PatchCore's floor is toothbrush (0.9167), Dinomaly's is capsule (0.9824)
— both far above K3's 0.90 floor but worth naming since they're also the categories driving each
backbone's smallest calibration pools (toothbrush has the fewest MVTec test images of any category).

---

## 2. Cross-seed stability

**PatchCore seed variance (PREREG §2's own "[TO BE MEASURED AT MAIN RUN]" question — now
answered):** all 60 seed0-vs-seedN score-table diffs (15 categories × 4 comparison seeds) are
**0/60 bit-identical**. Seeds 0–4 produce genuinely distinct coresets — `torch.manual_seed(seed)`
*does* propagate into PatchCore's coreset subsampling despite no explicit seed kwarg to
`Patchcore(...)` (PREREG §2's open question). Score deltas are real but modest: max |Δscore| across
all 60 pairs ranges 0.026–0.153 (mean 0.074), i.e. seeds are a genuine-but-small variance source,
not a relabeling. **Consequence:** PatchCore should be reported as a 5-effective-seed backbone in
the main grid, not collapsed to 1 (the PREREG left this open pending measurement — it's now closed).

**Dinomaly seed spread:** per-category I-AUROC range across the 5 seeds is tiny everywhere (widest:
capsule, range 0.0060, std 0.0026; most categories range < 0.002). Mean I-AUROC across seeds:
0.9960 ± 0.00028 (std). Dinomaly is a low-seed-variance backbone on this substrate.

---

## 3. Gate calibration (G1 + G2, primary protocol, R = 20, 15 categories × 5 seeds × 2 backbones)

**Certifiability floors cross-check.** Per-category `n_cal_defect`/`n_cal_good` computed here from
the full local test-set arrays match PREREG §3's published table **exactly, 0/15 mismatches**, for
both backbones (backbone-invariant, as expected — they're pure functions of the shared MVTec test
split), and are identical across all 5 seeds (0 mismatches, confirmed in `run.log`). G1 certified in
**15/15 categories** for both backbones; G2 certified in exactly the same **4/15** categories the
PREREG predicted from arithmetic alone: **cable, hazelnut, screw, transistor**. This is the
strongest sanity result in this pass — the full-scale run reproduces the PREREG's arithmetic-only
projection to the count.

**V1 tier-1 (the K1 statistic itself):** **150/150 cells pass** (2 backbones × 5 seeds × 15
categories, mean escaped-defect and mean false-reject rate both within target + 3pp tolerance,
every cell, every seed). **K1 not tripped** (0 violations, far below the 5-cell kill threshold) and
**K2 not tripped** (0 vacuous categories at the 80%-deferral/8-category threshold) in all 10
(backbone, seed) aggregates — see `gate_calibration/v1_{backbone}_seed{n}.json` and
`SUMMARY.json["gate_calibration_k1_k2"]`. Median per-category deferral at seed 0: PatchCore mean
55.1% (max pill 78.0%, min transistor 2.0%); Dinomaly mean 54.2% (max capsule 77.3%, min screw
3.1%) — expected given G2 refusal empties the auto-reject band in 11/15 categories (PREREG §5's own
K2-risk note), and not close to K2's 80%/≥8-category vacuity threshold.

**V1 tier-2 (descriptive only, per A1/A2 — NOT a pass/fail verdict here).** Pooling across R = 20
correlated repeats (the implementation's current, unmodified behavior, per PREREG D8) reproduces
exactly the anticonservative-power artifact A1 warned about: pooled `n_eval_def_total` for bottle is
620 (31/repeat × 20), far exceeding the per-repeat power floor of 22 — so the pooled construction
reports "adequately powered" everywhere it shouldn't. Recomputing per-repeat (dividing by 20, which
reproduces PREREG §3's own per-category `n_eval_def`/`n_eval_good` figures exactly): escaped-defect
tier-2 is underpowered in **toothbrush (15 < 22)** and **transistor (20 < 22)** only, 13/15
categories powered; false-reject tier-2 is **underpowered in all 15 categories** (largest per-repeat
`n_eval_good` is transistor's 30, still short of the required 36) — reproducing A1's finding exactly
at full scale, not just arithmetically. One notable pooled-construction anecdote: PatchCore seed 0's
screw cell fails the pooled tier-2 escaped-defect check (`pass_escaped=False`) despite passing
tier-1 cleanly — illustrating A2's point that tier-2 is a stringent estimator-variance check a
correctly-calibrated gate can fail near its own target, not evidence the certificate is broken.

---

## 4. Exploratory audit (excess-AURC vs. random-deferral null, `fixed`+`tuned` only)

B3 (train-good quantile) could not run for either backbone (§0 — no train-good scores in the local
substrate). Per-category audit (family size 2, matching the PREREG pilot's own methodology and its
D5 disclosure that B1≡B2 when scoped to one category):

- **PatchCore:** 10/30 practice-cells reject the random-deferral null after within-cell Holm
  (seed 0); 6/30 are degenerate (per-category AUROC = 1.0 ⇒ `aurc_random = 0`, zero measurable
  headroom by construction, same as the pilot's bottle result).
- **Dinomaly:** 0/30 practice-cells reject; 14/30 degenerate. Dinomaly's near-ceiling per-category
  AUROC (10/15 categories at 1.0 on this repeat-0 split) leaves threshold-based practices no room to
  show measurable skill above a baseline that is already near-perfect — an expected, not concerning,
  outcome for a near-saturated backbone.

K4 (audit headroom, design §4) was not computed — it needs an oracle-headroom statistic the design
names but `certify.py` doesn't yet implement (README: "not yet a certify.py function -- add if/when
the main grid needs it"). The excess-AURC-vs-random signal above is related but not the same
statistic; K4 proper is future work, not something this pass could close out.

---

## 5. What must be frozen to unlock the gated pieces

| Gated item | What unlocks it |
|---|---|
| Train-holdout G2 promotion (`holdout_results_2026-07-10/`) | Run the per-category KS exchangeability gate against it; sign-off that KS-failing categories report `audited-not-certified`, never silent promotion (PREREG §3.1/§8) |
| B3 audit practice | A train-good score dump for both backbones (none exists locally for either) |
| Cross-seed / cross-category pooled confirmatory Holm family (C2) | `run_main_grid.sh` Stage D's pooling rule needs to be *written* (currently a TODO comment), then frozen |
| V1 tier-2 as a verdict | PREREG §9 A1 (per-repeat vs. pooled power floor) and A2 (tolerance interpretation) sign-off |
| Any confirmatory C1/C2 claim in a paper | K6 citation re-scan (§10) + Dinomaly branch resolution (§1, now trivially Branch A — scores exist and pass reproduction) + A1–A3 sign-off, per the DRAFT's own status line |

---

## 6. Test suite

`PYTHONPATH=.../reliability-commons .venv/bin/python3 -m pytest tests/ -q`: **130 passed, 0
failed**, before and after this analysis pass (no `inspect_gate`/`orchestration` source file was
touched; only new files under `analysis_2026-07-10/` were added). The task brief anticipated "129
passed + 1 environment-guard failure about torch being installed locally" — this `.venv` has no
torch installed at all (`ModuleNotFoundError: No module named 'torch'`), so the guard test that
fails only when torch *is* importable instead passes cleanly here: 129 + 1 = 130, same total, a
benign environment difference, not a regression.

---

## 7. Draft-readiness verdict

**Not ready to draft a confirmatory paper**, by the DRAFT's own gating rule — three preconditions
(K6, Dinomaly branch resolution, A1–A3 sign-off) are still open, and this pass deliberately avoided
producing anything that could be mistaken for the confirmatory V1/C2 tables. **What this pass adds
concretely toward readiness:**

- The Dinomaly branch question (PREREG §1) is now trivially **Branch A**: Dinomaly scores exist,
  pass their own reproduction gate at 15/15 categories × 5/5 seeds, and are seed-stable. The
  "checkpoint not obtained" blocker that motivated leaving Branch B open is gone.
- G1's certificate-validity axis (C1's core claim) now has full-scale, both-backbone, 5-seed
  evidence with **zero K1/K2 trips and an exact match to the PREREG's arithmetic-only floor table**
  — this is the strongest signal the design's own machinery is sound going into freeze.
- PatchCore's seed-variance question is closed (genuinely 5 distinct seeds, not 1).
- What's still missing before freeze is *process*, not compute: the K6 re-scan and A1–A3 sign-off
  are editorial/preregistration steps, not additional GPU work — the train-good score dump needed
  for B3 (and to responsibly unlock the holdout G2 arm) is the one remaining data gap.

**Candidate SCIE-indexed venues** (per this portfolio's standing venue-fit rule — SCIE-only,
publisher-portal submission, no OpenReview; matches the existing inspect-gate retarget note from the
2026-07-10 write-up wave, TMLR → non-OpenReview journal):
1. **Journal of Intelligent Manufacturing** (Springer, SCIE) — primary fit: certified triage for
   industrial visual inspection is squarely in-scope, and the paper's applied-conformal-guarantee
   framing (not a new architecture) matches the journal's methods-for-manufacturing profile.
2. **IEEE Transactions on Industrial Informatics** (IEEE, SCIE) — alternate: broader industrial-AI
   readership, IEEEtran two-column format (consistent with the other IEEE-targeted papers already in
   this portfolio), a reasonable fit if the manufacturing-methods framing above doesn't land with a
   reviewer pool skewing more ML-systems than manufacturing-process.
