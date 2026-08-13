(() => {
  const root = document.querySelector("[data-category-map]");
  if (!root) return;

  const raw = root.querySelector("[data-map-json]");
  const data = JSON.parse(raw.textContent);
  const detail = root.querySelector("[data-detail]");

  const describe = (cat, axis) => {
    const certified = axis === "g1" ? cat.g1_cert : cat.g2_cert;
    const rate = axis === "g1" ? cat.g1_rate_pct : cat.g2_rate_pct;
    const lines = [
      `<div><strong>${cat.label}</strong> · ${axis.toUpperCase()}</div>`,
      `<dl>`,
      `<dt>Certificate</dt><dd>${certified ? "issued" : "withheld (hatched)"}</dd>`,
      `<dt>Observed rate</dt><dd>${rate === null || rate === undefined ? "—" : rate.toFixed(2) + "%"}</dd>`,
    ];
    if (cat.n_cal_def !== undefined) {
      lines.push(
        `<dt>n<sub>cal</sub><sup>def</sup></dt><dd>${cat.n_cal_def}</dd>`,
        `<dt>α<sub>min</sub> (G1)</dt><dd>${cat.alpha_min_g1}</dd>`,
        `<dt>n<sub>cal</sub><sup>good</sup></dt><dd>${cat.n_cal_good}</dd>`,
        `<dt>G2 floor</dt><dd>${cat.g2_floor || "—"}</dd>`,
      );
    }
    if (!certified && rate === 0) {
      lines.push(
        `<dt>Reading</dt><dd>Hatched 0.0 is an observed rate with the certificate withheld — not a certified zero-error cell.</dd>`,
      );
    }
    if (certified && rate === 0) {
      lines.push(
        `<dt>Reading</dt><dd>Colored 0.0: certificate issued and no errors observed on this axis.</dd>`,
      );
    }
    lines.push(`</dl>`);
    detail.innerHTML = lines.join("");
  };

  const cellClass = (cat, axis) => {
    const certified = axis === "g1" ? cat.g1_cert : cat.g2_cert;
    const rate = axis === "g1" ? cat.g1_rate_pct : cat.g2_rate_pct;
    if (!certified) return "cell g-hatch";
    if (rate === 0) return "cell g-zero";
    return "cell g-ok";
  };

  for (const bench of data.benchmarks) {
    const section = document.createElement("section");
    section.className = "map-bench";
    const tag = bench.tag === "confirmatory" ? "confirmatory" : "exploratory";
    section.innerHTML = `<h3>${bench.label}</h3><span class="tag">${tag}</span>`;
    const wrap = document.createElement("div");
    wrap.className = "cells";
    for (const cat of bench.categories) {
      for (const axis of ["g1", "g2"]) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = cellClass(cat, axis);
        const certified = axis === "g1" ? cat.g1_cert : cat.g2_cert;
        const rate = axis === "g1" ? cat.g1_rate_pct : cat.g2_rate_pct;
        const rateText = rate === null || rate === undefined ? "—" : rate.toFixed(1);
        btn.innerHTML = `<div class="name">${cat.label}</div><div class="axis">${axis.toUpperCase()} ${certified ? "OK" : "REFUSE"} · ${rateText}%</div>`;
        btn.addEventListener("click", () => describe(cat, axis));
        btn.addEventListener("focus", () => describe(cat, axis));
        wrap.appendChild(btn);
      }
    }
    section.appendChild(wrap);
    root.querySelector("[data-map-root]").appendChild(section);
  }

  detail.innerHTML = "Focus a cell for pool size, floor, and observed rate. Colored 0.0 is certified; hatched 0.0 is observed with the certificate withheld.";
})();
