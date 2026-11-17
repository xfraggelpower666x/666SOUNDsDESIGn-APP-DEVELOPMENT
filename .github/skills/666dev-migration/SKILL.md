---
name: 666dev-migration
description: Plant und verifiziert reversible Migrationen von bestehenden Anwendungen in 666DEV. Bei Portierung, Framework- oder Datenmigration, Toolchain-Wechsel und Übernahme älterer Anwendungen verwenden.
---

# Migration bestehender Anwendungen

1. Inventarisiere bestehendes Verhalten, Nutzerabläufe, Datenformate, Start- und Build-Skripte, Bereitstellung und Abhängigkeiten. Kläre, ob nur die Entwicklungsanbindung wechselt oder auch Quellcode, Laufzeit und Daten. Binde jede Seite an ihre tatsächliche Revision.
2. Leite die Anforderungen aus normalem Einstieg, Verträgen, Tests und beobachteter Ausgabe ab. Sichere einen reproduzierbaren Referenzfall und den Rückkehranker. Markiere fehlende Baseline-Nachweise sichtbar.
3. Plane einen durchgängigen Schnitt vom Einstieg über Daten und Logik zu Ergebnis und Lieferung. Behalte Alt-Daten, öffentliche Schnittstellen und Build-Einstiege bei, soweit der Auftrag sie erhält. Nutze die vorhandenen Werkzeuge des Zielprojekts. Zeichne erforderliche Konvertierungen und ihre Rückrichtung auf.
4. Vergleiche Alt und Neu mit denselben Eingaben, beispielsweise einer bestehenden Konfiguration, einem Fehlerfall und einem typischen Arbeitsablauf. Prüfe zusätzlich Build, Paketierung und Start auf der betroffenen Plattform. Bei mehreren Etappen führe Baseline, Diff, Ergebnis und Rückkehranker je Etappe.
5. Stelle Herkunft, geprüfte Verträge, offene Abweichungen und Rückkehrweg dar. Ein Wechsel des freigegebenen Zielstands erfolgt im dafür vorgesehenen ausdrücklich beauftragten Update.

Methodische Grundlage sind Bestandsaufnahme und Verhaltensvergleich aus den Modernisierungs-Workflows des hochgeladenen Community-Snapshots `0d020f70b9079c4add6673f8a1d1cc0e34fe60b5`. Wähle plattformspezifische Werkzeuge anhand des konkreten 666DEV-Auftrags.
