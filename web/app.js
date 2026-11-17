const projects = document.querySelector("#projects");
let data;
let selected;

function text(tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
}

function render() {
  projects.replaceChildren();
  for (const project of data.projects) {
    const button = text("button", `${project.name || project.id} · ${project.source_mode || "BLOCKIERT"}`);
    button.setAttribute("aria-pressed", String(project.id === selected));
    button.addEventListener("click", () => { selected = project.id; render(); });
    projects.append(button);
  }
  const project = data.projects.find(item => item.id === selected);
  const summary = document.querySelector("#summary");
  summary.replaceChildren();
  if (project.error) {
    summary.append(text("p", `BLOCKIERT — ${project.error}`));
    return;
  }
  summary.append(text("p", `${project.name} · Current ${project.commit || "OFFEN"} · ${project.revision_status}`));
  summary.append(text("p", `Letzte gültige Session: ${project.last_session || "OFFEN"} · Nächster Schritt: ${project.next_step || "OFFEN"}`));
  summary.append(text("p", `CLI: 666DEV ${project.id} ${project.next_step?.includes("CodeForge") ? "CODEFORGE" : "STATUS"}`));
  const path = document.querySelector("#path");
  path.replaceChildren();
  for (const label of ["Auftrag", "Ursachenanalyse", "Patch-Kandidat", "Re-Audit", "Abnahme"]) {
    const card = document.createElement("div");
    card.className = "card";
    card.append(text("b", label), text("div", label === "Patch-Kandidat" ? "VORGESCHLAGEN" : (project.current ? "EVIDENZ VORHANDEN" : "OFFEN")));
    path.append(card);
  }
  const nodes = document.querySelector("#nodes");
  nodes.replaceChildren();
  const detail = document.querySelector("#details");
  for (const node of project.graph.nodes || []) {
    const button = text("button", `${node.kind}: ${node.id}`);
    button.addEventListener("click", () => { detail.textContent = JSON.stringify({source:node.source, revision:node.revision, related:(project.graph.edges || []).filter(edge => edge.from === node.id || edge.to === node.id)}, null, 2); });
    nodes.append(button);
  }
  if (!project.graph.nodes?.length) nodes.append(text("p", "OFFEN — noch keine Graphdaten vorhanden."));
  const evidence = document.querySelector("#evidence");
  evidence.replaceChildren();
  const records = project.evidence || [];
  if (!records.length) evidence.append(text("p", "OFFEN — SYSTEMSTART erzeugt die ersten Belege."));
  for (const record of records) {
    const row = document.createElement("div");
    row.className = "evidence";
    row.append(text("b", `${record.status} · ${record.evidence_type}`), text("div", `${record.source} · ${record.commit}`), text("div", record.observed));
    evidence.append(row);
  }
}

fetch("dashboard.json").then(response => response.json()).then(payload => {
  data = payload;
  selected = payload.projects[0]?.id;
  render();
}).catch(() => document.querySelector("#summary").append(text("p", "OFFEN — dashboard.json fehlt; starte das lokale Dashboard erneut.")));
