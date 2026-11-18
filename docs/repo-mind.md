# 666REPO-MIND in 666DEV

`registry/repo-mind.json` definiert die erlaubten und erforderlichen Wurzeln, den
generierten Index und die Markdown-Dateien, für die der Hub selbst schreiben darf.
Repo Mind arbeitet anhand des festgehaltenen Git HEAD. Lokale Zwischenstände
bleiben unberührt.

| Befehl | Ergebnis |
| --- | --- |
| `666DEV REPO-MIND CHECK [RENAME-BASE]` | Meldet Strukturabweichungen und nicht auflösbare interne Markdown-Dateilinks. Mit Basis erkennt es belegte Zielwechsel. |
| `666DEV REPO-MIND INDEX` | Erzeugt den ausdrücklich als generiert deklarierten Dateiindex `.work/repo-mind/file-index.json` erneut. Er enthält Commit, Pfade, Git-Modi und Objekt-IDs. |
| `666DEV REPO-MIND PR <RENAME-BASE> <TARGET-BRANCH>` | Veröffentlicht eindeutig belegte Linkkorrekturen in einem separaten PR. Erfordert Git, eine angemeldete GitHub CLI und Schreibrechte am Repo. Der Zielbranch auf GitHub muss dem lokalen HEAD entsprechen. |

`RENAME-BASE` ist der Git-Stand, an dem die ursprünglichen Linkziele noch
vorhanden waren. Für eine automatische Reparatur muss eine ehemalige Markdown-Datei
in dieser Basis genau einmal vorkommen und ein exakt identischer Git-Blob muss
heute an genau einem neuen Pfad liegen. Query und Fragment bleiben erhalten.

Der Scanner unterstützt relative Ziele in einzeiligen Markdown-Links und
Referenzdefinitionen. Er klammert Codeblöcke, Zeilen mit Inline-Code, Zitate,
Kommentare und Frontmatter aus. Externe URLs, reine Sprungmarken und HTML-Links
gehören nicht zur Dateilink-Prüfung. Sprungmarken in Dateilinks werden beim
Umschreiben erhalten und unabhängig davon nicht validiert.

Automatische PRs beschränken sich auf freigegebene Hub-Dokumentation.
Projektübergreifende, mehrdeutige oder außerhalb dieses Schreibbereichs liegende
Verweise bleiben zur Prüfung. Strukturabweichungen liefern Anlass zur Prüfung
möglicher Verschiebungen oder Aufräumarbeiten. Aus ihnen wird kein Löschauftrag
abgeleitet. Änderungen an Quellcode, Projektordnern, Build-Verträgen oder
öffentlichen Schnittstellen brauchen einen eigenen geprüften Vorschlag.

Der Korrektur-Commit entsteht in einem temporären Git-Worktree. Der reguläre
Checkout bleibt verfügbar. Bei einem erneuten Aufruf prüft Repo Mind den
Korrekturbranch gegen den erwarteten Baum. Gibt es keine eindeutige Korrektur,
liefert der Befehl `NO_CHANGES`.

Ausführung aus der Repo-Wurzel:

```sh
python -m devhub.cli 666DEV REPO-MIND CHECK HEAD~1
python -m devhub.cli 666DEV REPO-MIND INDEX
```
