---
layout: layout.njk
title: Baseline
description: Dual gate versus single-threshold CRC, binding cells, and illustrative economics.
permalink: /baseline/
---

<div class="prose">
  <h1>Dual gate versus CRC</h1>
  <p>
    G1 is shared with a single-threshold conformal risk-control baseline. G2 is what CRC cannot offer.
    MPDD 0.0% false-reject at 73.1% deferral is a <strong>high-review diagnostic</strong>, not a dual-certificate win:
    auto-reject is empty because G2 is refused in all six categories.
  </p>
  <p>{{ crc.caption }}</p>
</div>

<table>
  <thead>
    <tr>
      <th>Benchmark</th>
      <th>Method</th>
      <th>G1</th>
      <th>G2</th>
      <th class="num">Escaped</th>
      <th class="num">FR</th>
      <th class="num">Deferral</th>
    </tr>
  </thead>
  <tbody>
    {% for row in crc.published %}
      <tr>
        <td>{{ row.benchmark }}{% if row.benchmark != "MVTec AD" %} <span class="tag">exploratory</span>{% endif %}</td>
        <td>{{ row.method }}</td>
        <td class="num">{{ row.g1 }}</td>
        <td class="num">{{ row.g2 }}</td>
        <td class="num">{{ row.escaped }}</td>
        <td class="num">{{ row.fr }}</td>
        <td class="num">{{ row.deferral }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>

<figure class="exhibit">
  <img src="{{ '/figures-web/inspect-fig-crcbaseline-web.svg' | url }}" alt="Stacked CRC comparison: pooled rates, VisA risk-coverage, and both-axis certified fraction." width="1200" height="900" />
  <figcaption>
    Dual gate versus CRC at the same escaped-defect target. Panel (a) pooled rates; (b) VisA risk–coverage companion; (c) both-axis certified fraction (CRC has no G2). Web panels are stacked at readable height; the print figure was height-capped.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-hoc</span>
  <img src="{{ '/figures-web/inspect-fig-binding-escaped-web.svg' | url }}" alt="Binding cells for escaped-defect: naive global best-F1 versus certified gate." width="1200" height="420" />
  <figcaption>
    Binding escaped-defect cells. Naive global best-F1 versus the certified gate. Sticky target at 0.10. Post-hoc exhibit.
  </figcaption>
</figure>

<figure class="exhibit">
  <span class="tag">post-hoc</span>
  <img src="{{ '/figures-web/inspect-fig-binding-fr-web.svg' | url }}" alt="Binding cells for false-reject, including VisA PatchCore capsules 96.8 percent versus 3.7 percent." width="1200" height="420" />
  <figcaption>
    Binding false-reject cells. Sticky target at 0.05. VisA PatchCore capsules are the extreme callout (96.8% versus 3.7%). Post-hoc exhibit.
  </figcaption>
</figure>

<div class="prose">
  <h2>Illustrative economics / latency</h2>
  <p>
    Scenarios (100 / 600 / 3000 parts per hour) are <strong>assumed inputs</strong>, not measured plant rates.
    Routing 2.8 µs versus backbone ~19 ms is the only hardware claim, and it is this work’s hardware.
  </p>
</div>

<figure class="exhibit">
  <span class="tag">illustrative scenarios</span>
  <img src="{{ '/figures-web/inspect-fig-opcost-web.svg' | url }}" alt="Illustrative operating-cost panels under assumed throughput scenarios." width="1200" height="720" />
  <figcaption>
    Illustrative operating-cost comparison under assumed throughputs. Not a landing claim; not “cheaper in every scenario.”
  </figcaption>
</figure>

<table>
  <caption>{{ latency.caption }} Hedge: {{ latency.hedge }}.</caption>
  <thead>
    <tr>
      <th>Component</th>
      <th>Cost</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>
    {% for row in latency.rows %}
      <tr>
        <td>{{ row.component }}</td>
        <td class="num">{{ row.cost }}</td>
        <td>{{ row.notes }}</td>
      </tr>
    {% endfor %}
  </tbody>
</table>
