# MPDD train-holdout G2 rescue arm — RESULTS

**Date:** 2026-07-14. **Backbone:** PatchCore only (Dinomaly has no train-side score
dump). **Substrate:** `mpdd_pulled_2026-07-14/patchcore_holdout/seed_{0..4}/` (test rows +
20%-of-train-good holdout pool, `--holdout-frac 0.2 --holdout-seed 0`; holdout ids match the
`.holdout_provenance.json` sidecars, identical across seeds). **Producer:**
`mpdd_results_2026-07-13/scripts/run_mpdd_holdout_analysis.py` (mirrors the signed MVTec
promotion arm `g2_promotion_2026-07-12/run_g2_promotion.py`; the KS gate + fallback are the
VERBATIM `gate.calibrate_gate` library path, the only change from the primary pass being the
two `good_cal_holdout*` kwargs). Machine-readable: `HOLDOUT-RESULTS.json`.

**Status / discipline:** MPDD is **post-freeze exploratory** (identical to VisA; never in the
confirmatory Holm family), and the train-holdout arm is additionally a **flag-gated,
prereg-NEUTRAL protocol variant** (`--good-cal train-holdout`, design §3.2). It re-freezes
nothing.

---

## HEADLINE

**G2 certifiable with train-holdout calibration: 4/6 categories (vs 0/6 primary); floor
predicted 5/6.** Stable across all 5 seeds (identical certify/refuse decisions every seed;
0 `n_cal_good`-count mismatches). The train-holdout arm turns the primary protocol's **0/6**
into **4/6** — a large rescue — but lands **one below** the count-only floor prediction of
5/6 because the **KS exchangeability gate rejects `tubes`** (train-good vs test-good scores
are strongly non-exchangeable, BH-adjusted p ≈ 1.2e-05), exactly the risk
`FLOOR-PREDICTION.md` flagged ("MPDD's non-homogeneous backgrounds … some categories may
KS-fail → `audited-not-certified`"). The remaining refusal is `metal_plate`, whose holdout
pool (11) is below the certifiability floor (needs ≥ 19).

So the honest one-line contrast is: **primary 0/6 → train-holdout 4/6** (5/6 clears the
count floor; the KS gate audits `tubes` out, leaving 4 genuinely certified).

---

## Per-category table (seed 0 representative; certify/refuse decisions identical for all 5 seeds)

| category | n_holdout_good | KS stat | KS p_bh (BH, α=0.05) | KS pass | G2 mode | G2 certified | reason |
|---|---|---|---|---|---|---|---|
| bracket_black | 58 | 0.287 | 0.62 | Y | train-holdout | **Y** | KS passed, pool 58 ≥ 19 |
| bracket_brown | 37 | 0.154 | 0.94 | Y | train-holdout | **Y** | KS passed, pool 37 ≥ 19 |
| bracket_white | 22 | 0.173 | 0.94 | Y | train-holdout | **Y** | KS passed, pool 22 ≥ 19 |
| connector | 26 | 0.282 | 0.71 | Y | train-holdout | **Y** | KS passed, pool 26 ≥ 19 |
| metal_plate | 11 | 0.287 | 0.91 | Y | train-holdout | n | KS passed but pool 11 < 19 (floor 1/12 = 0.083 > 0.05) |
| tubes | 24 | 0.792 | 1.2e-05 | **N** | audited-not-certified | n | KS **failed** → audited-not-certified (no promotion) |

- **G1 (escaped-defect) is unaffected by this arm** (design §2.3): G1 stays 5/6 — only
  `connector` fails G1 (14 test-defect → n_cal_defect 7 < 9), exactly as in the primary pass.
  Note `connector` is thus **G1-refused but G2-certified** under train-holdout.
- The `n_holdout_good` column is the **raw** 20%-train-good pool size. For `tubes` the KS
  failure makes G2 fall back to the test-good calibration half, so `floors["tubes"].n_cal_good`
  in the JSON reads 16 (the fallback pool), not 24 — the raw pool is recorded in
  `summary.holdout_pool_good_sizes`.

### KS gate stability across seeds

The KS decision is rock-stable: `tubes` fails every seed (p_bh ∈ [1.2e-05, 6.2e-05],
KS statistic ∈ [0.75, 0.79]); every other category passes every seed with a large margin
(p_bh ≥ 0.435 throughout). The gate is not living on a knife-edge — `tubes` is a decisive
non-exchangeability, the other five are decisively exchangeable.

---

## Sanity block (no gate): holdout-arm test scores vs primary-arm test scores

The holdout arm re-scores the test rows with a memory bank fit on **80%** of train-good; the
primary arm uses **100%**. The scores are therefore NOT identical — but they are the same
ranking of the same images (same model, smaller bank), reported here only as a consistency
check, with no gate attached.

| statistic | value (across all 6 cats × 5 seeds) |
|---|---|
| min per-category Spearman ρ (holdout-arm vs primary-arm test scores) | **0.9186** (connector, seed 0) |
| max \|per-category image-AUROC delta\| | **0.0399** (bracket_black, seed 0) |

Per-category means (across seeds): Spearman ρ ranges 0.92–0.99; image-AUROC deltas are within
±0.04 everywhere and near zero for `bracket_brown`/`metal_plate` (already saturated at 1.0).
This confirms the holdout arm scored the same model, not a different one — the 80%-bank
re-scoring perturbs magnitudes slightly but preserves the ranking.

---

## Honest caveats

1. **Post-freeze exploratory, PatchCore-only.** Same discipline as VisA; never in the
   confirmatory Holm family. Dinomaly is absent (no train-side score dump), so this is a
   single-backbone result.
2. **Flag-gated, prereg-NEUTRAL protocol variant.** The `--good-cal train-holdout` arm was
   pre-specified as a calibration-efficiency lever (design §3.2); running it changes nothing
   about the frozen primary protocol or its 0/6 result.
3. **4/6, not 5/6.** The count-only floor clears for 5/6, but the KS exchangeability gate —
   a real, pre-specified guardrail — audits `tubes` out. This is the gate working as
   designed, not a shortfall: promoting `tubes` would have certified a category whose
   train-good and test-good score distributions demonstrably differ (p_bh ≈ 1e-05).
4. **The contrast, not the level, is the result.** 0/6 → 4/6 on the *same benchmark, same
   scores* is the strongest single demonstration of the calibration-efficiency lever: the
   certificate count is a property of how much exchangeable good-data the protocol can spend,
   and the KS gate keeps the rescue honest.
