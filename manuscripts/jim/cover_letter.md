# Cover letter — Journal of Intelligent Manufacturing

**To:** The Editors, *Journal of Intelligent Manufacturing* (Springer)

**Re:** Submission of *"A certified three-way triage gate for industrial visual inspection:
escaped-defect and false-reject guarantees on MVTec AD and VisA"*

Dear Editors,

We submit the enclosed manuscript for consideration as a research article in the *Journal of
Intelligent Manufacturing*. The work sits squarely in the journal's core interest — machine-learning
methods that make manufacturing decisions trustworthy — and specifically in automated visual
quality inspection.

## What the paper contributes

Modern anomaly detectors now report image-level AUROC above 0.98 on the standard MVTec AD
inspection benchmark, yet a ranking score is not a decision a line engineer can act on: it fixes no
operating threshold and guarantees nothing about the two errors that carry asymmetric cost on a
production line — letting a defective part pass (an *escaped defect*, which can ship a fault to a
customer) and rejecting a good part (a *false reject*, which wastes yield and erodes operator
trust). Our contribution is a decision layer, not a new detector:

1. **A certified three-way triage gate.** The gate routes each image to *auto-pass*, *auto-reject*,
   or *defer* on top of any backbone's anomaly scores, with a per-category **certified
   escaped-defect rate** and a **certified false-reject rate**. Both guarantees reduce exactly to
   split-conformal calibration — adding no new estimator and inheriting finite-sample validity —
   which makes the tool a thin, testable wrapper rather than a heuristic.

2. **Two complementary benchmarks.** We evaluate on MVTec AD and VisA across two reproduced
   backbones (PatchCore, Dinomaly) and five seeds each. The two benchmarks exercise opposite
   failure modes by design: MVTec AD's small good-calibration pools stress the gate's refusal
   machinery (escaped-defect certifies in all 15 categories; false-reject in 4/15 under the primary
   protocol, lifted to 12–13/15 by a preregistered train-holdout remedy), while VisA's lower score
   ceilings and larger pools let both certificates bind in all 12 categories and give the deferral
   audit real headroom.

3. **A preregistered, frozen, honest protocol.** The analysis plan was preregistered and frozen
   (sha256-pinned sign-off, 2026-07-11) before the reported numbers were computed; every reported
   figure is recomputed from frozen local score dumps, and no kill-gate is tripped in any of the 20
   (backbone, seed) aggregates. Crucially, when a category's calibration pool cannot support the
   requested rate, the gate **refuses to certify** and reports the category as
   *audited-not-certified* rather than silently loosening the threshold — refusal is a first-class,
   reported outcome.

## Why the *Journal of Intelligent Manufacturing*

The paper's identity is a *trustworthy-decision method for manufacturing inspection* — a guarantee
on the routing decision, not another detector architecture. That is a tighter fit for JIM than for
a pure computer-vision or a pure statistics venue: JIM publishes ML/AI methods for manufacturing
that explicitly include quality inspection and defect detection, and it increasingly values
reproducible, statistically rigorous benchmarking — the bar this paper is built to. The
practitioner-facing framing is deliberate: we lead with the escaped-defect cost that matters on a
real line, and we include an excess-AURC audit that asks, symmetrically, whether field-standard
threshold practice earns any deferral skill over honest random deferral — a constructive-or-debunking
check a practitioner can actually use.

## An honest note on scope

We are explicit in the manuscript that both MVTec AD and VisA are academic benchmarks: no
production-line, temporal-drift, or real-factory data backs the industrial framing, and
threshold-transfer across production periods is future work. The preregistered confirmatory pooled
audit (per-backbone) now carries a constructive verdict on MVTec AD (standard threshold practice
earns real deferral skill over honest random deferral in all five seeds, Holm-adjusted p = 0.002),
and the tier-2 validity readout is graded under the frozen amendments. We also report, post-hoc and
explicitly labelled exploratory, the completion of the B3 train-good practice for PatchCore
(constructive) and a binding demonstration exhibiting concrete categories where a naive fixed
threshold's realized error rate exceeds target while the certified gate holds; the K6 scoop re-scan
was executed pre-submission with a clear verdict (no prior certified three-way triage on MVTec AD or
VisA), and the only arm that remains unlocked-but-uncomputed is the K4 audit-headroom gate. The
per-image end-to-end latency table an inspection-focused
reader will reasonably expect is now included (Section "Latency and deployment cost"): measured on
our hardware, the gate adds 2.8 us/image of routing on top of the backbone forward pass (under 0.02%
of a Dinomaly inference), confirming with a real measurement that certification is free relative to
detection.

We confirm that this manuscript is original, is not under consideration elsewhere, and that all
authors have approved the submission. We have no conflicts of interest to declare. Thank you for
considering our work.

Sincerely,

*[TODO-USER: author name(s), affiliation, and corresponding-author contact details]*
