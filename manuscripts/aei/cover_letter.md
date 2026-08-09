# Cover letter — Advanced Engineering Informatics

**To:** The Editors, *Advanced Engineering Informatics* (Elsevier)

**Re:** Submission of *"A certified three-way triage gate for industrial visual
inspection: escaped-defect and false-reject guarantees on MVTec AD, VisA, and MPDD"*

Dear Editors,

We submit the enclosed manuscript for consideration as a research article in *Advanced
Engineering Informatics*. The work presents a deployable component for an automated
visual-inspection system: a thin decision layer that converts any anomaly detector's
scores into an auditable, certified inspection routing decision. This sits within the
journal's established interest in intelligent, informatics-driven engineering systems, and
specifically in the industrial visual-inspection line the journal already publishes ---
component-aware anomaly detection for logical inspection, defect-aware transformer networks
for surface-defect detection, and autoencoder-based surface inspection, among others.

## What the paper contributes

Modern anomaly detectors report image-level AUROC above 0.98 on the standard MVTec AD
benchmark, yet a ranking score is not a decision an inspection line can act on: it fixes no
operating threshold and guarantees nothing about the two errors that carry asymmetric cost
in production --- letting a defective part pass (an *escaped defect*, which can ship a fault
to a customer) and rejecting a good part (a *false reject*, which wastes yield and erodes
operator trust). Our contribution is a decision layer, not a new detector:

1. **A certified three-way triage gate.** The gate routes each image to *auto-pass*,
   *auto-reject*, or *defer* on top of any backbone's anomaly scores, with a per-category
   **certified escaped-defect rate** and a **certified false-reject rate**. Both guarantees
   reduce exactly to split-conformal calibration --- adding no new estimator and inheriting
   finite-sample validity --- which makes the component a thin, testable wrapper rather than
   a heuristic. Because it is detector-agnostic, it drops onto the surface-defect and
   anomaly-detection pipelines this journal's readership already builds and deploys.

2. **Three complementary benchmarks, including a fabrication benchmark.** We evaluate on
   MVTec AD, VisA, and MPDD (real painted-metal parts) across two reproduced backbones
   (PatchCore, Dinomaly) and five seeds each. The benchmarks exercise opposite failure modes
   by design: MVTec AD's small good-calibration pools stress the gate's refusal machinery,
   VisA's larger pools and lower score ceilings let both certificates bind in all categories,
   and MPDD is the stingy extreme where uniformly small good pools force refusal --- the three
   together give a monotone reading of pool-size-driven refusal.

3. **A preregistered, frozen, honest protocol.** The analysis plan was preregistered and
   frozen (sha256-pinned sign-off, 2026-07-11) before the reported numbers were computed;
   every reported figure is recomputed from frozen local score dumps, and no kill-gate is
   tripped in any of the 30 (backbone, seed) aggregates. Crucially, when a category's
   calibration pool cannot support the requested rate, the gate **refuses to certify** and
   reports the category as *audited-not-certified* rather than silently loosening the
   threshold --- refusal is a first-class, reported outcome, which is exactly the honesty
   property a deployed inspection system needs.

## Why *Advanced Engineering Informatics*

The paper's identity is a *deployable, informatics-level reliability component for
manufacturing inspection* --- a guarantee on the routing decision, engineered to sit on top
of the detector architectures the field already produces, not another detector. That is a
tight fit for AEI, which publishes intelligent-systems and informatics methods for
engineering that explicitly include industrial visual inspection and defect detection, and
which values deployable, reproducibly benchmarked contributions. We also include a per-image
latency and deployment-cost table (the gate adds a measured 2.8 microseconds/image of routing
on top of the backbone forward pass, under 0.02% of a Dinomaly inference), quantifying with a
real measurement that the certificate is free relative to detection --- the kind of deployment
accounting an engineering-informatics reader will expect.

## An honest note on scope

We are explicit in the manuscript that MVTec AD, VisA, and MPDD are academic benchmarks: no
production-line, temporal-drift, or real-factory data backs the industrial framing, and
threshold-transfer across production periods (framed through conformal prediction under
covariate shift) is future work. The preregistered confirmatory pooled audit returns a
constructive verdict on MVTec AD (standard threshold practice earns real deferral skill over
honest random deferral in all five seeds, Holm-adjusted p = 0.002). We also quantify what the
dual gate buys over the nearest single-threshold conformal alternative (Conformal Risk
Control): the same escaped-defect guarantee, plus a false-reject guarantee the single-threshold
construction cannot offer, purchased by turning auto-rejects into deferrals.

We confirm that this manuscript is original, is not under consideration elsewhere, and that
all authors have approved the submission. We have no competing interests to declare. Thank
you for considering our work.

Sincerely,

*[TODO-USER: author name(s), affiliation, and corresponding-author contact details]*
