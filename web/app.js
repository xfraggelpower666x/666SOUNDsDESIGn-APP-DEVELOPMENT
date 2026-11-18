const find = selector => document.querySelector(selector);
const tabs = [...document.querySelectorAll("[data-view]")];
const panels = [...document.querySelectorAll("[data-panel]")];
let data = { projects: [] };
let selected = new URLSearchParams(location.search).get("project");
let view = "overview";
let selectedNode;
let command = "";
let fingerprint;

function text(tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
}

function renderEvidence(target, records) {
  target.replaceChildren();
  if (!records.length) target.append(text("p", "Für diesen Stand liegen keine passenden Belege vor."));
  for (const record of records) {
    const row = text("div", "");
    row.className = "evidence";
    row.append(text("b", `${record.status} · ${record.evidence_type}`),
               text("div", `${record.source} · ${record.commit}`), text("div", record.observed));
    target.append(row);
  }
}

function renderImpact(report) {
  const target = find("#impact");
  target.replaceChildren();
  if (!report || report.error) {
    target.append(text("p", report?.error || "Keine Änderungsanalyse verfügbar."));
    return;
  }
  target.append(text("p", `Git-Basis ${report.base.slice(0, 12)} · HEAD ${report.head.slice(0, 12)}`));
  if (!report.checks.length) target.append(text("p", "Keine Prüffälle im Projektprofil deklariert."));
  for (const check of report.checks) {
    const row = text("div", "");
    row.className = "evidence";
    const status = check.disposition === "RECHECK" ? "Erneut prüfen" : "Unbetroffen laut Projektprofil";
    row.append(text("b", `${status} · ${check.path}`));
    for (const chain of check.chains) row.append(text("div", chain.join(" → ")));
    if (!check.chains.length) row.append(text("div", check.reasons.join("; ")));
    target.append(row);
  }
}

function showView() {
  for (const tab of tabs) tab.setAttribute("aria-pressed", String(tab.dataset.view === view));
  for (const panel of panels) panel.hidden = panel.dataset.panel !== view;
}

function render() {
  const projects = find("#projects");
  projects.replaceChildren();
  for (const project of data.projects) {
    const button = text("button", `${project.name || project.id} · ${project.source_mode || "OFFEN"}`);
    button.setAttribute("aria-pressed", String(project.id === selected));
    button.addEventListener("click", () => {
      selected = project.id;
      selectedNode = undefined;
      const url = new URL(location.href);
      url.searchParams.set("project", selected);
      history.replaceState(null, "", url);
      render();
      projects.querySelector('[aria-pressed="true"]')?.focus();
    });
    projects.append(button);
  }

  const project = data.projects.find(item => item.id === selected);
  const summary = find("#summary");
  const nodes = find("#nodes");
  const detail = find("#details");
  const path = find("#path");
  const timeline = find("#history");
  const copy = find("#copy-command");
  const records = project?.evidence || [];
  for (const node of [summary, nodes, detail, path, timeline]) node.replaceChildren();
  command = "";
  copy.disabled = !project;
  copy.textContent = "CLI-Befehl kopieren";
  showView();
  renderImpact(project?.impact);

  const filter = find("#status-filter").value;
  renderEvidence(find("#evidence"), records.filter(record => filter === "ALL" || record.status === filter));
  renderEvidence(find("#findings"), records.filter(record =>
    ["code-audit", "build-audit", "patch-candidate", "patch-apply", "re-audit"].includes(record.evidence_type)));

  if (!project) {
    summary.append(text("p", "Keine Projekte registriert."));
    return;
  }

  command = `python -m devhub.cli 666DEV ${project.id} ${project.next_action || "SYSTEMSTART"}`;
  if (project.error) {
    summary.append(text("p", project.error), text("p", `CLI: ${command}`));
    return;
  }
  summary.append(text("h2", project.name),
    text("p", `HEAD ${project.commit} · Current ${project.current_commit || "OFFEN"} · ${project.revision_status}`),
    text("p", `Nächster Schritt: ${project.next_step}`), text("p", `CLI: ${command}`));
  timeline.append(text("p", `Arbeitsrevision: ${project.working_commit || "OFFEN"}`),
    text("p", `Letzter Checkpoint: ${project.last_session || "OFFEN"}`),
    text("p", `Rückkehranker: ${project.recovery_anchor || "OFFEN"}`));
  const list = text("ul", "");
  for (const checkpoint of project.history || []) list.append(text("li", checkpoint));
  if (list.childElementCount) timeline.append(list);

  for (const [label, kind] of [["Git-Stand", "git"], ["Quellprüfung", "code-audit"],
    ["Patch-Kandidat", "patch-candidate"], ["Re-Audit", "re-audit"], ["Build", "build"],
    ["Current-Abnahme", "current-acceptance"]]) {
    const latest = records.findLast(record => record.evidence_type === kind);
    const card = text("div", "");
    card.className = "card";
    card.append(text("b", label), text("div", latest?.status || "OFFEN"));
    path.append(card);
  }

  function showNode(node) {
    selectedNode = node?.id;
    detail.textContent = node ? JSON.stringify({
      source: node.source, revision: node.revision,
      related: project.graph.edges.filter(edge => edge.from === node.id || edge.to === node.id),
    }, null, 2) : "Wähle einen Graphknoten.";
  }
  for (const node of project.graph.nodes) {
    const button = text("button", `${node.kind}: ${node.id}`);
    button.addEventListener("click", () => showNode(node));
    nodes.append(button);
  }
  showNode(project.graph.nodes.find(node => node.id === selectedNode));
}

async function refresh() {
  try {
    const response = await fetch("/dashboard.json", { cache: "no-store" });
    if (!response.ok) throw new Error(response.statusText);
    const payload = await response.json();
    const observed = JSON.stringify([payload.projects, payload.providers]);
    if (observed !== fingerprint) {
      data = payload;
      fingerprint = observed;
      if (!data.projects.some(project => project.id === selected)) selected = data.projects[0]?.id;
      const providers = data.providers || {};
      find("#providers").textContent =
        `GitHub: ${providers.github || "OFFEN"}\nCI: ${providers.ci || "OFFEN"}\nZielhost: ${providers.target_host || "OFFEN"}`;
      render();
    }
    find("#connection").textContent = "";
  } catch {
    find("#connection").textContent = "Aktualisierung fehlgeschlagen. Die zuletzt geladenen Daten können veraltet sein.";
  } finally {
    setTimeout(refresh, 2500);
  }
}

for (const tab of tabs) tab.addEventListener("click", () => { view = tab.dataset.view; showView(); });
find("#status-filter").addEventListener("change", render);
find("#copy-command").addEventListener("click", async () => {
  if (!command) return;
  try {
    await navigator.clipboard.writeText(command);
    find("#copy-command").textContent = "CLI-Befehl kopiert";
  } catch {
    find("#copy-command").textContent = command;
  }
});
refresh();
