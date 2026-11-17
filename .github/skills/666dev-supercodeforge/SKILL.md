---
name: 666dev-supercodeforge
description: Ermittelt Ursachenketten und Auswirkungen über Module, Sprachen, Skripte, Build und Tests. Bei SuperCodeForge, Systemanalyse und HEAD-Deltas verwenden.
---

# 666dev-supercodeforge

## Wirkungsanalyse mit Belegen

- Beginne bei einem beobachteten Symptom, einem Vertrag oder einem konkreten Git-Delta. Erfasse geänderte, hinzugefügte, gelöschte und umbenannte Pfade. Weise Revision und Arbeitsbaumzustand aus.
- Nutze den vorhandenen Graphen unter `src/devhub/`. Ergänze fehlende Beziehungen aus tatsächlichen Quellen. Führe für jede relevante Kante Richtung, Quellfundstelle, Revision und Belegstufe. Verfolge rückwärts zum Verbraucher und vorwärts bis zu Build, Paket, Test oder beobachteter Ausgabe.
- Verknüpfe Sprachgrenzen über gemeinsame Verträge wie Routen, Events, Datenformate, IPC-Kanäle oder Dateiein- und -ausgaben. Prüfe bei Windows-Projekten auch Batch- und PowerShell-Einstiege, Compiler-Konfiguration und Paketierung. Weise dynamische oder heuristisch erkannte Kanten ausdrücklich als offen oder abgeleitet aus.
- Suche nach Folgeeffekten aus mehreren Belegen, etwa einem geänderten Entrypoint mit unverändertem Paketmanifest. Nenne zu jeder Hypothese die Evidenz, einen widerlegbaren Prüfschritt und die erwartete Wirkung.
- Ordne Arbeitsschritte nach ihren Abhängigkeiten und Dateibesitzern. Gemeinsame Schreibziele erhalten eine geordnete Integrationsfolge. Projektübergreifende Beobachtungen erweitern den Schreibscope nicht.
