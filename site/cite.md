---
layout: layout.njk
title: Cite
description: Protocol title, frozen numbers, keywords, and public archives.
permalink: /cite/
---

<div class="prose">
  <h1>Cite</h1>
  <p>Record status: frozen science. Code and reserved DOI. Not a venue package.</p>
  <p class="full-title"><strong>{{ site.title }}</strong></p>
  <p>{{ site.author }} (corresponding) · ORCID <a href="https://orcid.org/{{ site.orcid }}">{{ site.orcid }}</a></p>
  <p>{{ site.affiliation }}</p>

  <h2>Protocol</h2>
  <p>
    Anomaly detectors can rank defects well without defining a safe operating decision. A pre-deployment triage layer on two detector architectures and three academic industrial-inspection benchmarks maps anomaly scores to per-category auto-pass, auto-reject, and human-defer regions with finite-sample split-conformal bounds on escaped-defect and false-reject rates. Categories whose calibration pools cannot support a requested bound are audited-not-certified and routed to review. On confirmatory MVTec AD at α<sub>miss</sub>=0.10, α<sub>fr</sub>=0.05, escaped-defect certification holds for all 15 categories, while false-reject holds in only 4/15 under the primary protocol; pooled false-reject is 0.5% at 54.4% deferral, versus 3.1% with no deferral under single-threshold conformal risk control (CRC) (as on MPDD, refused G2 cells contribute structural zeros via an empty auto-reject band). Exploratory VisA and MPDD checks tag complementary pool-size extremes: on VisA the gate reduces false rejects from 16.2% to 3.0% relative to CRC (escaped-defect 7.6% vs. 9.5%), and on MPDD it reports 0.0% false-reject only by deferring 73.1% where the false-reject axis is refused in all six categories (0/6 G2-certifiable); a high-review diagnostic, not a dual-certificate success. Escaped-defect also holds for all 12 VisA categories; all 33 categories refuse at α<sub>miss</sub>=0.01 for lack of 99 defective calibration examples. A synthetic corruption stress test finds good-score drift screening misses 34% of accepted PatchCore cells above the escaped-defect target; a defect-score marginal test catches only about 5% of those residual cells. Evidence supports a calibration/refusal protocol on academic AD benchmarks, not portable production-line deployment: temporal drift remains untested.
  </p>

  <h2>Keywords</h2>
  <p>{{ site.keywords | join("; ") }}.</p>

  <h2>Highlights</h2>
  <ul>
    <li>Anomaly detectors rank defects; they do not define a safe operating decision.</li>
    <li>Three-way gate: per-category pass/reject/defer with finite-sample certificates.</li>
    <li>Refusal is first-class: audited-not-certified when the cal pool is too small.</li>
    <li>MVTec: escaped-defect certified in 15/15; false-reject only 4/15 primary.</li>
    <li>Evidence is for academic AD benchmarks, not portable production-line use.</li>
  </ul>

  <h2>Archives</h2>
  <p>
    Zenodo concept
    <a href="{{ site.zenodoConcept | doiHref }}">{{ site.zenodoConcept }}</a>
    (version 0.4.1 record <a href="{{ site.zenodoVersion | doiHref }}">{{ site.zenodoVersion }}</a>).
    Code: <a href="{{ site.github }}">{{ site.github }}</a>.
  </p>
</div>
