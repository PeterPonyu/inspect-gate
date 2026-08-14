---
layout: layout.njk
title: Reproduce
description: Zenodo archive, public code, and frozen artifacts.
permalink: /reproduce/
---

<div class="prose">
  <h1>Reproduce</h1>
  <p>
    Frozen scores and digests are in the public archive. The objects are the three-way gate, the G1/G2 certificates, and the refusal rule — not a line-side installer.
  </p>

  <h2>Archives</h2>
  <ul>
    <li>Zenodo concept DOI <a href="{{ site.zenodoConcept | doiHref }}"><code>{{ site.zenodoConcept }}</code></a></li>
    <li>Version 0.4.1 record <a href="{{ site.zenodoVersion | doiHref }}"><code>{{ site.zenodoVersion }}</code></a></li>
    <li>Code <a href="{{ site.github }}">{{ site.github }}</a> ({{ site.license }})</li>
  </ul>

  <h2>What is frozen</h2>
  <p>
    Score dumps, analysis digests, and the preregistration freeze log travel with the archive.
    Staging trees for VisA and MPDD, and weight trees, are not in the public archive.
  </p>

  <h2>Checks</h2>
  <p>
    Tests are CPU-only and do not require a deep-learning runtime. Score convention: higher = more anomalous.
  </p>
</div>
