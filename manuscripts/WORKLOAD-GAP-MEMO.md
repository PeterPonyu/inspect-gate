# Workload-gap memo — inspect-gate vs Journal of Intelligent Manufacturing (JIM)

Date: 2026-07-11. Purpose: audit the gap between the current inspect-gate substrate and the
empirical norm a JIM reviewer pool (manufacturing / industrial-AI, values industrial realism)
expects. No experiments run; no paper edited.

## 1. Current empirical inventory (skeleton + analysis_2026-07-10)

- **Task/data:** MVTec AD only (15 categories, 1,725 test images).
- **Backbones:** 2 (PatchCore, Dinomaly), both reproduction-gated, 5 seeds each.
- **Certified gate:** G1 (escaped-defect) certifiable 15/15; G2 (false-reject) 4/15 under the
  primary protocol; V1 tier-1 150/150 cells pass; K1/K2 not tripped.
- **Audit:** exploratory excess-AURC (PatchCore 10/30 reject; Dinomaly 0/30 — a **ceiling effect**
  from near-saturated per-category AUROC).
- **Gated (prereg freeze):** G2 train-holdout promotion (already computed), A1–A3 tier-2 verdicts,
  B3 practice, C2 confirmatory pooled Holm family.
- **Rigor:** 5 seeds, R=20 stratified splits, bootstrap CIs, preregistered kill-gates — matches the
  "reproducible and statistically-rigorous" bar of recent JIM benchmarking work.

## 2. JIM empirical norm for inspection / AD papers

Evidence from recent JIM and adjacent venues (see Sources):
- **Multi-dataset is the norm.** Current industrial-AD work runs on **MVTec-AD + VisA + MPDD**
  (often + BTAD); MVTec-only reads as under-powered to this pool. VisA (10,821 imgs), BTAD (2,830,
  3 products), MPDD (1,346, 6 metal-part categories) are the standard companions.
- **JIM prizes industrial realism.** JIM 2025 introduced **ISP-AD**, a large-scale *real-world*
  dataset with synthetic + real defects (10.1007/s10845-025-02778-z); MPDD is explicitly
  metal-parts-manufacturing. A real-line or metal-parts dataset lands better than MVTec's academic
  objects.
- **Inference latency / real-time efficiency** recurs as an evaluation axis (lightweight-device
  defect detection, JIM 10.1007/s10845-024-02487-z) — practicality tables are expected.
- **Statistical rigor** is now a JIM value (the reproducible-benchmarking paper
  10.1007/s10845-025-02672-8) — here we are already strong.

**Read:** our rigor and certificate machinery **meet or exceed** JIM norms; the deficits are
**dataset breadth + industrial realism** and a **latency/practicality table**.

## 3. Gap list

| # | Item | Cost | Tier | Notes / gating |
|---|---|---|---|---|
| I1 | **Second benchmark — VisA or MPDD** — re-score both backbones (5 seeds) + re-run the gate/V1/audit on one more dataset | GPU: PatchCore scoring cheap (mins/cat); **Dinomaly per-category training is the cost** — MPDD (6 cat) ≈ ~40% of MVTec's train budget, VisA (12 cat) ≈ ~80%. Rough order **10–40 GPU-h** for one dataset, both backbones, 5 seeds | **MUST-HAVE** | Directly answers the "MVTec-only" attack. Prefer **VisA** (lower per-category AUROC ceiling → the excess-AURC audit and Dinomaly arm become *informative*, fixing the ceiling effect) or **MPDD** (metal-parts realism, cheaper). Bonus: a lower-ceiling dataset makes the audit's constructive/debunking verdict actually testable |
| I2 | **G2 train-holdout promotion arm** — lifts G2 certifiable from 4/15 toward ~14/15 | **ZERO new compute** (already computed); needs the KS-gate run + A1–A3 / prereg **freeze sign-off** | **STRENGTHENER (gated)** | Highest value-per-cost: turns "the gate refuses 11/15 categories for false-reject" into "certifies almost everywhere," the single most likely reviewer complaint — but gated on the user freeze, not on compute |
| I3 | **Inference-latency / runtime table** — end-to-end per-image latency (backbone + gate) on a named device | CPU/GPU timing; **hours** | **MUST-HAVE** | JIM practicality expectation; the gate itself is O(sort)/negligible, so this is cheap and reframes the method as deployable |
| I4 | **Third backbone family** (e.g. a reverse-distillation or EfficientAD-class model) | GPU: train/score, ~10–20 GPU-h | **OPTIONAL** | Architecture breadth; but a *harder dataset* (I1) answers the near-ceiling concern better than another near-ceiling backbone |
| I5 | **Threshold-transfer / drift study** — calibrate on one production period, evaluate on a later one (exchangeability drift) | Needs temporally-split data; GPU + design | **OPTIONAL** | Strong JIM-realism angle but requires data we do not have; future work |

## 4. Reviewer-2 attack surface (JIM pool): "MVTec-only + near-ceiling backbones"

**Fatality: moderate-to-high for JIM specifically.** JIM explicitly values industrial realism and
generalization, so a single academic benchmark is the most likely rejection axis. Two compounding
issues: (a) MVTec-only limits the industrial-realism claim; (b) near-ceiling backbones make the
excess-AURC audit *uninformative* on Dinomaly (0/30 is a ceiling artifact, not a finding). **Both
are fixed by the same move: a second, lower-ceiling and/or metal-parts dataset (I1).** A latency
table (I3) neutralizes the "is this deployable?" follow-up. Unlocking G2-promotion (I2) removes the
"refuses most categories" complaint at zero compute. With I1 + I2 + I3 the paper is well-defended
for JIM; without I1 it is exposed.

Secondary attacks and status: "certificate refuses 11/15 categories" → I2 (gated, computed);
"statistical rigor?" → already strong; "why should I trust the reproduction?" → reproduction gate
+ seed stability already answer it.

## 5. Recommendation

**I1 (second benchmark) is the load-bearing MUST-HAVE** — pick **VisA** if the goal is to make the
audit informative and answer the ceiling attack, or **MPDD** for cheaper metal-parts realism; both
answer the MVTec-only objection. Pair with **I3 (latency table, cheap)** and unlock **I2
(G2-promotion, zero compute, needs freeze)**. That trio converts the current MVTec-only skeleton
into a JIM-defensible submission. I4/I5 are optional. Note the sequencing dependency: I2 and the
confirmatory arms are already blocked on the A1–A3 prereg freeze (user-attended), so the freeze is
on the critical path regardless of the dataset work.

## Sources
- JIM reproducible/statistically-rigorous defect benchmarking: https://link.springer.com/article/10.1007/s10845-025-02672-8
- ISP-AD large-scale real-world AD dataset (JIM 2025): https://link.springer.com/article/10.1007/s10845-025-02778-z
- Lightweight-device defect detection (JIM, latency focus): https://link.springer.com/article/10.1007/s10845-024-02487-z
- Survey of deep learning for industrial visual anomaly detection: https://link.springer.com/article/10.1007/s10462-025-11287-7
- Awesome industrial anomaly detection (dataset roster): https://github.com/m-3lab/awesome-industrial-anomaly-detection
