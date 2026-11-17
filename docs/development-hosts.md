# Entwicklungswege für 666DEV

666DEV benötigt für den lokalen Kern Python und Git. CLI, Registry, Profile,
Tests, Verifier und das lokale Dashboard verwenden keine KI-API. Jeder Host
arbeitet mit denselben Projektverträgen und überprüft seine eigene Tool-Verfügbarkeit.

| Host | Einstieg | Ausführung und Ergebnis |
| --- | --- | --- |
| Lokal | Checkout öffnen und den Startbefehlen im [README](../README.md#start-windows-and-linux) folgen | CLI, Tests, Verifier und Dashboard laufen direkt mit Python und Git. |
| Codex | Checkout und Zielbranch öffnen. [AGENTS.md](../AGENTS.md) und die Einstiege unter `.agents/skills/` verwenden. | Analyse, Patch und Tests im bereitgestellten Checkout. Veröffentlichung setzt den tatsächlichen Schreibzugriff voraus. |
| GitHub Copilot Coding Agent | Das Repository auf GitHub auswählen und einen Auftrag mit Zielprojekt, Ref und Abnahme formulieren. | Die [Copilot-Profile und Skills](../README.md#copilot-für-die-entwicklung-verwenden) verwenden dieselben Projektregeln. Maßgeblich sind der erzeugte PR und seine tatsächlichen Checks. |
| ChatGPT und eigene Coding-Plugins | Autorisiertes Repository auswählen oder den freigegebenen Quellstand, Diff und Kontext im Chat bereitstellen. [AGENTS.md](../AGENTS.md), Projektprofil und passenden [Skill](../.github/skills/) lesen. | Quellen lesen und Änderungen erarbeiten. Tests brauchen einen verfügbaren Checkout und eine Ausführungsumgebung. Veröffentlichungen brauchen einen tatsächlich verfügbaren, separat autorisierten Schreibzugang. |

## Kontext an einen anderen Host übergeben

Im Checkout liefert dieser Befehl eine JSON-Ausgabe für die weitere Arbeit:

```sh
python -m devhub.cli 666DEV demo-monorepo CONTEXT
```

Der Export benennt den Hub-Commit, das Projektprofil, die beobachtete Quellrevision
und die deklarierten Einstiegspunkte, Build-Verträge und Testpfade. Die Revision
bezeichnet den Git-Commit. Prüfe lokale Änderungen separat. Fehlt ein
verifizierbarer Checkout, bleibt die Quellrevision `READBACK_PENDING`. Der Export
initialisiert keinen Checkout und gibt keine lokalen Checkout-Pfade, Remote-URLs
oder Logs aus. Prüfe vor einer Übergabe, welche Dateien und Metadaten für den
Empfänger freigegeben sind.

Ergänze als Arbeitsauftrag Zielverhalten, geplanten Umfang, Abnahme und erwartetes
Ergebnis. Bei einer Fortsetzung gib außerdem den Checkpoint-Verweis, relevante
Änderungen seit dem letzten Nachweis und den nächsten offenen Schritt mit.
Der Empfänger vergleicht den real gelesenen Stand mit der angegebenen Revision.
Ein Handoff liefert Daten und erteilt keine Ausführungsbefugnis.

Der reguläre GitHub-Lesezugang in ChatGPT eignet sich zum Prüfen von Quellen und
Patches. Wenn der ausgewählte Host keine Tests ausführen oder keinen Branch
schreiben kann, bleibt die betreffende Aktion offen. Die Übergabe kann einen
prüfbaren Diff, Testanweisungen und die noch benötigten Nachweise enthalten.
Ein eigenes Plugin darf freigegebene Werkzeuge an denselben Projektvertrag
anbinden. Repo-Skills werden in ChatGPT über ihre Quelltexte verwendet, soweit der
Host sie nicht selbst als Skills lädt.
