# inspect-gate → Journal of Intelligent Manufacturing: highest-leverage compute plan

**Date:** 2026-07-13. **Author:** lever-inspect (strategy + feasibility research, READ-ONLY).
**Status:** run-plan only. No box booted, no `boxkit_api.py`, no ssh, no spend. The USER starts the box.
**Scope:** pick the single highest-leverage compute experiment that qualitatively raises inspect-gate
from "a 2-benchmark case study (MVTec AD + VisA, both academic)" to a certified-triage benchmark a
JIM reviewer pool cannot dismiss on industrial-realism grounds.

---

## 0. TL;DR recommendation

**Add MPDD (Metal Parts Defect Detection) as a third benchmark — both backbones, 5 seeds — replaying
the entire existing gate / V1 / audit / binding pipeline unchanged.** Then, only if the box has idle
headroom, add PatchCore-only on MPDD's harder cousin as a cheap bonus. Everything else (3rd backbone,
Real-IAD, ISP-AD, drift study) is optional and lower leverage-per-GPU-hour for *this* venue.

- **Why MPDD is the move:** it is the only candidate that directly answers JIM's #1 value —
  **real metal-parts manufacturing** — while (a) carrying a *bindable* Dinomaly reproduction target
  (published I-AUROC 97.2, and the Dinomaly repo ships an MPDD script), (b) shipping in **native
  MVTec-AD directory format** so `mvtec_layout.discover_category` and both `score_*.py` scripts run as
  a drop-in, and (c) costing ~**10–15 GPU-h ≈ $5–8** end to end. It reuses the *entire* VisA porting
  pattern already proven on 2026-07-12.
- **Contribution-class change:** "certified triage validated on two academic benchmarks" →
  "certified triage validated across academic objects (MVTec), academic multi-object (VisA), **and a
  real metal-parts manufacturing line (MPDD)**" — plus a *third* point on the G2-certifiability
  spectrum (MVTec stingy 4/15 → VisA generous 12/12 → MPDD in between) that turns the paper's
  "refusal tracks the data" thesis from a two-point claim into a demonstrated trend.
- **What it does NOT need:** no prereg re-freeze (MPDD enters as *post-freeze exploratory*, identical
  discipline to VisA), no new estimator, no new gate code.

Honest one-liner on odds: **MPDD is the difference between "reject: MVTec-only, no industrial
realism" being available to Reviewer 2 and not.** It is the load-bearing must-have. Real-IAD would be
more *impressive* but is 4–8× the cost/engineering and is a second move, not the first.

---

## 1. Recommended experiment(s) and why they change the contribution class

### 1a. PRIMARY (must-have): MPDD as a third benchmark, both backbones, 5 seeds

Run the exact protocol already frozen and used on MVTec/VisA — 5 backbone seeds, R=20 stratified
50/50 cal/eval repeats, α_miss=0.10, α_fr=0.05, primary (`--good-cal test`) protocol — on MPDD, and
regenerate every downstream artifact the paper already produces on VisA:

- reproduction gate (Dinomaly vs published 97.2; PatchCore descriptive per the no-guessed-target rule);
- seed stability; certifiability floor table (G1/G2 per category);
- V1 tier-1 per-axis; K1/K2/K3 kill-gates; median deferral;
- exploratory excess-AURC audit (B1/B2) + C2 pooled construction;
- the post-hoc binding demonstration (dataset-agnostic; replays automatically).

**Why this changes the contribution class (not marginal breadth):**

1. **It is the only move that neutralizes the venue's decisive attack.** The team's own
   `WORKLOAD-GAP-MEMO.md` grades "MVTec-only + near-ceiling" as *moderate-to-high fatality for JIM
   specifically*, because JIM "explicitly values industrial realism." VisA closed the *breadth* and
   *ceiling* half of that attack but is still an academic multi-object dataset (PCBs, macaroni,
   cashews). MPDD is **real painted-metal-parts fabrication** — brackets, connectors, metal plates,
   tubes — i.e. exactly the "metal-parts-manufacturing" substrate the memo names as landing better
   than "MVTec's academic objects." After MPDD, "you only tested on academic benchmarks" is no longer
   a true sentence a reviewer can write.

2. **It gives the "refusal tracks the data" thesis a third, intermediate data point.** Today the
   paper argues the gate's G2-certifiable count is a property of the *data*, not baked-in conservatism,
   using two extremes: MVTec (4/15 certifiable, small good pools) and VisA (12/12, large good pools).
   MPDD's per-category test-good pools sit *between* these, so its G2 count will land between — turning
   a two-point contrast into a monotone trend and making the honesty-figure argument materially
   stronger (this is the single most-cited reviewer complaint: "the gate refuses most categories").

3. **It extends the audit-headroom story onto metal parts.** Dinomaly on MPDD is 97.2 (published),
   below its 99.6 MVTec ceiling, and PatchCore on MPDD is well under its MVTec 0.982 — so the
   excess-AURC audit and the binding demo have real headroom here (as on VisA, unlike saturated
   MVTec-Dinomaly). The "does standard threshold practice earn deferral skill?" verdict gets a
   manufacturing-substrate instance.

4. **Reproduction discipline survives intact.** Unlike a dataset with no method-native published
   figure, Dinomaly *publishes* MPDD (97.2) and the repo *ships* an MPDD entry point, so the
   reproduction gate **binds** on the Dinomaly arm exactly as it does on MVTec/VisA — the paper's
   whole "no number is trusted from the literature; the gate recomputes and gate-checks it" credibility
   engine keeps running on the new benchmark. PatchCore-MPDD is descriptive, identical to the already-
   accepted PatchCore-VisA handling.

### 1b. OPTIONAL bonus (only with idle box time): a fourth, harder real-world point

If (and only if) the box is already up and cheap, PatchCore-only on **Real-IAD** (or the full
Real-IAD, see §5) adds a *modern, large-scale, real-world, multi-view* benchmark (Dinomaly published
89.3) that is the strongest possible answer to "is this deployable at scale?". This is a **second
move**, not part of the must-have — it is 4–8× the cost/engineering of MPDD and does not change
acceptance odds beyond what MPDD already secures. Detailed cost in §5.

### 1c. Explicitly NOT recommended as the primary lever (and why)

- **A 3rd backbone family (EfficientAD / RD4AD) on the same datasets.** Lower leverage for JIM: it
  answers an *architecture-breadth* objection the reviewers are not primarily making, while leaving
  the *industrial-realism* attack (their actual objection) untouched. The workload-gap memo says this
  outright: "a harder dataset (I1) answers the near-ceiling concern better than another near-ceiling
  backbone." Note also EfficientAD has *only community reimplementations* (the paper already says so),
  so it cannot anchor a binding reproduction gate; RD4AD can, but still doesn't touch realism. Keep as
  a future "architecture generality" strengthener, not the load-bearing experiment.
- **Threshold-transfer / temporal-drift study.** Genuinely the best *deployment* story, but MVTec,
  VisA, and MPDD have **no temporal split** to calibrate-then-evaluate across, so it needs data we do
  not have. Only Real-IAD (multi-view could proxy a domain shift) or ISP-AD (real-vs-synthetic split)
  could stand in, and both are heavier. Leave as stated future work — the paper already frames it
  that way in Limitations.
- **ISP-AD (JIM's own 2025 dataset).** Maximal venue alignment on paper, but 559k samples (mostly
  *synthetic* defects; only 711 real), no Dinomaly/PatchCore method-native published figure → the
  reproduction gate cannot bind (descriptive-only on both backbones), and the scale is a poor
  cost/return trade. Cite it in Related Work as the venue's own realism benchmark and as future work;
  do not spend compute on it now.

---

## 2. Datasets: exact sourcing, verified this pass

### MPDD — RECOMMENDED (primary)

| Field | Value |
|---|---|
| Content | 6 real metal-part categories: **bracket_black, bracket_brown, bracket_white, connector, metal_plate, tubes** |
| Counts | ~1,346 images: **888 train-good**, **458 test** (good + anomalous), pixel-precise masks |
| Size | **1.65 GB** |
| Format | **Native MVTec-AD layout** — per-category `train/good/`, `test/good/`, `test/<defect_type>/`, `ground_truth/<defect_type>/` (confirmed via multiple sources). `mvtec_layout.discover_category` works with zero changes. |
| Official source | `github.com/stepanje/MPDD` — download is a **SharePoint link (authenticated)**; the LICENSE file exists in-repo (dataset is for academic/research use; originating paper is the 2021 ICUMT "Deep learning-based defect detection of metal parts"). |
| Credential-free mirrors | **HyperAI** `hyper.ai/en/datasets/31541` provides an **MPDD.torrent** (1.65 GB) — credential-free via torrent, and China-friendly for the AutoDL box. HuggingFace `chasonfff/MPDD-AVG-2026` is a *gated challenge variant* (not the original — do NOT use for reproduction). |
| autodl-pub mirror? | **NO** — the 2026-07-10 map lists only `mvtec_anomaly_detection.tar.xz`. MPDD must be staged. At 1.65 GB this is trivial (see §6). |

**Recommended acquisition:** download once **locally** (torrent from HyperAI, or the SharePoint link
in a browser), verify a sha256, confirm the 6-category MVTec structure and the 888/458 counts, then
push to the user's own HuggingFace bucket (`PeterPonyu`) so the box pulls it credential-free and fast
(same trick used to dodge the figshare/CN-blocking class of failures). Never rely on the box
downloading from SharePoint.

### Real-IAD — OPTIONAL flagship (second move)

| Field | Value |
|---|---|
| Content | 30 real industrial-object categories, multi-view (5 cameras), real-world defects |
| Counts / size | ~150k images. HuggingFace files: **`realiad_1024` ≈ 53 GB** (1024px — the usable size), `realiad_raw` ≈ 507 GB (do not pull), `realiad_jsons.zip` (splits) |
| Access | **HuggingFace `Real-IAD/Real-IAD`**, research-use; **access request is auto-approved** on request (no manual form for the base dataset; the D³ variant wants a college-email account). Anomalib ships a `RealIAD` datamodule. |
| Reproduction | Dinomaly publishes **89.3** I-AUROC (uni) and the repo ships `dinomaly_realiad_uni.py` → bindable. Lower ceiling → audit very informative. |
| autodl-pub mirror? | NO. 53 GB download is the main staging cost. |

### BTAD, ISP-AD — considered, set aside

- **BTAD** (`dataset-ninja/btad`, 2,830 imgs, 3 products, real industrial): Dinomaly publishes 95.4
  **but the repo ships no BTAD script** → Dinomaly-BTAD would be descriptive (weaker), and it is *not*
  metal-parts, so it is strictly dominated by MPDD for the JIM attack. Skip.
- **ISP-AD** (`arxiv 2503.04997`, JIM 2025, 559k samples, mostly synthetic): venue-native but
  no method-native reproduction target and poor scale/return. Cite, don't run. Skip.

---

## 3. Models and where the weights come from

Both backbones are **reproduced, not improved** — identical to the MVTec/VisA arms. No new weights.

- **PatchCore** via **anomalib** (Apache-2.0), `wide_resnet50_2`, layers `layer2,layer3`, coreset
  ratio 0.10 — feature extractor is ImageNet-pretrained WRN50 (downloaded by anomalib/timm on first
  use; already cached on the box from the MVTec/VisA runs). **No training**; per-category memory bank
  built from MPDD `train/good`. Coreset-subsampling seed = the only variance source (seeds 0–4).
- **Dinomaly** (`github.com/guojiajeremy/Dinomaly`, Apache-2.0), DINOv2-base encoder (weights pulled
  by the repo; already cached from MVTec/VisA). Trained per seed (`DINOMALY_SEED`), 10,000 iters
  (`DINOMALY_ITERS`) via the existing `dinomaly_patch.py` P1–P5 patches. **Setting — RESOLVED this
  pass:** Dinomaly's published **MPDD 97.2 is the multi-class (MUAD/unified) number** (verified: the
  Dinomaly paper is titled "…Multi-Class Unsupervised Anomaly Detection" and reports 97.2 in the
  multi-class benchmark; a 2025 follow-up "Dinomaly2" reports 99.0 on MPDD in the same multi-class
  setting). So run the **uni (multi-class) setting** — it is *both* the reproduction-correct target
  *and* the cheaper path (~6 GPU-h vs ~15–30 for sep), and it matches the paper's existing
  Dinomaly-on-VisA multi-class treatment. Implement by porting `dinomaly_visa_uni.py` to a 6-class MPDD
  roster (the same small, proven edit made for VisA). The repo *ships* only `dinomaly_mpdd_sep.py`, but
  the uni training loop is dataset-agnostic given a roster + data paths, so the port is direct. (The
  sep script remains a fallback only if a Phase-0 smoke of the uni port fails to approach 97.2.)

---

## 4. Run pipeline — what code exists vs what needs writing

The 2026-07-12 VisA port is the exact template; MPDD is *easier* because it is already MVTec-format
(VisA needed the JPEG-as-PNG symlink dance; MPDD does not).

### Exists and reused UNCHANGED
- `inspect_gate/{gate,certify,audit,baselines,io,reproduction,report}.py` and `cli.py`
  (`calibrate` / `route` / `audit` / `certify` / `report`) — fully dataset-agnostic; consume canonical
  scores-JSONL.
- `orchestration/mvtec_layout.py::discover_category` — works on MPDD's MVTec layout directly (only a
  new category roster constant is needed).
- `orchestration/score_patchcore.py` — runs on MPDD as-is (anomalib on the per-category layout; point
  `--data-root` at staged MPDD, `--category` at the 6 MPDD classes). No holdout arm needed for MPDD.
- `orchestration/score_dinomaly.py --mode dump-ingest` — ingests the Dinomaly score dumps as-is.
- `orchestration/dinomaly_patch.py` — P1–P5 (env seed/iters, cuda:0, per-image score dump, pandas
  shim) reused; re-point the anchor target at the MPDD-uni script.
- `binding_demo_2026-07-13/run_binding_demo.py`, `c2_tier2_2026-07-13/*`, `b3_*` — dataset-agnostic;
  rerun pointed at MPDD canonical scores.

### Needs writing (all small, all mirror an existing VisA-era file)
1. **`orchestration/mpdd_layout.py`** (or just a `MPDD_CATEGORIES` constant added to `mvtec_layout.py`)
   — the 6-category roster. ~10 lines.
2. **`orchestration/mpdd_prep.py`** — clone of `visa_prep.py`, but likely a near-no-op: if the staged
   MPDD is already MVTec-format, this just *verifies* structure + counts (888 train-good, 458 test per
   the official split) and refuses on mismatch, rather than rebuilding a layout. ~40 lines.
3. **`dinomaly_mpdd_uni.py`** — port of `dinomaly_visa_uni.py` to the 6-class MPDD roster/paths (the
   same edit made for VisA). ~1 small file + one anchor update in `dinomaly_patch.py`.
4. **`mpdd_results_2026-07-1x/scripts/mpdd_adapter.py`** — clone of `visa_adapter.py`: parse Dinomaly
   MPDD score dumps + PatchCore JSONL → canonical scores-JSONL, with the same **AUROC cross-check vs
   the box's own `log.txt`** (proves label-join + sign convention) and **count-refuse vs the official
   MPDD split**. ~200 lines, mechanical.
5. **`mpdd_results_2026-07-1x/scripts/run_mpdd_analysis.py`** — clone of `run_visa_analysis.py`:
   reproduction → seed-stability → floor table → gate calibrate/route/certify (V1, K1/K2) → audit →
   emit `SUMMARY.json`. Dataset-agnostic body; only the roster + published-target (97.2) change.
6. **Paper edits** (post-box): extend `MVTEC-VS-VISA.md` → a 3-benchmark table; add MPDD to §Setup
   (data), a short MPDD results paragraph (reproduction + floors + V1 + audit), and one sentence in
   Limitations noting MPDD is post-freeze exploratory (identical to VisA's status). Update the abstract's
   "two ... benchmarks" → three, and the metal-parts realism claim in the intro.
7. **Unit tests**: extend `tests/test_mvtec_layout.py`-style coverage for the MPDD roster/prep (torch-
   free, local).

### Prereg / freeze status
MPDD is **post-freeze exploratory**, reported exactly as VisA is (the 2026-07-11 freeze does not
mention it; it runs under the identical frozen protocol and code path, never counted in the
confirmatory Holm family). **No re-freeze, no new sign-off required.** State this explicitly in the
manuscript to preempt a "moving the goalposts" objection.

---

## 5. GPU-hours, wall-clock, cost (assume ~$0.5/GPU-h, 4090-48G)

Dinomaly unified training measured at **~73 min/seed** on the 2026-07-12 VisA box (seed logs spaced
05:58→07:11→08:25→09:38→10:51; 8,659 train imgs, 10k iters). Iters are fixed, so MPDD (fewer images)
is **≤** that per seed. PatchCore has no training (feature extract + coreset only).

### PRIMARY: MPDD, both backbones, 5 seeds (Dinomaly **uni**)
| Component | Per-unit | Total |
|---|---|---|
| Dinomaly-MPDD uni training + score dump | ~1.0–1.2 GPU-h/seed | 5 seeds → **~5–6 GPU-h** |
| PatchCore-MPDD fit+score (6 cat × 5 seeds, small imgs) | ~0.15–0.35 GPU-h/cell | 30 cells → **~5–10 GPU-h** (realistically ~4–6) |
| Reproduction smoke + reruns buffer | — | **~2–3 GPU-h** |
| **Total** | | **~12–18 GPU-h** |

- **Wall-clock:** Dinomaly seeds serial ≈ 6 h; PatchCore ≈ 3–6 h → **~0.5–1 day** on one 4090-48G
  (less if Dinomaly seeds and PatchCore run on two rented instances in parallel).
- **Cost:** **~$6–9** compute + a few $ of box uptime ≈ **under $15 all-in.** Effectively free.

**Contingency — only if the uni port's Phase-0 smoke fails to approach 97.2 and *sep* is needed
(6 models/seed):** 6 cat × 5 seeds = 30 training runs. At ~0.4–1.0 GPU-h each (sep single-category
runs are shorter than a full uni run) → **~12–30 GPU-h** for the Dinomaly arm alone; total **~20–40
GPU-h ≈ $10–20**, wall-clock ~1–1.5 days. Still cheap. Uni is confirmed the reproduction-correct
target (§3), so this branch is a fallback, not the expected path.

### OPTIONAL: Real-IAD flagship (for reference, if pursued later)
- Download **53 GB** (`realiad_1024`) — hours, one-time. Dinomaly uni 5×~1.5 h ≈ **~8 GPU-h**;
  PatchCore over **30 categories** × 5 seeds at 1024px ≈ **~30–75 GPU-h** (the dominant cost).
- **Total ~40–85 GPU-h ≈ $20–45**, wall-clock **~3–5 days**, plus multi-view adapter engineering.
  → A deliberate second campaign, not bundled with the must-have.

---

## 6. What LOCAL prep can be staged NOW (no box, no spend)

All of this is doable today on the workstation and removes every box-side unknown before a single
GPU-hour is spent:

1. **Acquire + verify MPDD (1.65 GB).** Download locally (HyperAI torrent, or the stepanje/MPDD
   SharePoint link via browser). Compute + record a **sha256**; verify the 6-category MVTec structure
   and the **888 train-good / 458 test** counts; write a `DATA_MANIFEST` entry ("source: HyperAI
   mirror / stepanje SharePoint; sha256=…"). Confirm the license text from the in-repo LICENSE for the
   manuscript's data-availability statement.
2. **Push MPDD to the user's HuggingFace bucket** (`PeterPonyu`) so the box pulls it credential-free
   and China-fast — avoids the SharePoint-on-box failure mode entirely.
3. **Write and unit-test the torch-free code now:** `MPDD_CATEGORIES` roster, `mpdd_prep.py`
   (structure/count verifier), `mpdd_adapter.py` (schema adapter + AUROC xcheck + count-refuse),
   `run_mpdd_analysis.py` (clone of `run_visa_analysis.py`), and the `dinomaly_mpdd_uni.py` port. All
   the non-GPU logic (layout discovery, schema validation, floor arithmetic, gate/certify/audit) is
   exercisable locally against a handful of dummy scores — exactly as the VisA scripts were.
4. **Precompute the MPDD certifiability-floor table locally (zero GPU).** The G1/G2 α_min floors are a
   deterministic function of the per-category test-good/test-defect counts (round-half-to-even of n/2).
   Deriving the predicted G2-certifiable count for MPDD *before* any box run both de-risks the run and
   gives the paper's honesty-figure prediction to check against — the same pipeline-correctness check
   the paper already runs on MVTec.
5. **Draft the manuscript hooks** (table skeletons, the 3-benchmark `MVTEC-VS-VISA` extension, the
   post-freeze-exploratory sentence) so that when the box scores land, integration is a fill-in, not a
   rewrite.

After steps 1–5, the box session is purely: pull MPDD from the HF bucket → apply `dinomaly_patch.py` →
run 5 Dinomaly-uni seeds + PatchCore 6×5 → pull dumps → `mpdd_adapter.py` → `run_mpdd_analysis.py` →
done. One short, cheap, fully-scripted session.

---

## 7. Honest scorecard: what actually changes acceptance odds

| Experiment | Answers JIM's real objection? | Reproduction binds? | Cost | Verdict |
|---|---|---|---|---|
| **MPDD, both backbones, 5 seeds** | **Yes — metal-parts realism, the #1 axis** | Yes (Dinomaly 97.2) | ~12–18 GPU-h / ~$8 | **MUST-HAVE (the lever)** |
| Real-IAD (full) | Yes — real-world scale/multi-view | Yes (Dinomaly 89.3) | ~40–85 GPU-h / ~$30 | Optional flagship, second move |
| 3rd backbone (RD4AD) on existing data | No — wrong objection | Yes | ~10–20 GPU-h | Optional, low JIM leverage |
| EfficientAD | No | **No** (community-only impl) | — | Skip as certified arm |
| Threshold-transfer / drift | Best deployment story, but no temporal data | — | needs data we lack | Future work |
| ISP-AD | Venue-native, but no bindable target, huge | **No** | very high | Cite, don't run |

**Bottom line:** run **MPDD** now — it is cheap, it is a clean drop-in on the existing harness, it
carries a bindable reproduction target, and it is the single experiment that converts the paper from
"academic-benchmarks-only" (a true, fatal-for-JIM sentence today) into a certified-triage method
demonstrated on a real metal-parts manufacturing line. Hold Real-IAD as a deliberate, separately-
budgeted second campaign if a reviewer pushes for scale.
