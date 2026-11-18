# Quellenaudit für 666DEV Coding Control

Vergleichsbasis der Integration ist Hub-Commit
`0ca4665542367f17d03a760f888594068f1f981a` im Integrationsbranch. Erfasst wurden
die 34 verfügbaren ZIP-Inventare. Die Detailprüfung folgt den unten genannten
Dateien. Größen und Dateinamen sind Inventarbelege. Entscheidungen zur
Übernahme stützen sich auf die geprüften Mechanismen. Fremdskripte wurden für
diese Integration nicht ausgeführt.

## Community Skills

Die Hauptquelle enthält 5.266 Dateien und 1.129 verschachtelte `SKILL.md`.
Die Zusatzarchive wurden dateiweise über SHA-256 mit der Hauptquelle verglichen.
Beide ändern `README.md` und `registry.json`, ergänzen eine Root-`SKILL.md`
und lassen die vier Dateien aus `skills/extension-builder/` weg. Die
Migration-Variante lässt außerdem `deep-research-skills/SKILL.md` weg. Die
beiden Branch-Namen sind damit kein Beleg für neue Migration- oder Research-Skills.

| Fundstelle im Community-Hauptarchiv | Nutzen und Auswirkung auf 666DEV |
| --- | --- |
| `systematic-debugging/SKILL.md`, **The Four Phases** und `verification-before-completion/SKILL.md`, **The Gate Function** | Erst Diagnose, danach schreibende Reparatur über den nativen Projektschritt. Bei Quelländerung werden die Prüfbasis und die erneut fälligen Prüfungen im Recovery-Bericht sichtbar. |
| `agentic-development-principles/SKILL.md`, **Current status**, **Next tasks** und **Tried but failed** | Einen fortsetzbaren Arbeitsstand an aktuell belegte Quellen binden. Übergabe und native Pointer werden vor dem Fortsetzen verglichen. |
| `agent-evaluation/SKILL.md`, **Core Concepts**, `test-driven-development/SKILL.md`, **Red-Green-Refactor**, und `backend-testing/SKILL.md`, **Common Issues** | Recovery für gleiche Übergabe, älteren Checkpoint, echte Git-Änderung und unbekannte Basis über den nativen Einstieg prüfen. Windows-HTTP-Test für denselben Vertrag und fremde Autorität. |
| `receiving-code-review/SKILL.md`, **Source-Specific Handling**, und `using-git-worktrees/SKILL.md`, **Safety Verification** | Korrekturen am konkreten Stand prüfen. Die Integration entstand in einem getrennten Git-Worktree am verifizierten PR-Head. |
| `deep-research-skills/SKILL.md`, **Core Workflow**, und `technical-writing/SKILL.md`, **Testing Strategy** | Quellenpfade mit Kontext und Prüfergebnis dokumentieren. Der paketinterne Installations- und Rechercheweg ist an Autohand gebunden. |
| `dotnet-test-migration/SKILL.md`, **Workflow**, und `typescript-refactoring-patterns/SKILL.md`, **Refactoring Patterns** | Relevante Projektmethoden für .NET-Testmigration und TypeScript-Refactorings. Dieser Recovery-Pfad ändert weder ein .NET-Testprojekt noch eine TS-Struktur. |
| `skill-standardization/SKILL.md`, **Standard SKILL.md Structure**, `api-design/SKILL.md` und `state-management/SKILL.md` | Bestehenden nativen Skill als Einstieg und HTTP als Adapter beibehalten. Portablen Handoff und frisch erzeugten Recovery-Bericht unterschiedlich behandeln. |

## SDKs, Repo-Werkzeuge und weitere Archive

| Beleg im Archiv | Übernahme oder weiterer Einsatz |
| --- | --- |
| OpenAI Agents Python, `src/agents/run_state.py`, `_run_state_agent_identity.py`, `extensions/handoff_filters.py`. Pydantic AI, `docs/durable_execution/overview.md`, `docs/output.md`. Swarm, Handoff im `README.md`. | Zustandsübergabe, stabile Identität und strukturierter Bericht. Native 666DEV-Bindung wird weiter geprüft. Das separate SDK, LLM-Aufrufe und Agent-Delegation braucht die deterministische Recovery nicht. |
| Agent Skills, `skills-ref/src/skills_ref/parser.py` und `validator.py`. | Standardisiertes Skill-Format und eindeutige Namen bleiben relevant für den Plugin-Bau. Eine generelle Validierung des gesamten historischen Bestands ist eine eigene Änderung. |
| RepoGPT, `docs/grounded-retrieval.md` und `src/services/indexer/citations.ts`. RepoBrain, `engine`-Modul `hub/retrieval_graph.py`. | Projektbelege und Beziehungsketten an konkrete Revisionen binden. Recovery verwendet den nativen `project_impact`. Die semantische Suchabdeckung über weitere Sprachen ist offen. |
| RepoBrain 1.3.1 und -master, `src/repobrain/file_context.py`. Repo-brain Tree-sitter-Branch und entsprechender Main-Snapshot, `tree_sitter_chunker.py`. Slim-MCP-Archiv, `src/repo_brain/mcp_server.py`. | Strukturtreue Ausschnitte und Aktualität des Index sind relevant für Repo Mind. Gleiche Kernmodule in mehreren Archiven erzeugen keinen zweiten Mechanismus. Mehrsprachige Parser und Aktualisierung des Index sind separat gegen Repo Mind zu prüfen. |
| Simple Evals, `types.py`, MLE-bench-Auswertungslogik, Gym, `gym/core.py`. | Erwartete Zustandsübergänge und unabhängige Sollwerte eignen sich als Testprinzip. Der Recovery-Regressionstest prüft konkrete Git- und HTTP-Ergebnisse. |
| OpenAI Python und Node SDK, `README.md` und Paketmetadaten. | Versionsgebundene Clients bleiben für Projekte mit einer Provider-Anbindung relevant. Die lokale Recovery benötigt Git und den bestehenden Python-Kern. |
| BrainOutside, `README.md`. RepoMind-main, `README.md`. HackingTheRepo-Frontend, Projektinventar. 666REPO-MIND Desktop, ZIP-Inventar. | Versionsgebundene Dokumentation und bestehende UI-Muster sind Referenz. Ein externes Projekt oder ein Fremd-Handoff erhält keine native Schreibautorität. Für einen Vergleich mit dem separaten Desktop-Produkt ist dessen eigene Abnahme erforderlich. |
| BrainIAK, Paketmetadaten und README. Prompt-Sammlung und ChatGPT-Plugins-Katalog, README. | Neurowissenschaftliche Algorithmen und allgemeine Kataloge lösen im belegten Recovery-Pfad kein Problem. |
| L.Y.V.R.A. CODING PROFI `(3)`, Plugin-Manifeste und Skillbestand. | Der reproduzierbare 666DEV-Plugin-Bau verwendet weiterhin die geprüfte 0.75.0-Basis. ZIP `(4)` war in diesem Arbeitsstand nicht lesbar und wird für diesen Vergleich nicht als Nachweis geführt. |

## Einbau und prüfbare Wirkung

- `src/devhub/livecircle.py` erstellt Recovery beim Handoff-Abgleich und
  reicht den Bericht an die Diagnose weiter. `src/devhub/recovery.py` leitet
  Kontext und Projektprüfung aus dem nativen Stand ab.
- Bei abweichender Quellrevision prüft Git die Vorgängerbeziehung. Der
  vorhandene `project_impact` berechnet geänderte Projektpfade und fällige
  Prüfungen. Unvollständige Graphdaten können den Prüfumfang erweitern.
- `windows-app/app.py` verwendet denselben Kern für den Import. Die App zeigt
  Ergebnis und abgeleiteten nächsten Schritt. Der portable Export bleibt v1.
- Der native LiveCircle-Skill beschreibt die Auswahl des Projektvorgehens
  nach dem belegten Befund. Das Plugin-Paket verwendet denselben Vertrag.
- `tests/test_livecircle.py` und `tests/test_windows_app.py` prüfen den Einstieg
  über CLI und HTTP. Der native Windows-Start ist eine gesonderte Abnahme.

## Nachprüfung mit Coding Profi 0.80.0 und den zusätzlichen Uploads

`L.Y.V.R.A. CODING PROFI (5).zip` enthält Plugin-Version 0.80.0. Verglichen
mit dem für 666DEV gepinnten Paket (3) mit Version 0.75.0 enthält ZIP (5)
225 Dateien. 189 davon sind unverändert, 28 geändert, acht neu und keine
entfernt. Der Vergleich beruht auf ZIP-Mitgliedspfaden und Dateiinhalten.
Die Integration übernimmt gezielte Mechanismen in den 666DEV-Kern.

| Quelle oder Dateigruppe | Relevanz, Integration und Grenzen |
| --- | --- |
| `skills/sceeri-agentenlauf-chat/scripts/check_run_evidence.py` und zugehörige Tests | Sollvertrag, tatsächlicher Prozesszustand und Auslieferungsartefakte auseinanderhalten. Native 666DEV-Profile liefern den Sollbefehl. 666DEV zeichnet Prozesszustand, Exitcode, Quelle und Profilfingerabdruck auf. Der LiveCircle wertet passende Belege aus. SHA-256 für konkrete Auslieferungsartefakte gehört weiterhin zum eigenständigen Freeze-Vertrag. |
| `skills/sceeri-coding-profi-livecircle/scripts/checkpoint_review.py`, `tests/test_git_rehydration.py` und `references/checkpoint.md` | Git- und Abhängigkeitsprüfung vor Wiederaufnahme. Die Vorgängerprüfung und gezielte Auswirkungsanalyse liegen bereits in 666DEV. Der neue Guard hält Ergebnisse aus isolierten Patch-Worktrees aus der Abnahme des echten Quellstands heraus. Die Strang- und Ereignisschemata des Quellplugins sind für dessen eigene Checkpoints spezifiziert. |
| `skills/sceeri-code-converter/scripts/compare_trx.py` und `tests/test_compare_trx.py` | Testmigration und Testmengenparität mit Vorher-/Nachher-TRX sind für .NET-Aufträge relevant. Die registrierten 666DEV-Demos laufen über Python. Ein natives .NET-Profil mit TRX-Ausgaben wäre der passende Integrationspunkt. |
| `references/windows-starten-build.md`, ToolStarter-Wrapper, `packaging_tools.py`, `toolstarter.py` und Starter-Vertragstest | Relevante Toolchain-Diagnose und getrennte Setup-/Portable-Abnahmen. Als Kandidaten für den Windows-Starter geführt. Der bestehende 666DEV-Starter besitzt einen eigenen Aufrufvertrag. Ein Austausch erfordert Kompatibilitätsnachweise unter Windows. |
| Weitere geänderte SKILL.md und Referenzen zu App-Code, Engineering, Self-Healing, Research, Testing und Electron | Relevanz als Fachmethoden innerhalb passender Aufgaben. Für diesen Schritt übernimmt der 666DEV-Vertrag die Diagnose anhand von realer Ausführung und den revisionsgebundenen Prüfeinstieg. |
| `openai.yaml` | Gegen die vorhandene ToolStarter-Definition im Paket geprüft. Die Zusatzdatei ergänzt `policy.products` um vier Hostnamen. Das ist Host-Metadatenänderung ohne Effekt auf den nativen Build- oder Recovery-Ablauf. |
| Agents Python (2)/(3), Agent Skills (3), Node (1), Simple Evals (2), MLE-bench (2), Gym (2) und Swarm (2) | Vollständiger ZIP-SHA-256-Abgleich mit den früheren Snapshots ergibt Bytegleichheit. Run-State und Handoff-Filter, getrennte Evaluations-Sollwerte und Zustandsübergänge bleiben methodisch relevant. Der lokale Recovery-Pfad hat keine SDK- oder Benchmark-Runtime-Abhängigkeit. |
| Die drei zusätzlichen OpenAI-Python-ZIPs | Jede Datei ist bytegleich zu einem der zwei schon auditierten Snapshots. Zwischen den zwei verschiedenen Snapshots gibt es vier zusätzliche und 94 inhaltlich geänderte Dateien. Darunter sind Tests für Stream-Modus sowie Budget-, Fehler- und Transportereignisse. Deren Behandlung ist für einen entsprechenden Provider-Adapter relevant. Der 666DEV-Prüfpfad beruht auf lokalen Prozesszuständen. |

Die zusätzliche Laufzeitintegration liegt in `run_acceptance`, der
revisionsgebundenen Auswertung des LiveCircle und der Windows-Anzeige.
Die Gegenproben decken einen echten Exitcode 7, einen fehlenden Prozess,
einen bestandenen Befehl, abweichende Revision, geändertes Profil,
einen isolierten Kandidaten und eine unzulässige Handoff-Behauptung ab.
