---
name: 666dev-codeforge
description: Analysiert, repariert und prüft ausgewählte 666DEV-Projekte. Bei CodeForge, Feature-Aufträgen, Fehlern, Audits und Patch-Kandidaten verwenden.
---

# 666dev-codeforge

## Vom beobachteten Verhalten zum Patch

1. Binde den Auftrag an Projektprofil, Scope und Basis-Commit. Ermittle den tatsächlichen Einstieg und das erwartete Ergebnis. Lies die passende Toolchain und die zugehörigen Build-, Start-, Paketierungs- und Testdateien.
2. Verfolge Eingabe, Aufruf oder Event über Daten und Zustand bis zur beobachteten Wirkung. Erfasse den verantwortlichen Codepfad und seine Aufrufer. Dokumentiere eine überprüfbare Hypothese, falls der Ursache ein direkter Beleg fehlt.
3. Grenze einen wirksamen Patch ein, der bestehende Aufrufer, Alt-Daten, Wiederholungen und Teilfehler im betroffenen Ablauf berücksichtigt. Arbeite bei Bedarf im isolierten Git-Worktree. Binde Kandidat und Vorher-Nachweis an Basisrevision, Dateibereich und Recovery-Anker.
4. Wende Kandidaten nur im ausdrücklich beauftragten Scope an. Prüfe den Patch am normalen Einstieg. Bei einer Reparatur verwende möglichst dieselbe Eingabe für Reproduktion und Regression.
5. Lies Diff und erlaubte Pfade zurück. Erfasse für jeden Check Befehl, Revision, Umgebung, Exitcode und tatsächliche Wirkung. Bei reinem Audit liefere Fundstelle, Auswirkung, Beleg und nächsten Prüfschritt.

## Nachweis nach der Änderung

Prüfe bei einem laufzeitrelevanten Patch die drei zum Auftrag passenden Ebenen. Struktur umfasst Schema, Referenzen und Build-Vertrag. Verhalten umfasst normalen Einstieg, Aufrufer, Daten und Seiteneffekte. Wiederaufnahme umfasst Neustart, Rückkehranker und Recovery, soweit der Patch sie betrifft. Der Reviewer hält nach der Reparatur für jeden Befund fest, womit er erneut geprüft wurde. Behalte verbleibende Befunde mit Fundstelle und Auswirkung im Re-Audit.

Grundlage sind 666PFS CODEFORGE R01, LYVRA CodeForge R01 und 666 Code Reviewer Integration Repair Freeze v1.0.0.
