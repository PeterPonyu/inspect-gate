(() => {
  const dialog = document.querySelector("dialog.lb");
  if (!dialog) return;
  const img = dialog.querySelector("img");
  const cap = dialog.querySelector("[data-lb-cap]");
  document.querySelectorAll("[data-lightbox]").forEach((node) => {
    node.addEventListener("click", () => {
      img.src = node.currentSrc || node.src;
      img.alt = node.alt || "";
      img.hidden = false;
      cap.textContent = node.getAttribute("data-lightbox") || node.alt || "";
      dialog.showModal();
    });
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => {
    img.removeAttribute("src");
    img.alt = "";
    img.hidden = true;
  });
})();
