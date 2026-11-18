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
    get("mind-target").value = state.config.ref;
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
function downloadText(content, name, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function refreshCircle({handoff, download = false} = {}) {
  const project = get("project").value;
  if (!csrf || !project) return;
  const panel = get("livecircle-output");
  get("desktop-impact-status").textContent = "";
  get("livecircle-project").textContent = project;
  try {
    const data = handoff === undefined ? {project} : {project, handoff};
    const desktopBase = get("desktop-base").value.trim();
    if (desktopBase) data.desktop_base = desktopBase;
    const snapshot = await request("/api/livecircle", data);
    const result = JSON.stringify(snapshot, null, 2);
    panel.textContent = result;
    const impact = (snapshot.livecircle || snapshot).desktop_impact;
    const desktopMessages = {
      WINDOWS_REVIEW_REQUIRED: "Windows-App prüfen. Die betroffenen Funktionen stehen im Bericht.",
      NO_IMPACT_IN_DIFF: "Im verglichenen Git-Bereich ist keine Windows-Auswirkung erkennbar.",
      READBACK_PENDING: "Windows-Abgleich offen. Eine belegte Git-Referenz angeben.",
    };
    get("desktop-impact-status").textContent = desktopMessages[impact?.status] || "";
    if (download) {
      downloadText(result, `666dev-${project}-handoff.json`, "application/json");
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
let mindReview;
let mindBusy = false;
function setMindReview(review) {
  mindReview = review;
  const usable = Boolean(review?.diff);
  get("mind-diff").hidden = !usable;
  get("mind-diff-heading").hidden = !usable;
  get("mind-diff").textContent = review?.diff || "";
  get("mind-download").disabled = !usable;
  get("mind-publish").disabled = !usable || !review.rename_base;
}

async function mindAction(data) {
  if (!csrf || mindBusy) return;
  mindBusy = true;
  const panel = get("mind-output");
  const status = get("mind-status");
  status.textContent = "Aktion läuft …";
  try {
    const response = await request("/api/repo-mind", data);
    const {diff, ...summary} = response;
    panel.textContent = JSON.stringify(summary, null, 2);
    if (data.action === "review") {
      if (get("mind-base").value.trim() !== data.base || get("mind-target").value.trim() !== data.target) {
        status.textContent = "Die Eingaben haben sich geändert. Prüfe den Stand erneut.";
        return;
      }
      setMindReview(response);
      status.textContent = `${response.findings.length} Befunde · ${response.eligible_fixes} eindeutige Korrekturen`;
      return;
    }
    status.textContent = response.status || "Quellkontext gelesen.";
  } catch (error) {
    status.textContent = error.message;
    panel.textContent = "";
  } finally {
    mindBusy = false;
  }
}

get("mind-context").addEventListener("submit", event => {
  event.preventDefault();
  if (mindBusy) return;
  setMindReview(null);
  const paths = get("mind-paths").value.split("\n").map(path => path.trim()).filter(Boolean);
  mindAction({action: "context", instruction: get("mind-instruction").value, paths});
});
get("mind-review").addEventListener("submit", event => {
  event.preventDefault();
  if (mindBusy) return;
  setMindReview(null);
  mindAction({action: "review", base: get("mind-base").value.trim(), target: get("mind-target").value.trim()});
});
get("mind-index").addEventListener("click", () => {
  if (mindBusy) return;
  setMindReview(null);
  mindAction({action: "index"});
});
for (const key of ["mind-base", "mind-target"]) {
  get(key).addEventListener("input", () => setMindReview(null));
}
get("mind-download").addEventListener("click", () => {
  if (mindReview?.diff) downloadText(mindReview.diff, "666repo-mind.patch", "text/plain");
});
get("mind-publish").addEventListener("click", () => {
  if (!mindReview?.diff || mindBusy) return;
  get("mind-confirm-summary").textContent =
    `${mindReview.eligible_fixes} Linkkorrekturen für ${mindReview.target_branch} · Commit ${mindReview.commit.slice(0, 12)}`;
  get("mind-confirm").showModal();
});
get("mind-confirm").addEventListener("close", () => {
  const dialog = get("mind-confirm");
  if (dialog.returnValue === "publish" && mindReview?.diff) {
    const {rename_base, target_branch, review_sha256} = mindReview;
    setMindReview(null);
    mindAction({action: "publish", base: rename_base, target: target_branch, review_sha256});
  }
  dialog.returnValue = "";
});
initialize();
