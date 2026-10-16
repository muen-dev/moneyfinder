// Confirm destructive forms and show progress on slow ones (fetching can take a minute).
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (form.dataset.confirm && !confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  if (form.dataset.busy) {
    const button = form.querySelector("button");
    button.disabled = true;
    button.textContent = form.dataset.busy;
  }
});
