# Privates Plugin 666DEV Coding Control

Die zentralen Projektregeln und der LiveCircle liegen in
[der Haupt-Repo](../docs/livecircle.md). Dieses Verzeichnis enthält den
reproduzierbaren Paketbau. Das Quellpaket L.Y.V.R.A. CODING PROFI 0.75.0 wird
über seinen SHA-256 identifiziert und bleibt für einen Neubau erforderlich.

```powershell
py plugin/build.py "L.Y.V.R.A. CODING PROFI (3).zip" 666dev-coding-control.zip
```

Das private Plugin übernimmt Fachskills, Referenzen, ToolStarter und die
GitHub-App-Verbindung aus dem Quellpaket. Es erhält eine eigene 666DEV-Identität.
Die frühere LiveCircle-Facette verweist im neuen Paket auf den nativen
666DEV-LiveCircle. Das Quellplugin wird beim Paketbau nicht verändert.
Die GitHub-Verbindung dient dem autorisierten Lesezugriff auf Quellen.
Lokale Tests, Build und andere Host-Aktionen brauchen einen passenden
Checkout mit Ausführungszugriff. Ein lokaler Handoff gelangt per Export
und ausdrücklicher Übergabe in einen anderen Host.
