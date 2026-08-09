# MPDD certifiability-floor PREDICTION (pre-box, zero GPU)

Protocol: primary (good-cal=test), Mondrian per-category, repeat-0 split; alpha_miss=0.1, alpha_fr=0.05.

**Predicted G2-certifiable: 0/6** (G1-certifiable: 5/6).

| category | n_test_good | n_test_defect | n_cal_good | n_cal_defect | alpha_min_g1 | alpha_min_g2 | G1 cert | G2 cert |
|---|---|---|---|---|---|---|---|---|
| bracket_black | 32 | 47 | 16 | 24 | 0.0400 | 0.0588 | Y | n |
| bracket_brown | 26 | 51 | 13 | 26 | 0.0370 | 0.0714 | Y | n |
| bracket_white | 30 | 30 | 15 | 15 | 0.0625 | 0.0625 | Y | n |
| connector | 30 | 14 | 15 | 7 | 0.1250 | 0.0625 | n | n |
| metal_plate | 26 | 71 | 13 | 36 | 0.0270 | 0.0714 | Y | n |
| tubes | 32 | 69 | 16 | 34 | 0.0286 | 0.0588 | Y | n |

Certifiable ⇔ alpha_min ≤ target (G1: n_cal_defect ≥ 9 at 0.10; G2: n_cal_good ≥ 19 at 0.05). Floors are count-only, so these equal the box's repeat-0 floors bit-for-bit.
