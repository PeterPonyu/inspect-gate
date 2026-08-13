---
layout: layout.njk
title: Reproduce
description: Zenodo archive, theme repository, frozen artifacts, and CLI as a scientific interface.
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
    <li>Theme repository <a href="{{ site.github }}">{{ site.github }}</a> ({{ site.license }})</li>
  </ul>

  <h2>What is frozen</h2>
  <p>
    Score dumps, analysis digests, and the preregistration freeze log travel with the archive.
    What is <strong>not</strong> in git: staging trees for VisA and MPDD, and weight trees. See the repository data manifest.
  </p>

  <h2>CLI as protocol listing</h2>
  <p>Score convention: higher = more anomalous. Verbs:</p>
</div>

<pre class="cli">calibrate   fit (t_lo, t_hi) or refuse an axis
route       map scores to auto-pass / defer / auto-reject
audit       check realized rates against the issued certificates
certify     pool certificates across seeds
report      emit the human-readable digest</pre>

<div class="prose">
  <p>
    Tests are CPU-only and do not require a deep-learning runtime. That is a reproducibility fact, not a product claim.
  </p>
  <p>
    Figure rebuild under <code>manuscripts/figures-src</code> is for the PDF. Web figures on this companion have their own makefile under <code>site/figures-web-src</code>.
  </p>
</div>
