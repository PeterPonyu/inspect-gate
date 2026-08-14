---
layout: layout.njk
title: Envelope
description: Alpha frontier, calibration-fraction, and planning curve. All post-freeze exploratory.
permalink: /envelope/
evidenceTag: post-freeze exploratory
scripts:
  - /assets/js/planner.js
---

<div class="prose">
  <h1>Operating envelope</h1>
  <p>
    Every exhibit on this page is <strong>post-freeze exploratory</strong>. The operating point remains α<sub>miss</sub>=0.10, α<sub>fr</sub>=0.05.
  </p>
</div>

<figure class="exhibit">
  <span class="tag">post-freeze exploratory</span>
  <img src="{{ '/figures-web/inspect-fig-alphafrontier-web.svg' | url }}" alt="Deferral and both-axis certified fraction versus alpha_miss, small multiples by benchmark." width="1200" height="720" />
  <figcaption>
    Deferral versus α<sub>miss</sub>, and the fraction of categories with both axes certified. The operating point α<sub>miss</sub>=0.10 is marked. At α<sub>miss</sub>=0.01 every category refuses.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-freeze exploratory</span>
  <img src="{{ '/figures-web/inspect-fig-calfraction-web.svg' | url }}" alt="Lost calibration budget increases deferral; MPDD at fraction 0.10 is 100 percent deferral." width="1200" height="720" />
  <figcaption>
    Lost calibration budget becomes deferral, never silent error. MPDD at fraction 0.10 is measured 100% deferral.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-freeze exploratory</span>
  <img src="{{ '/figures-web/inspect-fig-calplanning-web.svg' | url }}" alt="Required calibration pool versus alpha, with G2 shortfall marked non-certifiable." width="1200" height="560" />
  <figcaption>
    Planning curve: n<sub>cal</sub> ≥ ⌈1/α⌉ − 1. α<sub>miss</sub>=0.10 costs 9 defectives; α<sub>fr</sub>=0.05 costs 19 goods. G2 refusals are a pool-allocation shortfall, not a deep obstruction. The non-certifiable shortfall reading is unchanged.
  </figcaption>
</figure>

<div class="prose">
  <h2>Read-only planner</h2>
  <p>Evaluates the planning equation only. It does not invent plant throughputs.</p>
</div>

<form class="planner" data-planner>
  <label>
    α
    <input name="alpha" type="number" min="0.001" max="0.5" step="0.01" value="0.10" />
  </label>
  <label>
    Required n<sub>cal</sub>
    <output data-ncal>—</output>
  </label>
  <p data-note></p>
</form>
