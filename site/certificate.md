---
layout: layout.njk
title: Certificate
description: Per-category G1 and G2 map on confirmatory MVTec, with VisA and MPDD tagged exploratory.
permalink: /certificate/
scripts:
  - /assets/js/categorymap.js
---

<div class="prose">
  <h1>Certification map</h1>
  <p>
    Confirmatory path: V1 → C2 on MVTec AD. G1 (escaped-defect) is plentiful; G2 (false-reject) is scarce because the good-pool floor is tighter.
    Do not lead with CRC or cost — those live on the baseline page.
  </p>
  <p>
    Colored 0.0 means the certificate issued and no errors were observed. Hatched 0.0 means the observed rate is shown and the certificate is withheld.
  </p>
</div>

<div class="map-grid" data-category-map>
  <script type="application/json" data-map-json>{{ categorymap | dump | safe }}</script>
  <div data-map-root></div>
  <aside class="detail" data-detail></aside>
</div>

<div class="prose">
  <h2>MVTec floors</h2>
  <p>{{ floors.caption }} G2 OK only on cable, hazelnut, screw, transistor.</p>
</div>

<table>
  <thead>
    <tr>
      <th>Category</th>
      <th class="num">n<sub>cal</sub><sup>def</sup></th>
      <th class="num">α<sub>min</sub> G1</th>
      <th>G1</th>
      <th class="num">n<sub>cal</sub><sup>good</sup></th>
      <th>G2</th>
    </tr>
  </thead>
  <tbody>
    {% for row in floors.rows %}
      <tr class="{{ 'ok' if row.g2 == 'OK' else 'refuse' }}">
        <td>{{ row.category }}</td>
        <td class="num">{{ row.n_cal_def }}</td>
        <td class="num">{{ row.alpha_min_g1 }}</td>
        <td class="cert">{{ row.g1 }}</td>
        <td class="num">{{ row.n_cal_good }}</td>
        <td class="cert">{{ row.g2 }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<div class="prose">
  <h2>Coverage is not a certificate</h2>
  <p>{{ deferral.caption }}</p>
</div>

<table>
  <thead>
    <tr>
      <th>Benchmark</th>
      <th>Backbone</th>
      <th>Median deferral</th>
      <th>Mean</th>
      <th>Max</th>
      <th>Min</th>
      <th>Tag</th>
    </tr>
  </thead>
  <tbody>
    {% for row in deferral.rows %}
      <tr>
        <td>{{ row.benchmark }}</td>
        <td>{{ row.backbone }}</td>
        <td class="num">{{ row.median }}</td>
        <td class="num">{{ row.mean }}</td>
        <td>{{ row.max }}</td>
        <td>{{ row.min }}</td>
        <td><span class="tag">{{ row.tag }}</span></td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<figure class="exhibit">
  <span class="tag">confirmatory MVTec · exploratory VisA / MPDD</span>
  <img src="{{ '/figures-web/inspect-fig-deferral-web.svg' | url }}" alt="Per-category deferral bars with a K2 0.80 reference line." width="1200" height="720" />
  <figcaption>
    Seed-0 per-category deferral. MVTec medians sit near 70% because G2 refusal empties auto-reject. VisA drops where G2 is live. Connector is 100% deferral: floor refusal, not indecision.
  </figcaption>
</figure>
