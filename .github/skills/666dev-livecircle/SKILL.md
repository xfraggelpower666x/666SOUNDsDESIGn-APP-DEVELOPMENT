---
name: 666dev-livecircle
description: Prüft Quellenstand, Current, Checkpoint und Wiederaufnahme in 666DEV. Bei SYSTEMSTART, WEITER, UPDATE, Handoffs, HEAD-Wechsel und Recovery verwenden.
---

# 666dev-livecircle

## Wiederaufnahme

- Ermittle zuerst Projekt-ID, Profil, Quellmodus und tatsächlichen HEAD. Lies anschließend Current, Checkpoint, Hash, Basisrevision, Scope, Rückkehranker und offenen Schritt. Prüfe Arbeitsbaum und betroffene Pfade.
- Unterscheide freigegebenen Current, Arbeitscheckpoint und Recovery-Kopie. Der Sollvertrag reserviert Current-Schreibvorgänge für ausdrücklich beauftragte Updates. Prüfe vor einem CLI-Aufruf seine tatsächlichen Seiteneffekte. Bestehende Abweichungen im Code sind Befunde. Bei einer Lesesitzung verwende die lesenden Einstiege oder direkte Dateiprüfung.
- Bei HEAD-Wechsel nutze einen exakten, passenden Nachweis oder eine verifizierte Vorgängerrevision als Vergleichsbasis. Prüfe betroffene Pfade, Abhängigkeiten, Eingaben und Umgebung. Prüfe die dadurch entwerteten Nachweise erneut. Bei divergierender Basis prüfe den Stand neu und dokumentiere den Konflikt.
- Setze am ersten fachlich und technisch freigegebenen offenen Schritt fort. Prüfe vor einem Wiederholungsversuch, ob ein Seiteneffekt bereits eingetreten ist. Sichere konkurrierende Stände und blockiere den betroffenen Schreibschritt bei einem Konflikt.
- Halte im Handoff Ziel, beobachteten Commit, belegte Arbeit, offene Nachweise und die nächste ausführbare Aktion fest. Bei einem autorisierten Update sichere den Ausgangsstand und prüfe Zustandskörper und Referenzen. Schreibe den Current-Pointer zuletzt und lies ihn direkt zurück.
