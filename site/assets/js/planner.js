(() => {
  const form = document.querySelector("[data-planner]");
  if (!form) return;
  const alpha = form.querySelector("[name=alpha]");
  const out = form.querySelector("[data-ncal]");
  const note = form.querySelector("[data-note]");

  const required = (a) => Math.ceil(1 / a) - 1;

  const paint = () => {
    const a = Number(alpha.value);
    if (!Number.isFinite(a) || a <= 0 || a >= 1) {
      out.textContent = "—";
      note.textContent = "α must be in (0, 1).";
      return;
    }
    const n = required(a);
    out.textContent = String(n);
    let extra = "";
    if (Math.abs(a - 0.1) < 1e-9) extra = " At α_miss = 0.10 the floor costs 9 defectives.";
    if (Math.abs(a - 0.05) < 1e-9) extra = " At α_fr = 0.05 the floor costs 19 goods.";
    note.textContent = `n_cal ≥ ⌈1/α⌉ − 1. Floor α_min = 1/(n_cal+1).${extra} This calculator does not invent plant throughputs.`;
  };

  alpha.addEventListener("input", paint);
  paint();
})();
