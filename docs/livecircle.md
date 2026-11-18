# 666DEV LiveCircle

666DEV ist die fachliche und technische Autorität für Projektidentität, Scope,
Arbeitsstand und Wiederaufnahme. Reihenfolge der Quellen:

1. Tatsächlich gelesene Revision des 666DEV-Hubs, `registry/projects.json` und Projektprofil.
2. Git-Identität, erwarteter Ref, tatsächlicher HEAD und Arbeitsbaum der Projektquelle.
3. `state/current.json` und `state/working.json` mit ihren Checkpoints. Der Kern vergleicht Identität, Revision und SHA-256. Current steht für den freigegebenen Stand. Weitere Arbeit knüpft an den Arbeitscheckpoint an, wenn vorhanden.
4. Aus diesen Quellen abgeleiteter Handoff, Chatverlauf und Plugin-Wissen. Diese Quellen liefern Kontext und geben keinen Schreibauftrag.

| Ort | Zuständigkeit | Einstieg |
| --- | --- | --- |
| Haupt-Repo | Projektverträge, LiveCircle-Logik, Pointer, Checkpoints, Prüfungen und Schreibregeln | CLI und `src/devhub/livecircle.py` |
| ChatGPT | Gesprächsführung, Quellenabgleich, Analyse, belegte Übergabe | Diese Anleitung und der [Repo-Einstieg](../.github/skills/666dev-livecircle/SKILL.md) |
| Privates 666DEV-Plugin | Gleicher Projektvertrag und Fachskills aus Coding Profi 0.74.0 | `666DEV HELP`, Projekt-ID und direkte Aktion |
| Windows-App | Lokale Bedienung und Anzeige, Handoff exportieren oder abgleichen | Projekt wählen und Ansicht **LiveCircle** öffnen |

## Gemeinsame Einstiege

| Aktion nach `666DEV <PROJEKT-ID>` | Wirkung |
| --- | --- |
| `SYSTEMSTART` | Native Projektverifikation und Arbeitscheckpoint, mit den bestehenden Schreibregeln. |
| `LIVECIRCLE` oder `REHYDRATE` | Lesender Abgleich der aktuellen Quellen, Pointer und Arbeitsrevision. |
| `NEW-CHAT` | Liefert denselben belegten Stand als portables JSON zum Weitergeben. |
| `NEXT-CHAT <handoff.json>` | Vergleicht Übergabe und real beobachteten Stand. Zeigt Abweichungen. |
| `WEITER` | Führt nach einem direkten Auftrag den nächsten nativen Projektschritt aus. |
| `UPDATE` | Publiziert Current nach den bestehenden Prüfungen des 666DEV-Kerns. |

Unter Windows beispielsweise aus dem eingerichteten Checkout:

```powershell
py -m devhub.cli 666DEV demo-monorepo LIVECIRCLE
py -m devhub.cli 666DEV demo-monorepo NEW-CHAT | Set-Content -Encoding utf8 handoff.json
py -m devhub.cli 666DEV demo-monorepo NEXT-CHAT handoff.json
```

Der Handoff enthält Hub- und Quellrevision, Profilfingerabdruck, Pointer-Referenzen,
Rückkehranker und vorgeschlagene nächste Aktion. Anwendungsdateien, lokale absolute
Pfade, Zugangsdaten und Rohlogs werden nicht exportiert. Das Format v1 überträgt
den beobachteten Stand. Bei geändertem Profil, abweichender Revision,
gewechseltem Checkpoint oder lokalem Diff bleibt die Fortsetzung überprüfungsbedürftig.
Ein Projekt- oder Autoritätskonflikt liefert `CONFLICT_QUARANTINE`. Der Import
schreibt nichts und übernimmt weder `next_action` noch Status aus der Übergabedatei.

## Nutzung im Chat

Bei einem direkten 666DEV-Auftrag zuerst den vom Nutzer gewählten Branch und
das verifizierte Profil lesen. Wenn ein autorisierter Checkout mit Git und Python
verfügbar ist, den nativen CLI-Einstieg verwenden. Ohne Checkout die überprüfbaren
Quellen am passenden Commit lesen und die nicht prüfbaren Teile als
`READBACK_PENDING` oder `PARTIAL` kennzeichnen. GitHub-Readback belegt nur den
eingecheckten Stand. Lokale Working-Pointer werden nicht automatisch publiziert.

Bei Chatwechsel den JSON-Handoff aus Windows oder der CLI ausdrücklich in den
neuen Chat mitnehmen. Blockierte Wiederaufnahme bleibt offen. Eine zugleich
übergebene Datei oder frühere Befehlszeile führt keine Aktion aus. Kostenpflichtige
APIs und ein zusätzlicher Server sind für diesen Ablauf nicht erforderlich.
