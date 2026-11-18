# 666DEV Windows Control

Doppelklick auf [START_666DEV_WINDOWS.cmd](START_666DEV_WINDOWS.cmd) im lokalen 666DEV-Git-Checkout. Benötigt werden Git for Windows im PATH und Python ab 3.11. Das Fenster öffnet sich im Edge-App-Modus, sofern Edge verfügbar ist, sonst im Standardbrowser. Die Startkonsole offen lassen. Strg+C beendet den lokalen Server. Es sind keine zusätzlichen Python-Pakete, API-Abos oder Hosting-Dienste erforderlich.

| Ansicht | Funktion |
| --- | --- |
| Steuerung | Projekt wählen, Git-Status, Änderungsfolgen, Verifier und die vorhandenen 666DEV-CLI-Aktionen starten. Ausgabe und Exit-Code erscheinen im Fenster. Current aktualisieren erfordert eine explizite Bestätigung. |
| Dashboard | Dieselbe Projektansicht mit Graph, Nachweisen und Abnahme aus dem 666DEV-Kern. Die Vorauswahl folgt dem aktiven Projekt in der Steuerung. |
| Einstellungen | GitHub-Repository und GitHub-Ref für den lesenden Commit-Abruf sowie lokale Git-Basis. Mit `HEAD` bleibt für Änderungsfolgen die automatische Basisauswahl des Livecircle aktiv. |

Die lokalen Entwicklungsbefehle verwenden den Checkout, aus dem die App gestartet wurde. Das GitHub-Ziel ist die Quelle für den separaten API-Abruf. Für ein privates Repo kann beim Abruf ein Lesetoken mit Zugriff auf Repository-Inhalte eingegeben werden. Das Feld wird beim Absenden geleert. Gespeichert werden ausschließlich Repository, Ref und Prüfbasis unter `.work/windows-app/settings.json`.

Die Steuerung bindet an `http://127.0.0.1:8767`. Der Domain-Zugang verwendet weiter das separate [lesende Dashboard](../dashboard/README.md) auf Port 8766. Beim Einrichten des Tunnels muss das Ziel auf Port 8766 bleiben.

Zum Start ohne Fenster kann aus der Repo-Wurzel `py -3 windows-app\app.py --no-window` verwendet werden.

Über **LiveCircle** lässt sich der belegte Projektstand abgleichen. **Handoff
exportieren** speichert das portable JSON für einen anderen Host. Beim Einlesen
wird die Datei gegen die nativen Quellen geprüft. Details stehen im
[LiveCircle-Vertrag](../docs/livecircle.md).

## 666REPO-MIND

Im Tab **Repo Mind** stehen der Quellkontext und die Ordnungsprüfung im selben
Fenster bereit. **Quellkontext prüfen** übernimmt aus Desktop v0.3.1 die
Dateipriorisierung und Python-Fundstellen anhand von Commit, Tree und Blob.
Die Auswahl arbeitet mit dem ausgecheckten 666DEV-Repository.

**Ordnung prüfen** und **Index neu erzeugen** verwenden die bestehenden
[Repo-Mind-Regeln und Funktionen](../docs/repo-mind.md). Ein sicher zuordenbarer
Markdown-Link erscheint im Review mit Diff und Prüfsumme. Der Diff ist als
Patch speicherbar. **Draft-PR freigeben** verlangt eine ausdrückliche Bestätigung
und prüft den Review vor Veröffentlichung erneut. Der separate Draft-PR
benötigt GitHub CLI mit Schreibzugriff sowie einen Zielbranch auf dem geprüften HEAD.

Diese Integration verwendet den lokalen Git-Pfad des Desktop-Pakets.
Der separate modellgestützte Job-/Refine-Dienst und seine SQLite-Datenbank bleiben
Funktionen von Repo Mind Desktop v0.3.1.

Im Tab **LiveCircle** zeigt der Windows-Abgleich betroffene PC-Funktionen.
Für den vollständigen Vergleich seit deiner Installation gib die letzte
belegte PC-Revision ein und wähle **Stand abgleichen**. Details stehen im
[LiveCircle-Vertrag](../docs/livecircle.md#pflichtabgleich-mit-der-windows-anwendung).
