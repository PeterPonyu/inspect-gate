(() => {
  const root = document.querySelector("[data-mondrian]");
  if (!root) return;
  const select = root.querySelector("[name=category]");
  const rows = [...root.querySelectorAll("tbody tr")];
  const paint = () => {
    const want = select.value;
    rows.forEach((row) => {
      row.hidden = want !== "all" && row.dataset.category !== want;
    });
  };
  select.addEventListener("change", paint);
  paint();
})();
