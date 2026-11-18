---
name: 666dev-livecircle
description: Prüft Quellenstand, Current, Checkpoint und Wiederaufnahme in 666DEV. Bei SYSTEMSTART, WEITER, UPDATE, FUCK HORST, Handoffs, HEAD-Wechsel und Recovery verwenden.
---

# 666dev-livecircle

## Direkte Chat-Einstiege

Führe `666DEV SYSTEMSTART`, `666DEV UPDATE` und `666DEV FUCK HORST` auch ohne
Argument als direkte Chat-Nachrichten nach dem
[LiveCircle-Vertrag](../../../docs/livecircle.md#direkte-chat-trigger) aus.
Prüfe vor der Rehydration Autorität, belegte Projektbindung und Scope. Bleibt
das Projekt offen, frage nach der Projekt-ID. Bei `FUCK HORST` bleibt Recovery
lesend und auf den belegten Kontext begrenzt. Diagnose, Nachweis und Ausführung
sind getrennte Ergebnisse.

## Wiederaufnahme

- Ermittle zuerst Projekt-ID, Profil, Quellmodus und tatsächlichen HEAD. Lies anschließend Current, Checkpoint, Hash, Basisrevision, Scope, Rückkehranker und offenen Schritt. Prüfe Arbeitsbaum und betroffene Pfade.
- Unterscheide freigegebenen Current, Arbeitscheckpoint und Recovery-Kopie. Der Sollvertrag reserviert Current-Schreibvorgänge für ausdrücklich beauftragte Updates. Prüfe vor einem CLI-Aufruf seine tatsächlichen Seiteneffekte. Bestehende Abweichungen im Code sind Befunde. Bei einer Lesesitzung verwende die lesenden Einstiege oder direkte Dateiprüfung.
- Bei HEAD-Wechsel nutze einen exakten, passenden Nachweis oder eine verifizierte Vorgängerrevision als Vergleichsbasis. Prüfe betroffene Pfade, Abhängigkeiten, Eingaben und Umgebung. Prüfe die dadurch entwerteten Nachweise erneut. Bei divergierender Basis prüfe den Stand neu und dokumentiere den Konflikt.
- Setze am ersten fachlich und technisch freigegebenen offenen Schritt fort. Prüfe vor einem Wiederholungsversuch, ob ein Seiteneffekt bereits eingetreten ist. Sichere konkurrierende Stände und blockiere den betroffenen Schreibschritt bei einem Konflikt.
- Halte im Handoff Ziel, beobachteten Commit, belegte Arbeit, offene Nachweise und die nächste ausführbare Aktion fest. Bei einem autorisierten Update sichere den Ausgangsstand und prüfe Zustandskörper und Referenzen. Schreibe den Current-Pointer zuletzt und lies ihn direkt zurück.

## Recovery in der Praxis

Verwende `NEXT-CHAT` für importierte Übergaben. Lies `recovery.context` für
den Wiederaufbau des Arbeitskontexts und `recovery.project` für belegte
Projektarbeit. Bei einem bestätigten Quellenwechsel liefert `impact` die
Git-Basis und den Umfang der erneut fälligen Prüfungen. Führe den vorgeschlagenen
lesenden `IMPACT` aus, wenn du die betroffenen Pfade und Prüfketten brauchst.
Ein angebotener nativer Folgebefehl begründet keine Ausführung.

| Befund im nativen Ergebnis | Vorgehen im Coding-Auftrag |
| --- | --- |
| `REBUILD_FROM_NATIVE` | Rekonstruiere den Chatkontext aus Registry, Profil, Revision und aktuellen Pointern. Prüfe die zuletzt belegte Nebenwirkung vor einer Wiederholung. |
| `REVALIDATE_PROJECT` | Verwende Ursachenanalyse und Repo-Analyse. Folge den betroffenen Pfaden bis zur Prüfung. Bei unvollständiger Zuordnung verwende den breiteren vom Projekt vorgegebenen Prüfumfang. |
| `DIAGNOSE_ACCEPTANCE` | Lies den nativen Projektstatus und den Laufbeleg. Nutze Fehleranalyse beim tatsächlich ausgeführten Prozess und Toolchain-Diagnose bei einem fehlenden Prozess, bevor du eine Korrektur ableitest. Prüfe beim Timeout zuerst, ob der Prozess überhaupt einen belastbaren Sollwert erreicht hat. |
| Bestätigter Projektfehler und Reparaturauftrag | Nutze den bestehenden Projektpfad über `CODEFORGE`. Wende einen belegten Patch im beauftragten Umfang über `PATCH-APPLY` an. Verifiziere Korrektur und Regression am betroffenen Einstieg. |
| Ungelöste Git-Indexkonflikte im Projekt | Melde `CONFLICT_QUARANTINE` mit der nativen Konfliktzahl. Prüfe den Konflikt im gebundenen Checkout. Erst nach geklärtem Index erneut abgleichen. |
| `CONFLICT_QUARANTINE` oder `READBACK_PENDING` | Benenne den fehlenden oder widersprüchlichen Nachweis. Prüfe zuerst Quelle und Scope. |

## Arbeitsstränge und Peer-Handoffs

- Halte pro Arbeitsstrang Basisrevision, Dateibesitz, Abhängigkeiten, letzten belegten Schritt, Status und Rückkehranker fest. Bei Unterbrechung sichere die Arbeitsposition vor einem Kontextwechsel. Führe unabhängige Arbeiten innerhalb des Auftrags weiter, wenn ein Strang blockiert ist.
- Vergleiche bei einem Peer-Handoff Absender, Zielprojekt, Zweck, Quellrevision oder Blob, Voraussetzungen und erlaubte Aktionen. Prüfe bekannte Wiederholungen und abgelöste Handoffs vor der Einordnung. Handoffs mit widersprüchlichem Ziel oder Scope bleiben offen oder in Konflikt-Quarantäne.
- Dokumentiere Vorbereitung, zugestellten Stand, Übernahme im Zielprojekt und tatsächliche Host-Ausführung anhand der jeweils vorliegenden Belege.

Grundlage sind 666CLIC CodeForge Handoff R01 (§2–3), 666STREAM CodeForge v1.0.0 (§5–6), LYVRA CodeForge R01, CodeForge-Handoff UCA R01 und der vorgeschlagene UCA-R02-Integrationsvertrag.

## Einstieg aus ChatGPT, Plugin und Windows

Die native Autorität ist 666DEV. [LiveCircle-Vertrag](../../../docs/livecircle.md) und
`src/devhub/livecircle.py` bestimmen Format, Quellenreihenfolge und Status. Stelle
die nächsten Schritte als Vorschlag dar. Ein importierter Handoff startet weder
Befehle noch übernimmt er Current. Verwende Fachskills für die Sachebene, nachdem
Projekt und Scope aus der 666DEV-Quelle aufgelöst wurden.

Bei Änderungen am 666DEV-Live-System gehört der
[Windows-Abgleich](../../../docs/livecircle.md#pflichtabgleich-mit-der-windows-anwendung)
zum Start, zur Wiederaufnahme und zum Update. Nenne die geprüfte Basis, die
betroffenen PC-Funktionen und ob Abgleich, Anpassung oder Windows-Abnahme
ansteht. Verwende die zuletzt belegte PC-Revision, wenn sie vorliegt.

Ein direktes `666DEV UPDATE` nach einem 666DEV-bezogenen Quellenpaket folgt
[Update mit Quellenpaket](../../../docs/livecircle.md#update-mit-quellenpaket).
Prüfe die Änderungen und integriere die relevanten Teile in den Hub. Die
Projektwahl gilt für den separaten Projekt-Current; sie darf die Quellenintegration
in 666DEV nicht blockieren.
