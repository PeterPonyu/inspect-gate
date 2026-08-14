---
layout: layout.njk
title: Gate
description: Score anatomy, floor arithmetic, and three-way routing on academic AD parts.
permalink: /gate/
scripts:
  - /assets/js/lightbox.js
---

<div class="prose">
  <h1>Mechanism</h1>
  <p>
    Score convention: <strong>higher = more anomalous</strong>. The band is not a detector;
    it is a split-conformal triage on scores the detector already emits.
  </p>
  <p>
    Two finite-sample certificates travel with the band: escaped-defect (G1) and false-reject (G2).
    Refusal is first-class. When the calibration floor is unmet, that auto-action is emptied.
  </p>
  <p class="eq">α<sub>min</sub> = 1/(n<sub>cal</sub>+1) · n<sub>cal</sub> ≥ ⌈1/α⌉ − 1</p>
</div>

<figure class="exhibit">
  <img src="{{ '/figures-web/inspect-fig-scoreanatomy-web.svg' | url }}" alt="Four score-anatomy panels: screw both axes live, VisA pcb1 PatchCore, MPDD connector refused, VisA pcb1 Dinomaly." width="1200" height="720" />
  <figcaption>
    (a) MVTec screw, PatchCore: both axes certified, finite (t<sub>lo</sub>, t<sub>hi</sub>).
    (b) VisA pcb1, PatchCore.
    (c) MPDD connector: floor refusal — thresholds at ±∞, every image defers; the panel is refused, not empty.
    (d) VisA pcb1, Dinomaly.
    Hover is not required: thresholds are drawn and labelled. Exploratory VisA / MPDD panels are tagged in the figure.
  </figcaption>
</figure>

<div class="prose">
  <h2>Six ground-truth × route classes</h2>
  <p>
    Tiles are real parts. Contours and insets are <strong>dataset ground truth, not model localization</strong>.
    Connector defer is named <strong>floor refusal</strong>, not “uncertain.”
    <span class="tag">exploratory MPDD / VisA tiles</span>
  </p>
</div>

{% set routes = ["AUTO-PASS", "DEFER", "AUTO-REJECT"] %}
{% for block in samples.tiles | batch(3) %}
  <h3 class="prose">{{ block[0].row }}</h3>
  <div class="samples">
    {% for tile in block %}
      {% set cls = "route-pass" if tile.route == "AUTO-PASS" else ("route-defer" if tile.route == "DEFER" else "route-reject") %}
      <figure class="{{ cls }}">
        <img
          src="{{ ('/figures-web/' + tile.file) | url }}"
          alt="{{ tile.row }} routed {{ tile.route }}, score {{ tile.score }}"
          data-lightbox="{{ tile.row }} · {{ tile.route }} · score {{ tile.score }}{% if tile.note %} · {{ tile.note }}{% endif %}. Dataset GT contours are not model localization."
        />
        <div class="cap">
          {{ tile.route }} · score {{ tile.score }}
          {% if tile.note %} · {{ tile.note }}{% endif %}
          {% if tile.gt %} · GT inset{% endif %}
        </div>
      </figure>
    {% endfor %}
  </div>
{% endfor %}

<p class="prose"><em>{{ samples.caption }} {{ samples.protocol }}</em></p>

<dialog class="lb">
  <img alt="" />
  <p data-lb-cap></p>
  <form method="dialog"><button>Close</button></form>
</dialog>
