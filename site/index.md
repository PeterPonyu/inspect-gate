---
layout: layout.njk
title: Three-way triage gate for visual-inspection AD
description: Three-way triage gate with escaped-defect and false-reject certificates on academic AD benchmarks.
permalink: /
---

<div class="title-block">
  <p class="full-title">{{ site.title }}</p>
  <p class="short">{{ site.shortTitle }}</p>
  <p class="meta">{{ site.author }} · ORCID {{ site.orcid }}</p>
</div>

<div class="prose">
  <p class="lede">Anomaly detectors rank defects; they do not define a safe operating decision.</p>
</div>

<figure class="exhibit">
  <img src="{{ '/figures-web/inspect-fig-overview-web.svg' | url }}" alt="Three-way gate: score to floor check to pass, defer, or reject, or audited-not-certified." width="1200" height="420" />
  <figcaption>
    Anomaly scores enter a floor check. If the calibration pool cannot support the requested bound, that auto-action is emptied and the axis is audited-not-certified. Otherwise the pair (t<sub>lo</sub>, t<sub>hi</sub>) routes each image to auto-pass, human-defer, or auto-reject. Higher score means more anomalous.
  </figcaption>
</figure>

<div class="tiles" aria-label="Frozen confirmatory numbers">
  <article class="tile">
    <div class="lab">G1 certified</div>
    <div class="num">15/15</div>
    <p class="caveat">MVTec, α<sub>miss</sub>=0.10</p>
  </article>
  <article class="tile">
    <div class="lab">G2 certified</div>
    <div class="num">4/15</div>
    <p class="caveat">MVTec, α<sub>fr</sub>=0.05, primary protocol</p>
  </article>
  <article class="tile">
    <div class="lab">Pooled FR</div>
    <div class="num">0.5%</div>
    <p class="caveat">at 54.4% deferral; CRC FR 3.1% with 0% deferral</p>
  </article>
  <article class="tile">
    <div class="lab">α<sub>miss</sub>=0.01</div>
    <div class="num">0/33</div>
    <p class="caveat">all categories refuse (need n<sub>cal</sub><sup>def</sup>≥99)</p>
  </article>
  <article class="tile">
    <div class="lab">Drift residual</div>
    <div class="num">~34% / ~5%</div>
    <p class="caveat">good-score KS misses 34% of accepted PatchCore cells above target; defect-marginal catches ~5% of those (exploratory stress)</p>
  </article>
</div>

<div class="band">
  <strong>Evidence boundary.</strong>
  The output is an auditable calibration/refusal protocol. Academic splits validate the machinery. Temporal production drift is future work.
</div>

<div class="prose">
  <p>
    Confirmatory path: V1 → C2 on MVTec AD. VisA and MPDD are exploratory pool-size extremes, not a second confirmatory claim.
    Continue: <a href="{{ '/gate/' | url }}">Gate</a> ·
    <a href="{{ '/certificate/' | url }}">Certificate</a> ·
    <a href="{{ '/envelope/' | url }}">Envelope</a> ·
    <a href="{{ '/honesty/' | url }}">Honesty</a> ·
    <a href="{{ '/reproduce/' | url }}">Reproduce</a> ·
    <a href="{{ '/cite/' | url }}">Cite</a>.
  </p>
</div>
