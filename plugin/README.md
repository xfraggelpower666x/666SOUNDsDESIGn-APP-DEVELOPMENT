# Privates Plugin 666DEV Coding Control

Die zentralen Projektregeln und der LiveCircle liegen in
[der Haupt-Repo](../docs/livecircle.md). Dieses Verzeichnis enthält den
reproduzierbaren Paketbau. Das Quellpaket L.Y.V.R.A. CODING PROFI 0.75.0 wird
über seinen SHA-256 identifiziert und bleibt für einen Neubau erforderlich.

**Sicherheitswarnung:** `plugin/build.py` ist ein historischer Builder
für `666dev-coding-control` **v0.1.5**, nicht der aktuelle Provider-Release
**v0.2.2**. Der direkte Aufruf wird deshalb mit `WRITE_BLOCKED` verweigert.
Nur für eine ausdrücklich autorisierte **lokale historische Prüfung**
ist `--allow-legacy-v015` zulässig; die Ausgabe muss im ignorierten
`.work/legacy-plugin-builds/` liegen. Das ist keine Plugin-Veröffentlichung.

```powershell
py plugin/build.py --allow-legacy-v015 "L.Y.V.R.A. CODING PROFI (3).zip" ".work/legacy-plugin-builds/666dev-coding-control-v015-archive.zip"
```

Keine privaten Quelldateien oder erzeugten Plugin-Pakete in das öffentliche
Repository committen. Aktuelle Plugin-Releases nur über den separaten
geprüften Provider-/Host-Veröffentlichungspfad.

Das private Plugin übernimmt Fachskills, Referenzen, ToolStarter und die
GitHub-App-Verbindung aus dem Quellpaket. Es erhält eine eigene 666DEV-Identität.
Die frühere LiveCircle-Facette verweist im neuen Paket auf den nativen
666DEV-LiveCircle. Das Quellplugin wird beim Paketbau nicht verändert.
Die GitHub-Verbindung dient dem autorisierten Lesezugriff auf Quellen.
Lokale Tests, Build und andere Host-Aktionen brauchen einen passenden
Checkout mit Ausführungszugriff. Ein lokaler Handoff gelangt per Export
und ausdrücklicher Übergabe in einen anderen Host.
