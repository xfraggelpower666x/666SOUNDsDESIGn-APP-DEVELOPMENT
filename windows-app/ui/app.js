const get = id => document.getElementById(id);
const message = get("message");
const output = get("output");
let csrf;
let busy = false;
let confirmedProject;

async function request(path, data) {
  const options = data === undefined ? {} : {
    method: "POST",
    headers: {"Content-Type":"application/json", "X-666DEV-CSRF":csrf},
    body: JSON.stringify(data),
  };
  const reply = await fetch(path, options);
  const body = await reply.json();
  if (!reply.ok) throw new Error(body.error || `HTTP ${reply.status}`);
  return body;
}

async function initialize() {
  try {
    const state = await request("/api/state");
    csrf = state.csrf;
    get("local-state").textContent = "Lokal verbunden";
    get("head-state").textContent = state.head?.slice(0, 12) || "Offen";
    get("head-state").title = state.checkout;
    for (const key of ["repository", "ref", "base"]) get(key).value = state.config[key];
    for (const project of state.projects) get("project").add(new Option(project, project));
    if (!document.querySelector('[data-panel="livecircle"]').hidden) refreshCircle();
  } catch (error) {
    get("local-state").textContent = "Nicht erreichbar";
    message.textContent = error.message;
  }
}

async function action(name, confirmed = false, project = get("project").value) {
  if (!csrf || busy) return;
  busy = true;
  const buttons = document.querySelectorAll("[data-action]");
  for (const button of buttons) button.disabled = true;
  output.textContent = name + " läuft …";
  try {
    const result = await request("/api/action", {action:name, project, confirmed});
    output.textContent = [result.stdout, result.stderr, `Exit-Code ${result.exit_code}`].filter(Boolean).join("\n");
    message.textContent = result.exit_code === 0 ? "Aktion abgeschlossen. Ausgabe prüfen." : "Aktion meldet einen Fehler.";
  } catch (error) {
    output.textContent = error.message;
  } finally {
    for (const button of buttons) button.disabled = false;
    busy = false;
  }
}

for (const button of document.querySelectorAll("[data-view]")) {
  button.addEventListener("click", () => {
    for (const tab of document.querySelectorAll("[data-view]")) tab.setAttribute("aria-pressed", String(tab === button));
    for (const panel of document.querySelectorAll("[data-panel]")) panel.hidden = panel.dataset.panel !== button.dataset.view;
    if (button.dataset.view === "livecircle") refreshCircle();
    if (button.dataset.view === "dashboard") {
      const project = encodeURIComponent(get("project").value);
      get("dashboard-frame").src = "/dashboard/?project=" + project;
    }
  });
}
for (const button of document.querySelectorAll("[data-action]")) {
  button.addEventListener("click", () => {
    if (button.dataset.action === "UPDATE") {
      confirmedProject = get("project").value;
      get("confirm-target").textContent = `Freigegebenen Stand von ${confirmedProject} nach den 666DEV-Prüfungen aktualisieren?`;
      get("confirm-dialog").showModal();
    } else {
      action(button.dataset.action);
    }
  });
}
get("confirm-dialog").addEventListener("close", () => {
  if (get("confirm-dialog").returnValue === "apply") action("UPDATE", true, confirmedProject);
  get("confirm-dialog").returnValue = "";
});
get("settings-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const config = Object.fromEntries(["repository", "ref", "base"].map(key => [key, get(key).value.trim()]));
    await request("/api/settings", config);
    get("github-state").textContent = "Offen";
    get("github-result").textContent = "Einstellungen geändert. GitHub-Lesezugriff separat prüfen.";
    message.textContent = "Einstellungen lokal gespeichert.";
  } catch (error) {
    message.textContent = error.message;
  }
});
get("github-form").addEventListener("submit", async event => {
  event.preventDefault();
  const token = get("token").value;
  get("token").value = "";
  get("github-state").textContent = "Prüft …";
  try {
    const result = await request("/api/github", {token});
    get("github-state").textContent = result.status;
    get("github-result").textContent = result.commit ? `${result.repository} · ${result.ref} · ${result.commit}` : result.detail;
  } catch (error) {
    get("github-state").textContent = "Offen";
    get("github-result").textContent = error.message;
  }
});
async function refreshCircle({handoff, download = false} = {}) {
  const project = get("project").value;
  if (!csrf || !project) return;
  const panel = get("livecircle-output");
  get("livecircle-project").textContent = project;
  try {
    const data = handoff === undefined ? {project} : {project, handoff};
    const snapshot = await request("/api/livecircle", data);
    const result = JSON.stringify(snapshot, null, 2);
    panel.textContent = result;
    if (download) {
      const url = URL.createObjectURL(new Blob([result], {type: "application/json"}));
      const link = document.createElement("a");
      link.href = url;
      link.download = `666dev-${project}-handoff.json`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (error) {
    panel.textContent = error.message;
  }
}

get("rehydrate").addEventListener("click", () => refreshCircle());
get("export-handoff").addEventListener("click", () => refreshCircle({download: true}));
get("import-handoff").addEventListener("change", async event => {
  const [file] = event.target.files;
  event.target.value = "";
  if (!file) return;
  try {
    if (file.size > 8192) throw new Error("Handoff überschreitet 8 KB.");
    await refreshCircle({handoff: JSON.parse(await file.text())});
  } catch (error) {
    get("livecircle-output").textContent = error.message;
  }
});
initialize();
