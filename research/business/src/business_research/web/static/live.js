// /live: poll the run's status and render it. Everything goes in with textContent; only https URLs become links.
(function () {
  const root = document.getElementById("live");
  if (!root) return;
  const MARK = { pending: "[ ]", running: "[..]", done: "[ok]", failed: "[x]" };
  const $ = (id) => document.getElementById(id);
  let frameSet = false, formsShown = false, logCount = 0;

  function el(tag, text) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; return e; }
  function https(url) { return typeof url === "string" && url.startsWith("https://") ? url : null; }
  function row(tbody, cells) { const tr = el("tr"); cells.forEach((c) => tr.appendChild(el("td", c ?? ""))); tbody.appendChild(tr); }

  function render(job) {
    $("steps").replaceChildren(...job.steps.map((s) => el("li", `${MARK[s.state] || s.state} ${s.label}`)));

    const log = $("log");
    job.log.slice(logCount).forEach((l) => log.append(`${l.t.toFixed(1).padStart(5)}s  ${l.step.padEnd(7)} ${l.text}\n`));
    if (job.log.length > logCount) log.scrollTop = log.scrollHeight;
    logCount = job.log.length;

    const live = https(job.live_view);
    if (live && !frameSet) {
      $("browser").hidden = false;
      $("live-frame").src = live;
      $("live-link").href = live;
      frameSet = true;
    }

    if ((job.fill || job.done) && job.forms && !formsShown) {
      $("results").hidden = false;
      job.forms.forEach((c) => {
        const li = el("li", `${c.name} (${c.jurisdiction}): `);
        c.forms.forEach((f, i) => {
          const url = https(f.url);
          const a = el(url ? "a" : "span", f.code + (f.title ? ` ${f.title}` : ""));
          if (url) { a.href = url; a.target = "_blank"; a.rel = "noopener noreferrer"; }
          if (i) li.append(", ");
          li.appendChild(a);
        });
        if (c.why) li.append(el("div", `Why: ${c.why}`));
        $("forms").appendChild(li);
      });
      const data = $("data").tBodies[0];
      job.data.forEach((d) => row(data, [d.label, String(d.value), d.source]));
      const filled = $("filled").tBodies[0];
      Object.entries((job.fill || {}).filled || {}).forEach(([k, v]) => row(filled, [k, v.value, `${v.source} (${v.from})`]));
      const needs = ((job.fill || {}).needs_user || []).map((n) => n.field);
      $("needs").textContent = needs.length ? `Needs your input: ${needs.join(", ")}` : "";
      formsShown = true;
    }
    if (job.screenshot && $("shot").hidden) { $("shot").src = job.screenshot; $("shot").hidden = false; }
    const browserStep = job.steps.find((s) => s.id === "browser");
    if (frameSet && browserStep && (browserStep.state === "done" || browserStep.state === "failed") && !$("live-frame").hidden) {
      $("live-frame").src = "about:blank";
      $("live-frame").hidden = true;
      $("live-link").replaceWith(el("p", "Browser session ended. The screenshot of the filled form is under Forms."));
    }
  }

  async function poll() {
    try {
      const res = await fetch(root.dataset.status, { cache: "no-store" });
      if (res.ok) {
        const job = await res.json();
        render(job);
        if (job.done) return;
      }
    } catch (e) { /* retry */ }
    setTimeout(poll, 600);
  }
  poll();
})();
