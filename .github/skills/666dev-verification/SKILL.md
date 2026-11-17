---
name: 666dev-verification
description: Prüft Tests, Build, Re-Audit, Freeze, ZIP und Readback für 666DEV. Bei Abnahme, CI-Prüfung, Paketlieferung und Release-Verifikation verwenden.
---

# 666dev-verification

## Abnahme und Liefernachweis

- Lies die Projektbefehle aus dem Entwicklungsvertrag. Prüfe getrennt Unit-Tests, normalen Einstieg, projektspezifischen Build, Paketierung und Zielhost. Prüfe den Scope mit einer aufgelösten Git-Diff-Basis. Erfasse tatsächliche Befehle, Commit, Umgebung, Exitcode und Ergebnis.
- Vergleiche bei einem Freeze das dokumentierte Dateiset mit dem Archiv. Verwende eine explizite Dateiauswahl aus verifiziertem Quellstand oder gebauten Artefakten. Prüfe Einträge, SHA-256, Bytezahl und erneutes Öffnen. Teste für ein startfähiges Lieferpaket nach dem Entpacken den dokumentierten Einstieg.
- Prüfe CI und Remote-Readback am zutreffenden Commit oder Artefakt. Halte lokale Tests, CI, Liefer-Readback und echte Plattformbeobachtung als eigene Nachweise fest.
- Melde fehlende Provider, blockierte Ausführung und ausgefallene Prüfschritte mit konkreter Begründung. Verwende die Status und Datenverträge aus `docs/architecture.md`.
