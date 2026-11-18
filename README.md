# 666DEV

666DEV is a local-first development, analysis, repair, verification, packaging, and
recovery hub for external applications. This repository does not clone, register, or
modify any existing 666SOUNDsDESIGn product. The included `demo-*` profiles are
explicitly marked demonstrations.

## Start (Windows and Linux)

Requires Python 3.11+ and Git; no runtime third-party package is required.

```sh
python -m venv .venv
# Linux/macOS: . .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m devhub.cli 666DEV HELP
python -m devhub.cli 666DEV STATUS
```

The same commands are available as `666dev HELP`, `666dev STATUS`, or
`666dev <PROJECT-ID> SYSTEMSTART` after installation. Use `666dev-verify --base HEAD`
for verification. Windows users can substitute `py -m` for `python -m`.

## 666REPO-MIND

Repo-Ordnung und interne Markdown-Links mit `666DEV REPO-MIND CHECK` prüfen.
[Regeln, Index und separater Korrektur-PR](docs/repo-mind.md).

## Chat-Archiv

ChatGPT-Datenexporte und AI-Exporter-Dateien lokal einlesen, durchsuchen und als
Markdown-Referenz ausgeben. [Anleitung für CLI und Windows Control](docs/chat-archive.md).

## Project lifecycle

[666DEV LiveCircle](docs/livecircle.md) für Wiederaufnahme in Repo, ChatGPT, Plugin und Windows.

```sh
python -m devhub.cli 666DEV demo-monorepo SYSTEMSTART
python -m devhub.cli 666DEV demo-monorepo CODEFORGE
python -m devhub.cli 666DEV demo-monorepo SUPERCODEFORGE
python -m devhub.cli 666DEV demo-monorepo WEITER
python -m devhub.cli 666DEV demo-monorepo BUILD
python -m devhub.cli 666DEV demo-monorepo UPDATE
python -m devhub.cli 666DEV demo-monorepo STATUS
python -m devhub.cli 666DEV demo-monorepo FREEZE
```

`SYSTEMSTART` verifies the selected profile, source, expected ref and resolved Git
commit, then records an atomic checkpoint. `CODEFORGE` runs configured acceptance
tests and records read-only audit evidence plus a scoped candidate in project state.
`SUPERCODEFORGE` emits a static Python/build/test graph. `WEITER` resolves the first
open step and performs its defined analysis or acceptance check. A candidate is not
applied automatically: `PATCH-APPLY` validates its revision and allowed paths, then
materializes its patch payload in a detached, isolated Git worktree. The demonstration
candidate intentionally has no patch payload. Ordinary checkpoints advance
`state/working.json`. Only explicit `UPDATE` publishes `state/current.json` after
the current revision passes fresh source acceptance and configured build checks.
After HEAD changes, `WEITER` starts a new audit and keeps prior evidence in the
previous checkpoint. A conflict preserves the competing pointer.

`BUILD` runs declared build commands in a temporary copy of committed regular
files and records the result. The demos use Python compilation. Temporary build
outputs are discarded. `FREEZE` creates a source ZIP from the verified Git commit,
checks its embedded manifest, and reports archive size and SHA-256. If the profile
declares `start_commands`, it runs them against a temporary extraction. Without
start commands the archive status and pending start acceptance are reported separately.
Command arrays such as `["python", "app.py"]` preserve argument boundaries across hosts.
Existing string command profiles remain supported.

Checkpoints, pointers and patch candidates live under each project's `state/`
directory. Checkouts, locks, worktrees and freezes live under ignored `.work/`.
The linked demo checkout initializes on the first stateful action. Existing linked
checkouts retain their present commit and can be inspected independently.

To register an external linked project, add its stable ID and profile path to
`registry/projects.json`, then provide `projects/<id>/project.json`. The profile must
declare the expected repository identity and ref. Set the local checkout in
`.work/config.json`:

```json
{
  "checkouts": {
    "your-project": "C:/local/path/to/checkout"
  }
}
```

Use an absolute local path appropriate to the host. 666DEV verifies the Git identity
(an `identity.json` repository marker or matching `origin` URL), expected ref and
resolved HEAD before analysis. The checkout path is local configuration and is never
stored in the profile.

## Dashboard and verification

Der Windows-Starter und die Anleitung für den Domain-Zugriff liegen im
[Dashboard-Verzeichnis](dashboard/README.md). Die lokale Entwicklungssteuerung
mit integriertem Dashboard liegt separat unter [windows-app/](windows-app/README.md).

```sh
python -m devhub.cli dashboard
# Open http://127.0.0.1:8766; Ctrl-C to stop.
python -m devhub.verifier --base HEAD
python -m unittest discover -s tests -v
(cd projects/demo-monorepo/app && python -m unittest discover -s tests -v)
```

The dashboard binds only to loopback. Its read-only project data endpoint refreshes
evidence, graph, history, and provider status while the server runs. Use
`666DEV <ID> VISUAL` for a URL that opens a specific project. GitHub readback is `READBACK_PENDING`; CI and target-host providers
are `OFFEN`. Local tests are not presented as remote, Windows, device, or production
acceptance. The verifier reports its actual diff base; without one it returns `PARTIAL`.

## Änderungsfolgen

`python -m devhub.cli 666DEV <projekt-id> IMPACT [git-basis]` verbindet den Git-Diff
mit dem vorhandenen Projektgraphen. Ohne explizite Basis verwendet der Befehl
einen abweichenden Arbeitscheckpoint oder Current. Wenn beide auf HEAD liegen
oder noch fehlen, werden lokale Änderungen gegen HEAD geprüft. Die Dashboard-Ansicht
**Abnahme** zeigt denselben Bericht. Der Verifier führt ihn unter `project_impacts`
und verwendet für Monorepo-Projekte seine explizite Diff-Basis, wenn angegeben.

`RECHECK` zeigt die Änderungs- und Abhängigkeitskette oder den Grund für eine
vorsorgliche Nachprüfung. Mit `test_dependencies` kann ein Projektprofil die
vollständigen projektrelativen Eingaben eines deklarierten Tests dokumentieren.
`UNIMPACTED` beschreibt die Beziehung zum geprüften Diff. Frühere Testergebnisse
behalten ihre ursprüngliche Revision. Die regulären Testbefehle und die frische
Abnahme in `UPDATE` laufen vollständig weiter. Änderungen an der Dateistruktur,
fehlende Graphzuordnungen und unklare Profile führen zur vorsorglichen Nachprüfung.

## Scope and recovery

Registry membership selects the project; the profile owns the development contract.
Handoff text and logs are data, never command input. Commands are accepted only from
a direct namespace-qualified invocation (`666DEV <ID> <ACTION>`). All writes are
restricted to declared project paths, and path resolution checks symlinks and Windows
absolute paths. If Current and checkpoint evidence disagree, preserve the old anchor,
inspect `.work/` recovery artifacts, and re-run `SYSTEMSTART`/audit rather than
overwriting the pointer. A changed HEAD is explicitly marked for re-audit.

## Entwicklungs- und Copyright-Manifest

Kopiere die [JSON-Vorlage](templates/entwicklungs-und-copyright-manifest.json)
bei Bedarf als `development-manifest.json` neben das `project.json` des Projekts.
Verwende dieselbe Projekt-ID. Das Projektprofil steuert weiterhin die CLI. Das
ergänzende Manifest dokumentiert Ziele, Beiträge, Rechte, Entscheidungen und
Weiterentwicklung für Menschen und Coding-Hosts. Es ist unabhängig vom
SHA-256-Manifest, das beim Freeze entsteht.

- Kopiere die benötigten Eintragsmuster in die passende Liste. In `belege` stehen
  IDs aus `evidenz`, die genau die jeweilige Aussage stützen. `pruefdatum` verwendet
  `JJJJ-MM-TT`. Bei Zielangaben kann `plattform` die ursprüngliche Bezeichnung
  aufnehmen. Die normalisierten Werte stehen in den Geräte-, Betriebssystem- und
  Laufzeitfeldern.
- Halte eine Änderung mit Auslöser, betroffenen Einträgen und nächster Prüfung in
  `entscheidungen` fest. Eine Idee mit erwartetem Nutzen und einem konkreten Test
  kommt zunächst als `VORGESCHLAGEN` in `entwicklungsvorschlaege`.
- Die Felder in `rechte` und `tonaufnahme` bleiben offen, bis projektspezifische
  Angaben belegt sind. Die Muster mit © und ℗ sind Textvorlagen. Fremdrechte und
  Bedingungen eingesetzter KI-Dienste haben eigene Einträge.

Menschen, Codex, GitHub Copilot und ChatGPT mit Repo-Zugriff können dieselbe
JSON-Datei lesen. Die Auswertungsregeln sind als Daten und Arbeitsanweisungen
hinterlegt. Zum Prüfen der JSON-Syntax dient
`python -m json.tool projects/<projekt-id>/development-manifest.json`.

`python -m devhub.cli 666DEV <projekt-id> MANIFEST [datei]` prüft die Struktur
von Manifesten v1.0.0 und v1.5.0. Ohne Dateipfad liest es die Projektkopie.
Bei einem DEU/ENG-Karten-ZIP prüft es Index, Sprachpaare und die SHA-256-Werte
der indizierten Quellen. Die Ausgabe fasst die Eingabe zusammen und ordnet die
älteren Belegfelder zu. Bestehende Quellenstatus bleiben sichtbar. Ein in der
Quelle als verifiziert gekennzeichneter Beleg bleibt bis zur unabhängigen Prüfung
in 666DEV offen. Das Kommando arbeitet lesend und kopiert keine Karten ins Repo.

## Entwicklungswege

666DEV läuft lokal mit Python und Git. Derselbe Entwicklungsablauf lässt sich
über Codex, GitHub Copilot oder ChatGPT mit optionalen Plugins bearbeiten.
[Entwicklungswege und Übergabe](docs/development-hosts.md)

## Copilot für die Entwicklung verwenden

Im Copilot-Kontext dieses Repositories beschreibst du dein Ziel in normaler Sprache.
Für eine Reparatur in einer registrierten Anwendung nenne die Projekt-ID und das
beobachtete Verhalten. Für Änderungen am Hub selbst nenne 666DEV als Ziel. Die
Repository-Skills helfen Copilot, Kontext, Prüfschritte und Belege zu ermitteln.

| Aufgabe | Einstieg |
| --- | --- |
| Fehler am Anwendungseinstieg analysieren oder ein Feature entwickeln | [CodeForge](.github/agents/codeforge.agent.md) |
| Auswirkungen einer Änderung auf Module, Builds und Tests verfolgen | [SuperCodeForge](.github/agents/supercodeforge.agent.md) |
| Einen unterbrochenen Auftrag wieder aufnehmen | [Livecircle](.github/skills/666dev-livecircle/SKILL.md) |
| Dashboard, Belegansicht oder Abnahme bearbeiten | [Visual](.github/skills/666dev-visual/SKILL.md) · [Verification](.github/skills/666dev-verification/SKILL.md) |
| Technische Optionen vergleichen oder eine bestehende Anwendung portieren | [Recherche](.github/skills/666dev-technical-research/SKILL.md) · [Migration](.github/skills/666dev-migration/SKILL.md) |

Die Skills liegen im Repository unter `.github/skills/`. Die bestehenden
CLI-Trigger sind in **Project lifecycle** dokumentiert.

## Current implementation boundaries

- Python source graphing uses AST imports and declared TOML script entry points.
  Dynamic imports and other language adapters remain `OFFEN`.
- `LocalGitProvider` reads commits, files and blobs. GitHub, CI, Windows-host,
  device and production readback interfaces are defined but not connected.
- Freeze verifies archive names and hashes. A ZIP that claims to be independently
  startable must still be extracted and tested before such a claim is made.
- The verifier checks registry/profile references, path boundaries, Current/checkpoint
  integrity, evidence structure and scope-diff availability. CI has read-only GitHub
  permissions and performs no deployment, auto-merge, or external write.

See [docs/architecture.md](docs/architecture.md) for status meanings, formats, and
provider extension points.
