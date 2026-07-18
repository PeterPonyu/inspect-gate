# inspect-gate data manifest

## Source

MVTec AD (Bergmann et al., CVPR 2019): 15 categories, 3,629 defect-free
training images, 1,725 test images (mixed good + defective), 73 defect
types, pixel-level ground truth (unused by this package -- inspect-gate
is image-level only, design §2.2).

**Staged copy (this portfolio's convention, per
`SOTA-REPRODUCTION-PLAN-2026-07-10.md` §5): the `/root/autodl-pub` mirror,
`mvtec_anomaly_detection.tar.xz` (~5.3GB), zero download cost per
container.** Override via `AUTODL_PUB_MVTEC_PATH` (default
`/root/autodl-pub/mvtec_anomaly_detection.tar.xz`); extraction target via
`INSPECT_GATE_DATA_ROOT` (default `/root/autodl-tmp/mvtec_anomaly_detection`,
the DATA disk, never the system disk -- standing portfolio rule).

## Checksum-at-Phase-0 convention

`orchestration/phase0.py`'s `stage_tarball()` computes and records the
tarball's SHA256 into `phase0_staging.json`'s `staging.tarball_sha256`
field EVERY run (not just the first) -- this is the "checksum recorded at
Phase 0" the design addendum (2026-07-10) requires, and it doubles as a
staleness/corruption check if the AutoDL mirror is ever repacked.
Extraction is idempotent: if `data_root` already has any of the 15
category subdirectories present, `stage_tarball()` skips re-extraction
(`staging.already_staged: true`) but still recomputes the checksum.

## On-disk layout (assumed, per the published distribution -- see
`orchestration/mvtec_layout.py`'s module docstring for the full
per-category structure and the "verify against the real staged tarball
at Phase 0" caveat)

```
{data_root}/{category}/train/good/*.png
{data_root}/{category}/test/good/*.png
{data_root}/{category}/test/{defect_type}/*.png
{data_root}/{category}/ground_truth/{defect_type}/*_mask.png   (unused)
```

## Per-category counts

**No per-category count is asserted anywhere in this package's code or
docs as fact** (design §3.2's own rule) -- `phase0.py`'s
`freeze_category_counts()` enumerates every category's
`n_train_good`/`n_test_good`/`n_test_defect`/`defect_type_counts` from the
STAGED tarball and writes them into `phase0_staging.json`; that file (not
this manifest, not the design doc) is the source of truth once a real box
run has executed, and is what F6's certifiability-floor table and T1's
dataset spec are frozen from at Phase 0 / PREREG freeze (design §5, §7).

## Backbones (design ADDENDUM 2026-07-10, binding)

| Backbone | Reproduction anchor | License | Reference |
|---|---|---|---|
| PatchCore | PatchCore-via-anomalib (community-standard) | Apache-2.0 | Roth et al., arXiv:2106.08265, CVPR 2022 |
| Dinomaly | official checkpoints released | Apache-2.0 | Guo et al., CVPR 2025, github.com/guojiajeremy/Dinomaly |

EfficientAD is demoted to an OPTIONAL exploratory robustness arm (Phase
3), not implemented in this build (no official code release exists for
it -- SOTA-REPRODUCTION-PLAN-2026-07-10.md §2).

## Reproduction targets

`inspect_gate/reproduction.py` holds the named, env-overridable target
constants (`PATCHCORE_TARGET_AUROC=0.991` from design §3.1's own stated
figure; `DINOMALY_TARGET_AUROC` UNSET by default -- must be confirmed
from the official Dinomaly repo's reported MVTec table at Phase 0 before
its reproduction gate can pass/fail anything). See that module's
docstring for the full rationale.

## MPDD (third benchmark, post-freeze exploratory — added 2026-07-13)

MPDD (Metal Parts Defect Detection; Jezek et al., "Deep learning-based
defect detection of metal parts: evaluating current methods in complex
conditions", ICUMT 2021): **6 real painted-metal-part categories**
(bracket_black, bracket_brown, bracket_white, connector, metal_plate,
tubes), **native MVTec-AD directory layout** (per-category `train/good/`,
`test/good/`, `test/<defect_type>/`, `ground_truth/<defect_type>/`), so
`orchestration/mvtec_layout.py::discover_category` consumes it unchanged
(roster: `MVTEC_layout.MPDD_CATEGORIES`).

**Source (credential-free, verified 2026-07-13):** the PUBLIC HuggingFace
mirror `meksamiao/mpdd` (`gated=False`), single file `MPDD.zip`
(1,825,041,283 bytes; content wrapped under a top-level `MPDD/`). The
official origin is `github.com/stepanje/MPDD` (SharePoint download,
authenticated — NOT used); the HyperAI torrent (`hyper.ai/en/datasets/31541`)
was an alternative (no torrent client on this box). The gated HF variant
`chasonfff/MPDD-AVG-2026` is a CHALLENGE variant — NOT the original, NOT used.

- HF-reported content hash (`x-linked-etag`, from the resolve HEAD):
  `69f8da73eea4a31451a50251e5c261e83e0c53f2d1a39a7d4dfc78b5c434ddd6`.
  CDN object `etag`: `80f80b489f89da1672e9478b1dede7e644857e0edd3e01b082371cdc0af0544f`.
  Locally-computed sha256 of the full archive: pending full-download completion
  (staged at `mpdd_staging/MPDD.zip`); `mpdd_prep.py` re-records the archive
  sha256 into the frozen split manifest on the box.

**Per-category counts (authoritative — read from the ZIP central directory,
`mpdd_staging/mpdd_counts_from_zipCD.json`; totals reproduce the documented
888 train-good / 458 test = 176 normal + 282 defect; ground-truth mask counts
equal per-category defect counts):**

| category | train/good | test/good | test/defect | defect types (count) |
|---|---|---|---|---|
| bracket_black | 289 | 32 | 47 | hole 12, scratches 35 |
| bracket_brown | 185 | 26 | 51 | bend_and_parts_mismatch 17, parts_mismatch 34 |
| bracket_white | 110 | 30 | 30 | defective_painting 13, scratches 17 |
| connector | 128 | 30 | 14 | parts_mismatch 14 |
| metal_plate | 54 | 26 | 71 | major_rust 14, scratches 34, total_rust 23 |
| tubes | 122 | 32 | 69 | anomalous 69 |
| **total** | **888** | **176** | **282** | test total 458 |

**Reproduction target:** Dinomaly published MPDD multi-class (uni) mean
image-AUROC **0.972** (bindable; the box runs `dinomaly_mpdd_uni.py`).
<!-- EXTERNAL-TARGET CONFIRMED 2026-07-14 (red-team round 2): the 0.972 figure
     is verified against the source paper. Guo et al., "Dinomaly: The Less Is
     More Philosophy in Multi-Class Unsupervised Anomaly Detection" (CVPR 2025),
     arXiv:2405.14325. MPDD multi-class (unified) I-AUROC = 97.2 reported in
     Table A13, Appendix C ("Additional Ablation and Experiment"): "...on other
     popular UAD benchmarks, i.e., MPDD, BTAD, and Uni-Medical, with I-AUROC of
     97.2, 95.4, and 84.9, respectively." Source URL: https://arxiv.org/abs/2405.14325
     (full text https://arxiv.org/html/2405.14325). -->

PatchCore-on-MPDD is DESCRIPTIVE (no repo-confirmed published figure), same
handling as PatchCore-on-VisA.

**Certifiability floors (pre-box, count-only — final):** G1 5/6, **G2 0/6**
at the primary protocol (good-cal=test, α_fr=0.05); MPDD is the *stingy*
extreme of the trend (MPDD 0/6 → MVTec 4/15 → VisA 12/12). See
`mpdd_results_2026-07-13/FLOOR-PREDICTION.md`.

**License / data-availability:** MPDD is released for academic/research use
(LICENSE in `stepanje/MPDD`); confirm the exact text from the in-repo LICENSE
for the manuscript's data-availability statement once the archive is extracted.
