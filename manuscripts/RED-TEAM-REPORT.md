# RED-TEAM REPORT — inspect-gate manuscript skeleton (`manuscripts/paper.tex`)

**Reviewer stance:** adversarial, goal = reject. **Scope:** attacks what EXISTS in the current draft
(reproduction gate, seed stability, floor table, V1 tier-1, exploratory audit — all real, all traced
to `analysis_2026-07-10/`). The `\todo{}`-marked gated arms (confirmatory C2, B3, G2 train-holdout
promotion, V1 tier-2 verdict, K4/K6) are not attacked as absent. No paper edits made.

---

## MAJOR-1: "Zero new math" is presented as a strength but is also the paper's biggest novelty
liability, and the paper does not fully defend against the obvious reviewer objection

**Claim under attack.** Abstract: "Both guarantees reduce exactly to split-conformal calibration...
so the method adds no new estimator and inherits finite-sample validity." Intro's first bullet:
"A zero-new-math certified gate... The method is a thin, testable wrapper with finite-sample
validity, not a new calibration heuristic."

**Hostile argument.** "You have told me, twice, in your own words, that there is no new statistics
here. The score-negation trick for a one-sided lower bound is textbook/folklore conformal prediction
— your own §Methods correctly attributes it to an order-statistic identity, not a contribution. Two
established backbones (PatchCore, Dinomaly), one established benchmark (MVTec AD), one established
selective-prediction pattern (accept/reject/defer — your own Related Work concedes this is a
selective-prediction mechanism). What, precisely, is the contribution that clears a journal's
novelty bar? A CLI tool and a one-line floor formula (α_min = 1/(n_cal+1), itself immediate algebra)
are engineering, not research."

**What the paper's actual defense is, and whether it holds.** The paper's real answer is *system/
application* novelty, not math novelty: "To our knowledge no published method delivers a certified
three-way triage... on MVTec AD with coupled escaped-defect and false-reject guarantees and explicit
per-category certifiability floors; a scoop search at draft time (2026-07-11) surfaced none." This is
a legitimate and, per my own independent re-verification (see Scoop search, below), currently
accurate claim. **But it is asserted, not demonstrated quantitatively** — the paper names the closest
systems (CRC-SGAD, Kumar et al., Shen & Liu) and states in prose why each falls short, but never shows
a table or figure making the gap concrete (e.g., "here is what a single-guarantee system like CRC-SGAD
would certify on this same substrate, and here is what the coupled two-guarantee + refusal-floor
system adds"). For a methods-adjacent journal (Journal of Intelligent Manufacturing), "we assert no
one else does this exact combination" is weaker than "here is the operational capability gap,
quantified."

**Severity: MAJOR.** Not fatal — the novelty claim is real and (per my scoop check) currently
unscooped — but under-defended in a way a skeptical reviewer will exploit, especially since the paper
proactively volunteers the "zero new math" framing rather than being caught making a stronger claim.

**Remediation.** Add one concrete illustration of what the coupled/refusal system provides that a
single-guarantee or non-refusing system would not — e.g., show what a naive practitioner using only
G1 (or only a fixed global threshold, already computed as baseline B1 in the exploratory audit) would
get wrong on a specific category, contrasted with the gate's honest refusal there. This also directly
strengthens MAJOR-2 below.

---

## MAJOR-2: Both reproduced backbones are near-ceiling (98.2%/99.6% mean AUROC) — does this substrate
have the power to demonstrate the triage system's value at all, and is the paper's rebuttal tested?

**Claim under attack.** The Introduction's own framing is the paper's best asset here and also its
biggest exposure: "Modern detectors... report image-level AUROC above 0.98 and, for the newest
models, above 0.99. On the usual reading the problem looks solved." The paper's rebuttal — "Image-
AUROC is a threshold-free ranking summary... it names no operating point" — is the correct, real
argument (a high-AUROC ranking metric is genuinely a different object from a calibrated operating-
point error rate), but it is asserted, not empirically demonstrated anywhere in this draft.

**Hostile argument.** "You've told me the detectors are already near-perfect. You've told me (in
§Exploratory audit) that Dinomaly is SO saturated that your own excess-AURC audit has 14/30 degenerate
cells and rejects the random-deferral null in 0/30 — by your own account, 'uninformative about
practice quality.' If your best backbone makes your own confirmatory-audit-in-waiting uninformative,
and your weaker backbone (PatchCore, still 98.2%) is not much better, is MVTec AD simply too easy a
substrate to show this system adds value over a naive fixed threshold? Show me ONE category where a
naive threshold would actually violate α_miss or α_fr and the gate catches it — that's the whole
argument, and it's not in this draft."

**What partially defends this.** The paper is admirably honest about the Dinomaly ceiling effect —
it's flagged in §Exploratory audit AND restated in Limitations ("a Dinomaly '0/30 reject' is
uninformative about practice quality rather than evidence against it"). This substantially blunts a
"you're hiding this" attack. It does **not** address the deeper question of whether MVTec AD, at this
backbone maturity, is the right substrate to demonstrate the SYSTEM's operational value (as opposed to
the substrate on which the audit's statistical machinery happens to be validated) — and the concrete
counter-example that would settle it (a naive threshold actually failing somewhere) is exactly what
the currently-gated confirmatory C2 audit is designed to produce.

**Severity: MAJOR**, mitigated by honest self-disclosure but not resolved by it.

**Remediation.** Either (a) pull forward one illustrative naive-threshold-fails case from the
exploratory audit already run (PatchCore has real, non-degenerate excess-AURC signal in 10/30
practice-cells — this is closer to a genuine finding than Dinomaly's), or (b) add a synthetic/
degraded-backbone stress arm showing the gate behaves correctly when the underlying detector is NOT
near-ceiling, which also strengthens the paper against the objection that its statistical machinery
has never been tested somewhere it could plausibly fail.

---

## MODERATE-3: The PREREG-floor-exact-match result is framed as an empirical finding but is (mostly)
deterministic arithmetic — the paper does not distinguish it from the genuinely empirical V1 result

**Claim under attack.** §5.3 (Table "tab:floors"): "The per-category calibration counts computed from
the full local test arrays match the preregistered arithmetic-only floor table exactly (0/15
mismatches for both backbones, identical across all 5 seeds)... This reproduces the preregistered
projection to the count."

**Hostile argument.** "MVTec AD's per-category test-set counts are fixed, public constants, unchanged
since the dataset's 2019 release. The PREREG's floor table and your Table 2 both derive their counts
by applying the SAME deterministic rounding rule (round-half-to-even of n/2) to the SAME fixed input.
Reporting that two evaluations of the same deterministic function on the same fixed input produce the
same output is not an empirical confirmation of anything about your METHOD — it's a check that your
code doesn't have a bug in reading a CSV, which is useful, but it does not belong in a Results section
presented at the same level of significance as V1 tier-1 (which IS a genuine empirical result — it
could have failed if the calibration/routing pipeline were actually broken)."

**Is this fair?** Substantially yes, though not entirely — the check does have real (if narrow) value:
it validates the data-staging pipeline reads the frozen substrate correctly and that no corruption or
off-by-one crept in between the PREREG's original count and the analysis script's re-derivation. But
the paper's own language ("This reproduces the preregistered projection to the count") reads as if the
match itself is evidence *for the method*, when it is evidence *for the pipeline's arithmetic
correctness* — a different (and much weaker) claim.

**Severity: MODERATE.** A framing issue, not a validity issue — the underlying numbers are correct and
the pipeline behavior is worth reporting, just not with the rhetorical weight currently given to it.

**Remediation.** One sentence distinguishing the two: "the floor-table match is a pipeline-correctness
check (the counts are a deterministic function of the fixed MVTec test split); the genuinely empirical
result is V1 tier-1 below, which is measured from real calibrate/route/evaluate runs and could have
failed."

---

## Point in the paper's favor (stated for balance, since the sibling rotcert draft has the opposite
problem): V1 tier-1 is a genuine held-out result, not a self-referential one

Independently re-verified this pass: `analysis_2026-07-10/scripts/run_analysis.py`'s calibration loop
uses `splits.repeated_stratified_splits` to produce R=20 **disjoint** (cal, eval) pairs per
(backbone, seed); `gate.calibrate_gate` is fit on the cal half only, and `route_gate` +
`certify.coverage_cell` are evaluated on the eval half only — genuinely held-out, unlike the rotcert
sibling paper's in-sample pilot audit (see that report's FATAL-1). I wrote this analysis script
myself in an earlier pass and re-confirmed the split logic directly in this pass; a hostile reviewer
checking this specific mechanism would find it sound. Cross-checked against `SUMMARY.json`:
`n_cal_count_mismatches_across_seeds: 0`, `patchcore_bit_identical_pairs: "0/60"`,
`dinomaly mean_iauroc_across_seeds: {mean: 0.99603, std: 0.00029}` — all match Table 3/§5.2's reported
numbers exactly.

---

## Number-tracing audit (§3 of the assignment)

Spot-checked against `analysis_2026-07-10/SUMMARY.json` this pass (not just re-cited from memory):
`n_cal_count_mismatches_across_seeds = 0` ✓ matches §5.3; `patchcore_bit_identical_pairs = "0/60"` ✓
matches §5.2's "0/60 bit-identical" claim; `dinomaly mean_iauroc_across_seeds` values
`[0.99649, 0.99604, 0.99596, 0.99598, 0.99569]`, mean `0.99603`, std `0.00029` ✓ matches Table 3's
"0.9957-0.9965" range and §5.2's "0.9960 ± 0.00029." K1/K2 zero-violation claims in Table "tab:v1"
confirmed programmatically against `SUMMARY.json["gate_calibration_k1_k2"]` for all 10 (backbone,
seed) cells this pass — all pass. No discrepancy found anywhere traced.

## Scoop search summary (§5 of the assignment)

This paper's scoop search was already run as a dedicated task this cycle (`analysis_2026-07-10/
K6-CITATION-RESCAN.md`, dated 2026-07-11): two targeted searches for a published certified three-way
triage (auto-pass/auto-reject/defer with coupled escaped-defect/false-reject conformal guarantees +
Mondrian floors) on MVTec AD found nothing matching. One adjacent-but-distinct item was flagged there
for a closer look at actual submission time (a 2026 "conformal ML for industrial cyber-physical
systems" hit, likely sensor/telemetry rather than image-based, not confirmed either way). Standing
finding: **no scoop currently found**, but per the design's own K6 discipline this should be re-run
immediately before submission, not treated as permanently closed by a 2026-07-11 search.

## Does the Limitations section pre-empt these attacks?

**Partially, for MAJOR-2** — the Dinomaly ceiling effect is explicitly disclosed, which blunts (but
does not resolve) the "is this substrate even hard enough" objection; the deeper substrate-choice
question is not addressed. **No, for MAJOR-1** — novelty sufficiency is defended in the Introduction/
Related Work (proactively, which is good practice) but not revisited in Limitations, and the defense
there is qualitative rather than quantitative. **No, for MODERATE-3** — the floor-table triviality
issue is not raised anywhere; the section is otherwise candid (gated arms are exhaustively listed) but
does not distinguish "trivial arithmetic check" from "genuine empirical result" among the numbers it
DOES report as non-gated.
