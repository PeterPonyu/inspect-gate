# Venue-fit memo — inspect-gate (certified visual-inspection triage)

**Date:** 2026-07-10. **Constraint:** SCIE-indexed journals only, publisher-portal submission,
**no OpenReview / no preprint-server venue** (portfolio standing rule; matches the inspect-gate
retarget note, TMLR → non-OpenReview journal). **Paper identity:** an *applied conformal
guarantee* — a three-way triage gate (`auto-pass / auto-reject / defer`) with a certified
escaped-defect rate and a certified false-reject rate for industrial visual inspection on
MVTec AD, plus an excess-AURC audit of whether standard thresholding beats random deferral. It
is **not** a new anomaly-detection architecture; the backbones (PatchCore, Dinomaly) are
reproduced, not improved. That identity — reliability/decision-layer method, applied to
manufacturing inspection — is what the venue must fit.

IF / decision-latency / APC figures below are **approximate** (last-known ballpark, not
re-verified this pass) and must be confirmed on each journal's author page before submission.

## Candidates

### 1. Journal of Intelligent Manufacturing (JIM, Springer) — **RECOMMENDED (primary)**
- **Scope fit: strong.** JIM publishes ML/AI *methods for manufacturing*, explicitly including
  quality inspection and defect detection. A certified-triage decision layer that tells a line
  operator which images to trust, reject, or send to human review is squarely its "methods that
  make manufacturing decisions trustworthy" profile. The paper's contribution is a *guarantee
  on the decision*, not a detector — which distinguishes it from the many pure-AD papers and
  plays to JIM's applied-methods angle.
- **Format/length:** Springer `svjour3`; no hard page limit — accommodates the honesty figure
  (F6 floor table), the G2-refusal disclosure, and the K-diagnostics without an overlength fee.
- **OA:** hybrid — traditional route carries **no mandatory APC** (gold OA optional). Fits the
  no-APC preference.
- **Latency:** approximate first decision ~2–4 months; single-blind.
- **Risk:** a reviewer pool skewed to process/operations rather than ML may want a stronger
  shop-floor deployment story than a benchmark study provides — mitigated by the practitioner
  framing (escaped-defect is the cost that matters on a line) and the audit's actionable verdict.

### 2. IEEE Transactions on Industrial Informatics (IEEE TII) — **alternate**
- **Scope fit: good, broader.** Industrial-AI readership; certified inspection is in-scope, but
  the pool skews ML-systems/industrial-informatics rather than manufacturing-process, so the
  "guarantee, not architecture" framing must carry more of the novelty weight.
- **Format/length:** IEEEtran two-column, **tight page budget** (~8–10 pp + overlength charges)
  — the floor table + K-diagnostics + audit would likely push detail into a supplement. This is
  the main friction: an honesty-heavy paper fights a two-column page cap.
- **OA:** hybrid (APC optional). **Latency:** approximate ~3–5 months; higher IF than JIM.
- **Note:** IEEEtran matches other IEEE-targeted papers already in this portfolio, so template
  reuse is cheap if JIM desk-rejects on scope.

### 3. Expert Systems with Applications (ESWA, Elsevier) — **third option / fallback**
- **Scope fit: adequate but generic.** ESWA takes applied intelligent-systems work across
  domains; a certified inspection gate qualifies, but the venue is not manufacturing-specific,
  so the industrial-value framing lands less naturally than at JIM and the reliability-methods
  novelty less naturally than at a stats/ML venue. It is the "safe but unfocused" option.
- **Format/length:** Elsevier `elsarticle`, no hard page limit.
- **OA:** hybrid, but **gold-OA APC is high**; traditional route available.
- **Latency:** approximate ~2–3 months, historically fast; large annual volume.
- **Why third:** breadth cuts both ways — easy to place, harder to be the paper a reviewer
  champions. Reasonable if both JIM and TII decline on scope.

(Considered and set aside: *Computers in Industry* (Elsevier, SCIE) — a genuine fourth option
with a strong inspection/Industry-4.0 fit, comparable to JIM; worth holding as a JIM-equivalent
backup if a manufacturing-process pool is wanted over ESWA's breadth.)

## Recommendation

**Submit to Journal of Intelligent Manufacturing.** It is the tightest match to the paper's
actual identity — a trustworthy-decision *method for manufacturing inspection* — with no
mandatory APC and no page-limit pressure on the honesty-heavy content (the F6 floor table and
the disclosed G2 refusals are the paper's backbone, not trimmable). IEEE TII is the alternate if
a broader industrial-AI pool is preferred or JIM cites scope; ESWA (or Computers in Industry) is
the fallback. Cover-letter angle for JIM: lead with escaped-defect cost on a real line and the
*certified* (not merely accurate) routing decision, and position the excess-AURC audit as a
practitioner-facing check on whether current threshold practice is worth anything over random.

**Caveat carried from the substrate:** the manuscript is a *skeleton over a DRAFT preregistration*
— confirmatory C1/C2 claims are gated behind the K6 re-scan, the A1–A3 sign-off, and the
train-good dump (see the paper's Limitations and `analysis_2026-07-10/ANALYSIS-MEMO.md` §5).
Venue selection can proceed now; submission cannot until the prereg is frozen.
