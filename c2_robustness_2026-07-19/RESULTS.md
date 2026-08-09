# L6 — C2 robustness across all R=20 repeats + K4 oracle headroom — 2026-07-19

Two hardening analyses for the confirmatory C2 audit. **POST-FREEZE EXPLORATORY — not
confirmatory; edits no frozen result.** L6a re-runs the *frozen* construction verbatim on
inputs the frozen analysis never used (repeats 1–19); L6b implements a preregistered-but-
never-built kill gate. Script: `script.py`. Full numeric output: `results.json`.

---

## PART 1 (L6a) — C2 across all 20 repeats

**Question.** The confirmatory C2 pooled audit (four-member per-seed Holm family
{fixed, tuned} × {patchcore, dinomaly}, MVTec; frozen in
`../c2_tier2_2026-07-13/`) rests on the repeat-0 cal/eval split only — an **AUTHORED
(minor)** choice per that analysis's own frozen-vs-authored table ("Split: audit uses the
repeat-0 50/50 stratified cal/eval split … Not independently pinned in prereg text").
Does the verdict survive the other 19 frozen splits?

**Construction.** Byte-identical code path to the frozen analysis
(`splits.stratified_cal_eval_split(repeat_seed=r)` → `gate.calibrate_gate` →
`gate.route_gate` → realized pooled deferral → `audit.run_audit(fixed, tuned;
n_perm=2000; Holm α=0.05)`), for all 20 repeats × 5 backbone seeds × 2 backbones = 200
cells (2 practices each). The R=20 splits are the frozen protocol's own
(`splits.py`: split-seed = repeat index).

**Replication check.** The repeat-0 rerun reproduces the frozen `c2_mvtec.json` values
**exactly**: max |Δ excess-AURC| = 0.0, max |Δ p| = 0.0 across all 20
(practice × backbone × seed) cells. The construction being swept is the frozen one, not
a re-implementation.

### Verdict

**The confirmatory verdict is stable in 20/20 repeats.** In every (repeat, seed) cell —
all 100 of them — the per-seed 4-member Holm family rejects the random-deferral null for
**all four members** (`all4_reject = true`). The authored cross-seed reduction
(seed-max-p + Holm) likewise rejects all four members in all 20 repeats. **Zero flips.**

| Quantity | Value |
|---|---|
| Repeats where all 5 seeds reject all 4 members | **20 / 20** |
| Worst raw p over all 200 practice-cells | 0.01399 (dinomaly:tuned, repeat 12, seed 1) → p_holm 0.01399, still rejects |
| Worst per-member max p (over repeats × seeds) | pc:fixed 0.00100; pc:tuned 0.00050; dm:fixed 0.00150; dm:tuned 0.01399 |
| Global min excess-AURC (over 200 cells) | **0.01454** (> 0 everywhere) |
| Realized pooled deferral the bands were matched to | 0.492–0.561 across all cells (stable) |

The softest repeat is **repeat 12**: all 8 dinomaly practice-cells there come off the
permutation floor (raw p 0.001–0.014, vs the floor 0.0005 everywhere else except 18 other
scattered cells at p ≤ 0.002). Every one still rejects after Holm in every seed. The
frozen repeat-0 choice is therefore not load-bearing: the constructive C2 arm
("standard threshold practice carries deferral skill beyond honest random deferral")
holds on every frozen split.

---

## PART 2 (L6b) — K4 oracle-deferral headroom (preregistered, never implemented)

**Spec.** Design `01-APP-mvtec-triage` §4 K4, preregistered in
`../PREREG-DRAFT-2026-07-10.md` §7 step 8 / §7.1:

> "oracle-deferral excess-AURC headroom < 0.02 in ≥ 12/15 categories → the audit cannot
> discriminate anything (backbone saturation); reframe C2 as a saturation finding"

(`ANALYSIS-MEMO.md` §4: "needs an oracle-headroom statistic the design names but
`certify.py` doesn't yet implement". The paper's Limitations admits this.)

**Ambiguity, documented per the brief.** The prereg names the statistic and the trip
rule but not the statistic's *inputs*. Most literal reading, stated once, no tuning:

- **(K4-a) Losses:** the audited practice's realized 0/1 errors on the eval half — the
  only loss vector in the confirmatory construction, built by `audit.py`'s own
  `_practice_predictions_and_conf` verbatim. Headroom is reported per
  (practice, backbone, seed) because fixed/tuned induce different loss vectors.
- **(K4-b) Split:** repeat-0, mirroring the authored C2 split choice (the only frozen
  precedent).
- **(K4-c) Oracle:** the error-last confidence ordering (`conf = 1 − loss`) — the
  maximum excess-AURC **any** deferral ordering can achieve on those losses, computed by
  `relmetrics.aurc.excess_aurc_gain` itself. For 0/1 losses this is exact and
  tie-order-independent (the correct-prefix losses are all 0 and the error-suffix losses
  all 1, so the Riemann sum cannot depend on within-group order). Cross-checked against
  the closed-form continuous limit −(1−e)·ln(1−e) for per-category error rate e: max
  |discrete − closed-form| = 0.0061 over all 960 category-cells (expected
  discrete-vs-integral gap).
- **(K4-d) Trip rule (verbatim):** headroom < 0.02 in ≥ 12/15 categories. MVTec only —
  VisA (12 categories) and MPDD (6) carry no preregistered K4 semantics; their counts
  are exploratory context.

### Verdict

**K4 does NOT trip — in any (practice, backbone, seed) cell.** Categories with oracle
headroom ≥ 0.02 (need ≥ 4/15 to pass; trip at ≤ 3/15):

| Backbone : practice | n categories ≥ 0.02, per seed (0–4) | min | K4 trips? |
|---|---|---|---|
| patchcore : fixed | 8, 8, 8, 8, 7 | 7/15 | **no** (no seed) |
| patchcore : tuned | 9, 9, 10, 10, 9 | 9/15 | **no** (no seed) |
| dinomaly : fixed | 7, 7, 7, 7, 7 | 7/15 | **no** (no seed) |
| dinomaly : tuned | 6, 7, 7, 7, 9 | 6/15 | **no** (no seed) |

The margin is wide: the worst cell clears the pass bar (≥ 4/15) by 2 categories and the
trip bar (≤ 3/15) by 3. The audit **can** discriminate on MVTec; the saturation reframe
is not triggered. The headroom is concentrated where expected — the degenerate
(zero-headroom) categories are the near-perfect-AUROC ones (bottle, hazelnut, leather,
metal_nut, tile at error rate 0.0 for patchcore:fixed seed 0, joined by cable 0.013 and
transistor 0.020 just under the bar), exactly the "near-saturated backbone" mechanics the
design's §6 risk note describes; but 6–10 categories retain real headroom in every cell,
which is why the pooled C2 test rejects decisively (Part 1).

**Exploratory context off-MVTec (no preregistered trip semantics):**

| Benchmark | Backbone : practice | n categories ≥ 0.02, per seed | min / total |
|---|---|---|---|
| VisA | patchcore : fixed / tuned | 11×5 / 12,12,11,12,12 | 11/12, 11/12 |
| VisA | dinomaly : fixed / tuned | 12×5 / 12,11,11,11,11 | 12/12, 11/12 |
| MPDD | patchcore : fixed / tuned | 6,6,6,6,3 / 4×5 | 3/6, 4/6 |
| MPDD | dinomaly : fixed / tuned | 6×5 / 4×5 | 6/6, 4/6 |

VisA has headroom nearly everywhere (consistent with its larger C2 excess-AURC). On MPDD
the **tuned** practice retains ≥ 0.02 headroom in only 4/6 categories (both backbones,
every seed), and patchcore:fixed drops to 3/6 in seed 4 (bracket_brown, connector,
metal_plate are zero-error there) — had a K4-style rule been preregistered for MPDD at
the same fraction, the tuned-practice cells would sit exactly at the saturation
boundary. Reported as exploratory observation only; no rule exists to trip.

---

## Limitations

- L6a sweeps the split dimension only; the permutation/bootstrap RNG seeds are held at
  the frozen values (seed = backbone seed), so the sweep isolates split sensitivity, not
  RNG sensitivity. The p-values that sit on the permutation floor (1/2001) in 173/200
  cells are floor-limited by construction — "rejects" there means "p ≤ 0.0005", as in
  the frozen analysis.
- L6b's headroom is a property of the practice's realized eval-half loss vector; a
  different practice roster (e.g. including B3/quantile, skipped for lack of a
  train-good pool) would induce different headroom numbers. The oracle is over deferral
  *orderings*, not over thresholds — it upper-bounds what any confidence ranking could
  extract from the practice's existing decisions.
- K4 is evaluated per seed on repeat-0 only (the frozen precedent); per-category
  headroom on other repeats will differ at the margin. Given the 2–3-category margin to
  the trip bar in the worst cell, the verdict is unlikely to be split-sensitive, but
  this was not swept.
- Neither analysis re-scores anything or modifies any frozen artifact; L6a consumes the
  same canonical score dumps as the frozen C2 run.

## Reproduce

```
cd reliability-commons/tools/inspect-gate
PYTHONPATH=$(pwd)/../.. .venv/bin/python c2_robustness_2026-07-19/script.py
```
(~3.5 min CPU: 200 audit cells at ~0.9 s each, plus loads.)
