---
layout: layout.njk
title: Honesty
description: Drift monitors fail, gates do not transfer across detectors, and G2 remedies are not the primary protocol.
permalink: /honesty/
scripts:
  - /assets/js/mondrian.js
---

<div class="prose">
  <h1>Negative results are the point</h1>
  <p>
    These exhibits are why the companion is scientific: monitors fail, gates do not transfer, and remedies are not the primary protocol.
    Calibrated gates do not transfer across detectors. Synthetic drift screening misses a large share of accepted cells above the escaped-defect target. Temporal production drift is untested.
  </p>
</div>

<div class="band exploratory">
  <span class="tag">post-freeze exploratory</span>
  <p>{{ drift.residual }}</p>
</div>

<table>
  <caption>{{ drift.caption }}</caption>
  <thead>
    <tr>
      <th>Corruption</th>
      <th class="num">Severity</th>
      <th>KS-refused</th>
      <th>Escaped among accepted</th>
      <th>FR among accepted</th>
    </tr>
  </thead>
  <tbody>
    {% for row in drift.rows %}
      <tr>
        <td>{{ row.corruption }}</td>
        <td class="num">{{ row.severity }}</td>
        <td class="num">{{ row.ks_refused }}</td>
        <td class="num">{{ row.escaped }}</td>
        <td class="num">{{ row.fr }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<figure class="exhibit">
  <span class="tag">post-freeze exploratory</span>
  <img src="{{ '/figures-web/inspect-fig-jointmon-web.svg' | url }}" alt="Four-panel joint monitor: catch rate tracks false-alarm rate." width="1200" height="720" />
  <figcaption>
    Joint location tests are indiscriminate: catch tracks false alarm. Good-score KS is not a deployable monitor. A rank-order statistic is named as future work, not shown as a result.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-freeze exploratory</span>
  <img src="{{ '/figures-web/inspect-fig-xdet-web.svg' | url }}" alt="Cross-detector transfer: diagonal certificates hold, off-diagonal escaped-defect violations dominate." width="1200" height="560" />
  <figcaption>
    Transfer: 160/165 escaped-defect violations PatchCore→Dinomaly; 80/165 G2 violations in reverse; same-detector diagonal 30/30. Recalibrate on the detector you guard.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-hoc · PatchCore-only</span>
  <img src="{{ '/figures-web/inspect-fig-g2delta-web.svg' | url }}" alt="G2 train-holdout remedy flips most MVTec cells from floor-refused to certified; leather stays KS-refused." width="1200" height="560" />
  <figcaption>
    {{ g2delta.caption }} {{ g2delta.summary }} Amber is KS-refused; gray is floor-refused. Not the primary protocol.
  </figcaption>
</figure>

<div class="prose" data-mondrian>
  <h2>Mondrian appendix</h2>
  <p>
    Residual errors concentrate in subtle defect types. Filter the heatmap; no new science.
    <span class="tag">{{ mondrian.tag }}</span>
  </p>
  <label>
    Category
    <select name="category">
      <option value="all">all</option>
      {% for cat in floors.rows %}
        <option value="{{ cat.category }}">{{ cat.category }}</option>
      {% endfor %}
    </select>
  </label>
  <div class="heat">
    <table>
      <thead>
        <tr>
          <th>Category</th>
          <th>Defect type</th>
          <th class="num">PC miss</th>
          <th class="num">PC defer</th>
          <th class="num">DM miss</th>
          <th class="num">DM defer</th>
        </tr>
      </thead>
      <tbody>
        {% for cell in mondrian.cells %}
          <tr data-category="{{ cell.category }}" class="{% if cell.pc_miss and cell.pc_miss > 0.1 %}hot{% endif %}">
            <td>{{ cell.category }}</td>
            <td>{{ cell.defect_type }}</td>
            <td class="num">{{ cell.pc_miss if cell.pc_miss !== none else "—" }}</td>
            <td class="num">{{ cell.pc_defer if cell.pc_defer !== none else "—" }}</td>
            <td class="num">{{ cell.di_miss if cell.di_miss !== none else "—" }}</td>
            <td class="num">{{ cell.di_defer if cell.di_defer !== none else "—" }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
