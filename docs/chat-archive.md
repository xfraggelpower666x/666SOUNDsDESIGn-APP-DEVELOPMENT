# Chat-Archiv in 666DEV

Der gemeinsame Python-Kern indexiert Chat-Titel und Nachrichten aus ausgewählten
lokalen Exportdateien. CLI und Windows Control verwenden denselben Datenbestand.

## Windows Control

Anwendung wie gewohnt starten und **Repo Mind → Chat-Archiv** öffnen. Im Explorer den Export
mit **Als Pfad kopieren** auswählen, den Pfad einfügen und importieren. Über die
Suche lassen sich Titel und Nachrichtentext durchsuchen. Ein leeres Suchfeld zeigt
die 50 zuletzt neu eingelesenen Chat-Stände. **Markdown exportieren** erstellt eine
Referenz mit Quellenformat, Archivschlüssel und Text des gewählten Chats.

## Kommandozeile

```text
666dev CHAT-ARCHIVE IMPORT "C:\Users\Name\Downloads\chat-export.zip"
666dev CHAT-ARCHIVE SEARCH "666STREAM"
666dev CHAT-ARCHIVE EXPORT <64-stelliger Schlüssel aus der Suche>
```

Ohne installiertes Skript funktioniert `python -m devhub.cli 666DEV CHAT-ARCHIVE …`
mit `src` im Python-Suchpfad. Der Markdown-Export geht an die Standardausgabe.
Der Schlüssel identifiziert den konkreten Chat-Stand. Identische Stände werden
beim erneuten Import anhand von Quell-ID, Titel und Nachrichten erkannt.
Geänderte Stände bleiben als eigene Treffer erhalten.

## Formate und Speicherung

- Offizieller ChatGPT-Datenexport als JSON oder ZIP mit `conversations.json` bzw.
  nummerierten `conversations-*.json` im Wurzelordner des ZIPs. Der Index liest
  Textnachrichten aus dem aktiven Zweig des vorhandenen Chatbaums. Alternativzweige,
  Anhänge, Bilder, Projekteinstellungen und Kontodaten bleiben im Originalexport.
- AI Exporter 1.8.0 als Universal JSON oder OpenAI JSON, auch im erzeugten ZIP.
  Enthält das ZIP beide Darstellungen, hat Universal JSON Vorrang. Die ZIPs mit dem
  Quellcode sind keine Chat-Exporte.
- Maximal 128 MiB pro JSON-Datei und insgesamt 512 MiB an ausgewählten JSON-Dateien
  pro ZIP. Bei einem Dateifehler wird der laufende Import zurückgerollt.
- Der Index liegt im ignorierten Pfad `.work/chat-archive/archive.sqlite3`.
  Chattexte liegen dort unverschlüsselt. Der Import erfordert keinen Dienst,
  keine Anmeldung und keinen API-Schlüssel. Das Archiv enthält keine Projekt-Current-
  oder Checkpoint-Daten. Wer den Index zurücksetzen will, kann die Datenbank bei
  geschlossener Anwendung verschieben oder löschen.

Eine Markdown-Referenz kann in einem Folgechat als Quelle mitgegeben werden.
Für native 666DEV-Projektzustände bleibt der referenzgebundene LiveCircle-Handoff
zuständig. Der Archivexport führt keine gespeicherten Nachrichten oder Befehle aus.
