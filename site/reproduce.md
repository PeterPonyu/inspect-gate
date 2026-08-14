---
layout: layout.njk
title: Reproduce
description: Zenodo archive, public code, and frozen artifacts.
permalink: /reproduce/
---

<div class="prose">
  <h1>Reproduce</h1>
  <p>
    Scientific interface, not a product quickstart. The protocol listing is how the certificates are issued, not a deploy-to-line invitation.
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

  <h2>Protocol verbs</h2>
  <p>Score convention: higher = more anomalous. The issued objects are:</p>
</div>

<pre class="cli">fit         (t_lo, t_hi) or refuse an axis
route       scores to auto-pass / defer / auto-reject
audit       realized rates against the issued certificates
certify     pool certificates across seeds
report      human-readable digest</pre>

<div class="prose">
  <p>
    Tests are CPU-only and do not require a deep-learning runtime. That is a reproducibility fact, not a product claim.
  </p>
</div>
