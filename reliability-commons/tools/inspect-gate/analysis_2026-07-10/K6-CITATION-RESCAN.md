# K6 citation re-scan — 2026-07-11

## K6's verbatim definition

From the design doc, `apps-design/01-APP-mvtec-triage.md`, §4 "Kill criteria" (line 258-259):

> **K6 (scoop gate):** manual re-scan of the §1 citation block at prereg freeze; a published
> certified three-way triage on MVTec → pivot per header.

The "pivot per header" clause refers back to the doc's own header (line 24-27):

> **Scoop defense: re-run the §1 citation scan at prereg freeze (K6); if a three-way certified
> triage on MVTec appears, pivot the claimed contribution to the audit (C2) + the tool (C3) and
> demote C1 to replication-with-floors** — the design is built so C2/C3 stand without C1's novelty.

`PREREG-DRAFT-2026-07-10.md` §10 "K6 scoop note" elaborates what re-running it means in practice:

> The design's §1 citation block (conformal anomaly detection; `nonconform`; CRC-SGAD; Shen & Liu;
> Kumar et al.) was last scanned at design time. **The K6 re-scan and the full network
> citation-verification pass — including CRC-SGAD's author list and the Laxhammar & Falkman
> FUSION-2011 bibliographic details, both venue-verified but not author-verified — must run before
> this document is frozen.** If a published certified three-way triage on MVTec AD appears, the
> pre-decided pivot is C2 + C3 primary, C1 demoted to replication-with-floors.

**Interpretation.** K6 is two things, not one: (a) a **scoop search** — has anyone published the
exact three-way triage system C1 claims? — and (b) a **citation-integrity pass** on the design's
"§1 citation block" (the "Novelty positioning" paragraph, design doc lines 66-90), verifying that
every external claim/paper cited there is real, correctly attributed, and correctly characterized.
"Manual" in the design doc's own phrasing is contrasted with the automated numeric checks K1-K5/K7
(all computed from result JSONs); PREREG §10 calls the executable part of it "the full network
citation-verification pass," which is exactly WebSearch/WebFetch work — not something requiring a
human's hands specifically. The task brief pre-authorized WebSearch/WebFetch for this reason. What
K6 does NOT delegate to an agent: the actual **freeze decision** (whether the findings below are
sufficient to sign off) is the user's/team's call, not mine — I report findings, not a freeze
verdict.

## Methodology

For every citation in the design doc's §1 "Novelty positioning" paragraph (lines 66-90) plus the
backbone/dataset citations used elsewhere in the doc, I fetched the arXiv abstract page directly
(`arxiv.org/abs/<id>`) via WebFetch, cross-checked ambiguous/flagged items with a second targeted
fetch or WebSearch, and ran two scoop searches for a published three-way certified triage on MVTec
AD. No local files were modified; this file is the only output.

## Per-citation results

| # | Design doc's claim | Verified title / authors / venue | Verdict |
|---|---|---|---|
| 1 | Laxhammar & Falkman, *Sequential Conformal Anomaly Detection in Trajectories*, IEEE FUSION 2011 — **flagged "venue-verified but not author-verified"** | Confirmed: Rikard Laxhammar & Göran Falkman, "Sequential Conformal Anomaly Detection in Trajectories Based on Hausdorff Distance," Proc. 14th Int'l Conf. on Information Fusion (FUSION) 2011, pp. 1-8. Two-author paper, both names as cited. | **PASS — author list now confirmed** (2 authors, matches design doc's implicit 2-author citation) |
| 2 | Laxhammar & Falkman, *Inductive Conformal Anomaly Detection*, Ann. Math. Artif. Intell., 2015 — same author-verification flag | Confirmed: Rikard Laxhammar & Göran Falkman, "Inductive conformal anomaly detection for sequential detection of anomalous sub-trajectories," Annals of Mathematics and Artificial Intelligence, vol. 74, issue 1-2, pp. 67-94, June 2015 (Springer). | **PASS — author list confirmed, same 2 authors** |
| 3 | `nonconform` package — Hennhöfer, Kirsch & Preisach, arXiv:2605.13642, "FDR over flagged anomalies, not a routing certificate" | Confirmed: "Conformal Anomaly Detection in Python: Moving Beyond Heuristic Thresholds with 'nonconform'," Oliver Hennhöfer, Maximilian Kirsch, Christine Preisach, arXiv (stat.ML), submitted May 2026. Claim: unified interface for calibration/p-value generation/FDR control. | **PASS — title, 3 authors, and FDR characterization all match exactly** |
| 4 | Angelopoulos et al., *Conformal Risk Control*, arXiv:2208.02814 | Confirmed: "Conformal Risk Control," Anastasios N. Angelopoulos, Stephen Bates, Adam Fisch, Lihua Lei, Tal Schuster, arXiv (stat.ME), Aug 2022. Generalizes split conformal to control the expectation of any monotone loss. | **PASS — matches design doc's "formalism" characterization exactly** |
| 5 | Shen & Liu, arXiv:2504.17721, "bound the mean error rate of a Mask R-CNN defect segmenter on steel-surface data ... not on MVTec AD" | Confirmed core claim (mean-error-rate bound via conformal calibration) and confirmed **not MVTec AD**. Could NOT independently confirm from the abstract alone that Mask R-CNN / steel-surface is the specific model+dataset used in this work (the abstract mentions Mask R-CNN only as a background example of prior CNN approaches, not explicitly as the architecture used here) — the full paper (now published, see below) would need to be pulled to nail this one detail down. | **PASS on the load-bearing claim (not MVTec AD, no deferral/triage option); UNCONFIRMED on the Mask R-CNN/steel specificity** — does not affect the novelty argument either way, since "not MVTec AD" is the only fact the design doc's differentiation actually depends on. **Bibliographic update**: this paper is no longer "arXiv preprint, under review" — it has since been published as Shen & Liu, *Mathematics* (MDPI), vol. 13, issue 15, article 2430, 2025, DOI via mdpi.com/2227-7390/13/15/2430 (fetch blocked by a 403 from this host; found via search-result metadata, not independently loaded). Worth citing the journal version at freeze, not just the arXiv ID. |
| 6 | CRC-SGAD, arXiv:2504.02248 — **flagged "author list to be confirmed in the pre-freeze citation-verification pass"** | Confirmed: "CRC-SGAD: Conformal Risk Control for Supervised Graph Anomaly Detection," **Songran Bai, Xiaolong Zheng, Daniel Dajun Zeng**, arXiv (cs.LG), submitted April 2025. Claims a dual-threshold conformal risk control mechanism with guaranteed FNR/FPR bounds for graph anomaly detection. | **PASS — author list now confirmed (3 authors), FPR/FNR + graph-AD characterization matches exactly.** This closes the specific gap the PREREG called out by name. |
| 7 | Kumar et al., arXiv:2502.07255, "generic dual-threshold conformal abstention for perception — classification benchmarks, no industrial AD, no escaped-defect estimand" | Confirmed: "Beyond Confidence: Adaptive Abstention in Dual-Threshold Conformal Prediction for Autonomous System Perception," Divake Kumar, Nastaran Darabi, Sina Tayebati, Amit Ranjan Trivedi, IEEE COINS 2025. Evaluates on CIFAR-100/ImageNet1K/ModelNet40 (classification) **and** camera/LiDAR autonomous-perception tasks. | **PASS on the load-bearing claim** (no industrial AD, no escaped-defect estimand, no MVTec) — the differentiation the design doc relies on holds. **Minor characterization gap**: the design doc's "classification benchmarks" descriptor undersells the paper — it's centrally an autonomous-system/robotic-perception paper (title says so) that uses classification datasets as one of its testbeds, not a classification paper per se. Cosmetic, not a citation-integrity failure. |
| 8 | PatchCore — Roth et al., arXiv:2106.08265, CVPR 2022, "~99.1% mean image AUROC on MVTec AD (published)" (design doc line 159) | Confirmed title/authors/venue: "Towards Total Recall in Industrial Anomaly Detection," Karsten Roth, Latha Pemula, Joaquin Zepeda, Bernhard Schölkopf, Thomas Brox, Peter Gehler, CVPR 2022. **AUROC figure needs two numbers, not one**: the paper's abstract headline is "up to 99.6%" (best configuration); per a secondary source (emergentmind.com's PatchCore summary, cross-referencing the paper's own results table) **PatchCore-25% (25% coreset, single WideResNet-50 backbone) reports 99.1% mean image AUROC** — the exact figure the design doc and `inspect_gate.reproduction.PATCHCORE_TARGET_AUROC` use. | **PASS, with a precision note**: 0.991 is traceable to a real PatchCore table entry (25%-coreset config), not a fabricated number — but it is *not* the paper's headline "up to 99.6%" figure, and it is *not* an exact match to the actually-scored configuration (`orchestration/score_patchcore.py` uses `coreset_sampling_ratio=0.10`, i.e. 10% not 25% — already disclosed as PREREG D3, not a new finding here). Worth a one-line footnote at freeze clarifying which PatchCore variant 0.991 refers to, since "coreset 10%" and "coreset 25%" are different published numbers in the same paper. |
| 9 | EfficientAD — Batzner et al., arXiv:2303.14535, WACV 2024 | Confirmed: "EfficientAD: Accurate Visual Anomaly Detection at Millisecond-Level Latencies," Kilian Batzner, Lars Heckler, Rebecca König, WACV 2024, pp. 128-138. (Dropped from the confirmatory roster per the 2026-07-10 ADDENDUM — retained here only because it's still cited in the original §1/§3.1 text.) | **PASS** |
| 10 | MVTec AD dataset — Bergmann et al., CVPR 2019 | Confirmed: "MVTec AD — A Comprehensive Real-World Dataset for Unsupervised Anomaly Detection," Paul Bergmann, Michael Fauser, David Sattlegger, Carsten Steger, CVPR 2019, pp. 9592-9600. 15 categories, 70+ defect types, pixel-accurate ground truth — matches DATA_MANIFEST.md's description exactly. | **PASS** |
| 11 | Dinomaly — Guo et al., CVPR 2025, github.com/guojiajeremy/Dinomaly (no arXiv ID given in the design doc) | Confirmed: "Dinomaly: The Less Is More Philosophy in Multi-Class Unsupervised Anomaly Detection," Jia Guo et al., CVPR 2025 (arXiv:2405.14325, the arXiv ID the design doc omits). Published figures: **99.6% mean image-AUROC on MVTec-AD**, 98.7% VisA, 89.3% Real-IAD. | **PASS, and closes an open item**: this independently confirms the `INSPECT_GATE_DINOMALY_TARGET_AUROC=0.996` value used in my prior analysis pass (`analysis_2026-07-10/ANALYSIS-MEMO.md` §1) — it is the paper's own reported MVTec-AD headline number, not a guess. |

## Scoop search (the actual K6 gate condition)

Two searches targeted the exact claim structure C1 makes — a certified three-way triage (auto-pass
/ auto-reject / defer) on MVTec AD with two coupled conformal guarantees (escaped-defect +
false-reject) and per-category Mondrian stratification with explicit certifiability floors:

1. `"three-way" OR "auto-pass auto-reject defer" conformal certified triage MVTec AD escaped defect false reject rate`
2. `conformal prediction industrial visual inspection auto-pass auto-reject human review coupled guarantee 2026`

**No published paper matching this claim structure was found.** The closest adjacent work surfaced:
- Shen & Liu (already in the design's own citation block, §1 — a single conformal segmentation
  guarantee, no triage/deferral, not MVTec AD) — not a scoop, already disclosed.
- "Classification with Reject Option: Distribution-free Error Guarantees via Conformal Prediction"
  (arXiv:2506.21802) — general classification-with-abstention, confirmed via direct fetch to be
  about binary classification error-rate control, not industrial AD, not MVTec, not a dual
  escaped-defect/false-reject metric with per-category stratification — not a scoop.
- "Conformal machine learning for reliable anomaly detection in industrial cyber-physical systems"
  (a 2026 hit from `ideas.repec.org`) — thematically closest on the "industrial + conformal + AD"
  axis but, going by title/venue alone, appears to target cyber-physical/sensor-telemetry anomaly
  detection rather than image-based visual inspection on MVTec AD. **Not independently fetched and
  read in full** (time-bounded search, not a hard block) — flagged here as the one item worth a
  closer look at actual freeze time rather than confirmed clear.

**K6 scoop-gate verdict: no trigger found.** No published three-way certified triage on MVTec AD
surfaced in this pass. This is not a proof of absence — it is a documented, dated (2026-07-11)
search that the team can point to and re-run before freeze exactly as the design doc requires
("re-run the §1 citation scan at prereg freeze").

## Overall K6 verdict

**PASS, with three precision notes for whoever signs the freeze** (none of them block anything or
change the design's contribution claims — all differentiation arguments the design doc relies on
survive):
1. CRC-SGAD's author list (previously flagged "to be confirmed") is now confirmed: Bai, Zheng, Zeng.
2. PatchCore's 0.991 reproduction target is a real published number (PatchCore-25%-coreset) but is
   neither the paper's own headline "up to 99.6%" figure nor an exact match to the 10%-coreset
   configuration actually scored locally — worth a one-line footnote at freeze, not a correction
   (the reproduction gate already passed with margin either way, see `ANALYSIS-MEMO.md` §1).
3. Dinomaly's arXiv ID (2405.14325) is confirmed and its published 99.6% MVTec-AD figure matches
   what was already used as `INSPECT_GATE_DINOMALY_TARGET_AUROC` in the prior analysis pass.

**Does this close K6 as a confirmatory-paper blocker?** The scoop search (the part of K6 that
actually gates C1's novelty claim) found nothing — that's the substantive result. But I want to be
precise about what "closing" K6 means here: the design doc frames K6 as something to be **re-run at
prereg freeze**, i.e. as close to submission as possible (literature moves; a paper published next
month would still need catching). What this pass delivers is a dated, reproducible execution of
that re-scan with a clean result today, plus resolution of the one specific open item PREREG named
(CRC-SGAD's author list). Whether "one clean K6 pass, dated 2026-07-11" satisfies the freeze
precondition, or whether the team wants K6 re-run again immediately before actual submission, is a
judgment call for whoever signs the freeze — I'm reporting the finding, not declaring the
precondition satisfied on the team's behalf.

**Blocker list after this pass**: A1-A3 sign-off (user-attended, per the team lead's own framing)
is the remaining precondition PREREG-DRAFT-2026-07-10.md's status line requires before any
confirmatory C1/C2 claim. K6 itself is no longer *unexecuted* — it has now been run once, cleanly,
with one previously-open item (CRC-SGAD authors) resolved. Re-running it again immediately before
actual submission remains good practice per the design doc's own instruction, but is not something
this pass leaves undone in substance.
