# B3-PatchCore post-hoc audit — the C2 family's feasible half completed (2026-07-13)

Compute-only run on cached scores (CPU). No manuscript edited by this script.
Runner + result JSON live beside this file. This closes the M1 red-team finding:
the earlier "no held-out train-good pool exists" justification for skipping B3 was
wrong for PatchCore — the pool exists and B3-PatchCore is now reported here, post-hoc.

---

## HEADLINE

**B3 (train-good score-quantile heuristic) is CONSTRUCTIVE for PatchCore, decisively,
in all 5 seeds — consistent with the frozen fixed/tuned arms.** Pooled excess-AURC over
the analytic random-deferral null is **0.053–0.056** (primary, self-consistent substrate),
every matched-abstention permutation p-value hits the floor **p = 0.0005 = 1/(2000+1)**,
and every category-blocked bootstrap CI excludes zero. A cross-run sensitivity arm agrees
(excess-AURC 0.046–0.059, same p-floor, CIs exclude zero).

**Labeling (unchanged):** the frozen per-seed **4-member** Holm construction
`{fixed, tuned} × {patchcore, dinomaly}` (`c2_tier2_2026-07-13`) **remains THE confirmatory
result.** This B3-PatchCore arm is **post-hoc / exploratory** — it completes the *feasible*
half of the prereg's full 6-member family. **B3-Dinomaly remains impossible**: the Dinomaly
branch has no train-side score dump at all (only the PatchCore holdout run scored train-good
images), so the full 6-member family cannot be run even now.

---

## Why B3 was skipped in the frozen pass, and why it is feasible now (M1 truth)

The frozen 2026-07-13 C2 pass ran `run_audit(..., train_good_records=None, ...)` and B3 fell
out of the family by the preregistered degradation (PREREG §4: `{fixed,tuned,quantile}` → 
`{fixed,tuned}` when no train-good pool is loaded; family 6 → 4). Two facts, stated plainly:

1. **The frozen analysis loaded no train-good records** — `ig_scores_full` (its PatchCore
   source) carries test scores only. That is why B3 degraded out *there*.
2. **A held-out train-good pool DOES exist for PatchCore.** The 2026-07-10 holdout run
   (`holdout_results_2026-07-10/.../ig_scores_holdout/scores_patchcore_<cat>_seed<n>.jsonl`)
   scored, in one inference pass, both the MVTec test images and the per-category train-good
   images (726 train-good images pooled across the 15 categories, per seed; 12–78 per category).

So the correct statement is **not** "no held-out train-good pool exists" (the false sentence
M1 flagged) but: *Dinomaly has no train-side dump (6-family impossible), the frozen pass ran
without train records loaded, and the PatchCore pool exists and its B3 arm is completed here
post-hoc.*

---

## Construction (identical to the frozen C2 machinery)

Per (practice) the audit is the frozen pooled-category construction: excess-AURC vs the
analytic random-deferral null (`relmetrics.aurc`, closed form), matched-abstention permutation
p (`n_perm=2000`, `strata=category`), category-blocked bootstrap CI, deferral band matched to
the conformal gate's realized pooled rate. `b3_quantile=0.95`. Split = repeat-0 50/50
stratified cal/eval. `alpha_miss=0.10`, `alpha_fr=0.05`, Holm `alpha=0.05`.

**The one authored knob — substrate (stated once, no tuning).** B3's threshold is the
per-category 0.95-quantile of *train-good* scores, then applied to the *eval-test* scores.
Train-good scores exist only in the holdout inference run, whose test scores differ from
`ig_scores_full` (the frozen C2 source) by ≈0.011 on average (a separate inference pass of
the same frozen checkpoints). To keep B3 free of any cross-run score-scale artifact, the
**primary** run computes all three practices end-to-end **on the holdout run** — train-good and
eval-test share one inference pass. The frozen fixed/tuned (on `ig_scores_full`) stay the
confirmatory anchor; the holdout-run fixed/tuned here are an **in-run reference** so B3 sits
beside its siblings on identical substrate. A **cross-run sensitivity** arm (B3 threshold from
holdout train-good, eval on the frozen `ig_scores_full` half) confirms the verdict is
substrate-independent.

---

## Numbers

### Primary (self-consistent, holdout run) — pooled excess-AURC, all 5 seeds

| practice | excess-AURC (min–max over seeds) | permutation p (all seeds) | all CIs exclude 0 |
|---|---|---|---|
| fixed (B1), in-run reference | 0.023–0.027 | 0.0005 | yes |
| tuned (B2), in-run reference | 0.033–0.042 | 0.0005 | yes |
| **quantile (B3), post-hoc** | **0.053–0.056** | **0.0005** | **yes** |

B3's effect size is *larger* than B1/B2 here (the train-good-quantile threshold sits further
from the calibrated operating point, so the |score − threshold| ordering has more headroom
above the random-deferral null). Per-seed: target deferral 0.528–0.538, n_eval = 864,
n_train_good = 726.

### Cross-run sensitivity (B3 eval on the frozen `ig_scores_full` half)

B3 excess-AURC 0.046–0.059 over the 5 seeds, every permutation p = 0.0005, every CI excludes
zero. **The B3 verdict does not depend on the substrate choice.**

### Post-hoc 5-member Holm (frozen 4 + B3-PatchCore)

Adding B3-PatchCore's holdout-run p-value to the frozen 4 members' own p-values gives a
5-member per-seed Holm family in which **all 5 members reject in all 5 seeds**
(p_holm = 0.0025 = 5 × 0.0005 < 0.05). Reported only to show the confirmatory 4-member verdict
is unchanged by the extra member; the substrates differ (frozen 4 on `ig_scores_full`, B3 on
the holdout run), so this is a robustness readout, **not** a new confirmatory family.

Raw per-seed / per-practice numbers, both substrates, and the combined Holm: `results.json`.

---

## Reproduce

```
cd reliability-commons/tools/inspect-gate
PYTHONPATH=$(pwd)/../.. .venv/bin/python b3_patchcore_2026-07-13/run_b3_patchcore_audit.py
```
