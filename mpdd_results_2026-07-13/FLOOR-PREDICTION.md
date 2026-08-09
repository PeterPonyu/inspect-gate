# MPDD certifiability-floor PREDICTION (pre-box, zero GPU)

**Date:** 2026-07-13. **Author:** t1-inspect (Tier-1 local, no box, no spend).
**Inputs:** authentic per-category MPDD counts read from the ZIP central directory of the
public mirror `meksamiao/mpdd` (totals reproduce the documented 888 train-good / 458 test =
176 normal + 282 defect; ground-truth masks match defect counts). Floors computed by driving
the REAL `splits.stratified_cal_eval_split` + `gate.calibrate_gate` code path on synthetic
records carrying MPDD's counts — floors are count-only, so this equals the box's repeat-0
floors bit-for-bit. Machine-readable primary-protocol table: `floor_prediction.json`;
auto-generated primary table: `FLOOR-PREDICTION-primary.md`.

---

## HEADLINE (the number the team-lead flagged the trend claim hinges on)

**MPDD predicts 0/6 G2-certifiable at the frozen primary protocol** (good-cal=test,
α_fr=0.05). G1 (escaped-defect, α_miss=0.10) is healthy at **5/6**.

The plan's hypothesis — "MPDD lands *between* MVTec 4/15 and VisA 12/12, making a monotone
trend" — is **REFUTED in ordering but CONFIRMED in mechanism.** MPDD's per-category test-good
pools are uniformly small (26–32 images → n_cal_good 13–16, all below the 19 needed at
α_fr=0.05), so MPDD is the **stingiest** anchor, not the middle:

| benchmark | G2-certifiable (primary, good-cal=test) | test-good pool sizes | protocol |
|---|---|---|---|
| **MPDD** | **0/6** | small, uniform (26–32 → n_cal 13–16) | good-cal=test, α_fr=0.05, 50/50 |
| MVTec | 4/15 (cable, hazelnut, screw, transistor) | mixed (only 4 reach n_cal ≥ 19) | identical |
| VisA | 12/12 | large (50–100 → n_cal 25–50) | identical |

All three verified apples-to-apples from the frozen floor records in-repo
(`analysis_2026-07-10/` and `visa_results_2026-07-12/` gate_calibration seed-0 floors). The
corrected trend, ordered by test-good pool size, is **MPDD 0/6 → MVTec 4/15 → VisA 12/12** —
still monotone, still "refusal tracks the data," but MPDD sits *below* MVTec.

**Why this STRENGTHENS the core thesis while flipping the plan's narrative:** the thesis is
that the G2-certifiable count is a property of the *data* (good-pool size), not baked-in
conservatism. MPDD's uniformly small good pools → 0 certificates is the cleanest possible
demonstration: the gate refuses precisely because 5%-false-reject certification is
information-theoretically unsupported by ≤16 calibration goods. The manuscript hook must change
from "MPDD is the intermediate point" to "MPDD is the stingy extreme that proves the gate
refuses when the data can't pay for a certificate."

---

## Per-category floor table (primary protocol, good-cal=test)

| category | n_test_good | n_test_defect | n_cal_good | n_cal_defect | α_min_g1 | α_min_g2 | G1 cert | G2 cert |
|---|---|---|---|---|---|---|---|---|
| bracket_black | 32 | 47 | 16 | 24 | 0.0400 | 0.0588 | Y | n |
| bracket_brown | 26 | 51 | 13 | 26 | 0.0370 | 0.0714 | Y | n |
| bracket_white | 30 | 30 | 15 | 15 | 0.0625 | 0.0625 | Y | n |
| connector | 30 | 14 | 15 | 7 | 0.1250 | 0.0625 | **n** | n |
| metal_plate | 26 | 71 | 13 | 36 | 0.0270 | 0.0714 | Y | n |
| tubes | 32 | 69 | 16 | 34 | 0.0286 | 0.0588 | Y | n |

- **G2 = 0/6:** the max n_cal_good is 16 (bracket_black, tubes); the floor needs ≥ 19, i.e. a
  test-good pool ≥ 38. MPDD's largest is 32. Robust — not a rounding-edge artifact (margin ≥ 3).
- **G1 = 5/6:** only `connector` fails (14 test-defect → n_cal_defect 7 < 9). Escaped-defect
  certification is well-supported on MPDD.

## Constructive counter-story: the train-holdout arm (good-cal=train-holdout)

MPDD's *train*-good pools are LARGE (54–289 per category), unlike its test-good pools. Under the
design's `--good-cal train-holdout` arm, G2 calibrates on a 20% train-good holdout instead of
the tiny test-good half. The G2 certifiability **FLOOR** (n_holdout_good ≥ 19) is then satisfied
for **5/6** categories (code-confirmed via `train_good_holdout_split` + `calibrate_gate`):

| category | n_train_good | n_holdout_good (20%) | G2 floor (≥19) |
|---|---|---|---|
| bracket_black | 289 | 58 | Y |
| bracket_brown | 185 | 37 | Y |
| bracket_white | 110 | 22 | Y |
| connector | 128 | 26 | Y |
| metal_plate | 54 | 11 | **n** |
| tubes | 122 | 24 | Y |

**Caveat (needs box):** clearing the floor is necessary but not sufficient — each category must
also pass the per-category **KS exchangeability gate** (train-good vs test-good), which requires
the real box scores. MPDD's "non-homogeneous backgrounds, diverse orientations/lighting" make
this a genuine risk (some categories may KS-fail → `audited-not-certified`). So the honest
statement is: **train-holdout could rescue up to 5/6 G2 certificates that the primary protocol
refuses (0/6), subject to KS** — a vivid instance of the calibration-efficiency lever the design
already studies. The primary protocol (0/6) is what the plan scoped; the train-holdout arm is
out-of-scope-but-decision-relevant and cheap to add on the same box run.

---

## Implications for the run decision (for team-lead)

1. The **industrial-realism** rationale for MPDD (metal parts → neutralizes "academic-only")
   is untouched — that was always the #1 reason and it still holds.
2. The **trend** argument survives but must be re-narrated: MPDD is the *stingy* extreme
   (0/6), not the middle. This is a cleaner honesty-figure story, not a weaker one.
3. **Reviewer risk:** "0/6 certified at primary → the gate is useless on MPDD." Mitigations
   are real and should be pre-loaded into the manuscript: (a) G1 is 5/6 (escaped-defect works);
   (b) the train-holdout arm clears the G2 floor for 5/6 (KS-gated) — lead with those numbers
   for the "usable certificate" story; (c) 0/6 is the *honest, thesis-confirming* behavior.
4. **Cheap add worth considering:** run the `--good-cal train-holdout` arm on MPDD alongside
   primary (no extra GPU — reuses the same scores) so the paper can show 0/6 → up-to-5/6 on the
   same benchmark. This turns the 0/6 surprise from a liability into the headline honesty result.

## Reproduce

```
python3 mpdd_results_2026-07-13/scripts/mpdd_floor_table.py \
  --counts mpdd_staging/mpdd_counts_from_zipCD.json \
  --out-json mpdd_results_2026-07-13/floor_prediction.json \
  --out-md   mpdd_results_2026-07-13/FLOOR-PREDICTION-primary.md
```
