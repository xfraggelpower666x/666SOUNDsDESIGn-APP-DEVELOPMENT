# 666DEV R14 — Host-Execution Receipt Gate

**Native Authority:** 666DEV. Entwicklung auf R13, produktiver Current bleibt unberührt.

## Implementiert

`src/devhub/intelligence/codeforge_host_acceptance.py` erweitert R12/R13
minimalinvasiv um einen echten Originalmodul-Aufruf und revisionsgebundenen
lokalen Receipt. `execute_with_receipt(request, expected_source_commit,
expected_module_blob, branch_fetch, file_fetch)` ruft direkt
`devhub.intelligence.codeforge_host_binding.verify_with_host` auf, anstatt
den Algorithmus zu kopieren oder Connector-Ergebnisse nachzuspielen.

Der prüfende Host muss **beide** tatsächlich autorisierten, lesenden
GitHub-Funktionshandles bereitstellen. Vor jedem Provider-Aufruf werden
`git rev-parse HEAD^{commit}` und das **wirkliche Git-Blob**
`git hash-object src/devhub/intelligence/codeforge_host_binding.py`
gegen die ausdrücklich gepinnten Sollwerte geprüft. Ungültige Request-
Formate, fehlende Handles oder falsche Revisionen bleiben blockiert.

Die originale R12-Logik prüft Quelle, Branch-HEAD, tatsächliche Dateibytes,
Git-Blob und nochmaliges Branch-HEAD. Der R14-Rahmen protokolliert zusätzlich
die **tatsächlich ausgeführten** Callback-Aufrufe (2 Branch + 1 Datei bei
erfolgreichem Source-Readback). Pro SHA-gebundener Ausführung wird ein
append-only JSON-Receipt in ignoriertem `.work/codeforge-host-receipts/`
gespeichert und unabhängig zurückgelesen. Ein vorhandener Receipt blockiert
erneute Provider-Aufrufe (Replay-Guard). Der Receipt enthält Metadaten und
Hashes, nicht den fremden Quelldateiinhalt.

Die neue Operations-Center-Projektion bleibt read-only und ergänzt
**keine achte Facette**. Der bereits existente R10-Executor und
GitHub-Draft-PR-Weg bleiben unverändert.

## Evidenzgrenzen

- **R13:** Tatsächlicher Python-Lauf in GitHub Actions mit öffentlichen REST-
  Callbacks und CLIC-Handoff-Readback (GitHub-Run `45511940652`) ist bereits
  als revisionsgebundene Actions-Evidenz vorhanden.
- **R14 SOURCE/CI:** Neue Tests prüfen Originaladapter-Aufruf,
  SHA-Bindung, Replay-Blockade, Source Drift, ungültige Eingaben und
  append-only lokalen Receipt. Eine bestandene CI bestätigt nur diese
  ausführbare Implementierung und die jeweilige Testumgebung.
- **R14 PLUGIN HOST:** Ein vom Test bereitgestelltes Python-Callable ist
  kein Nachweis, dass die authentifizierte ChatGPT-Plugin-Laufzeit
  diese Datei tatsächlich importiert hat. Deshalb bleibt
  `chatgpt_plugin_host_verified=false`,
  `github_connector_host_verified=false` und
  `host_runtime_identity=UNATTESTED` ohne unabhängige Attestation.
  Der tatsächliche fehlende Schritt ist die ausführbare Einbindung
  **beider** vom Plugin-Host autorisierten GitHub-Handles in denselben
  Originalmodul-Prozess und der unabhängige Readback dessen Receipts.

Keine kostenpflichtigen Provider, keine fremde Schreibautorität, keine
fremden Trigger, keine automatische Plugin-Veröffentlichung, kein
produktiver Merge. Der R08-Historical-Security-Hold und Windows-GUI-
Host-Abnahme bleiben unabhängig offen.
