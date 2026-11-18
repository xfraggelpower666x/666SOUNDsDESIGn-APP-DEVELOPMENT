# 666DEV Dashboard auf Windows

## Lokaler Start

Voraussetzungen sind Git und Python 3.11 oder neuer. Falls 666DEV noch nicht
lokal ausgecheckt ist, kann der aktuelle Draft-Branch so geladen werden:

```powershell
git clone --branch copilot/666dev-initial-functional-setup https://github.com/xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT.git
cd 666SOUNDsDESIGn-APP-DEVELOPMENT
```

Starte [START_666DEV_DASHBOARD.cmd](START_666DEV_DASHBOARD.cmd) aus dem Checkout.
Das Fenster bleibt während des Betriebs offen. Prüfe die Oberfläche unter
[http://127.0.0.1:8766/](http://127.0.0.1:8766/). Die Batch verwendet denselben
Python-Dienst und dieselben Dateien unter [web/](../web/) wie die CLI.

## Persönlicher Zugriff über die Domain

Der vorgesehene Host ist
[dev.666soundsdesign-broadcaster.com](https://dev.666soundsdesign-broadcaster.com/).
Die Route `666dev-windows` verweist auf `http://127.0.0.1:8766`. Der Tunnel
setzt für den lokalen Dienst den Host-Header `127.0.0.1:8766` und verlangt
ein gültiges Cloudflare-Access-Token für diese Anwendung.

1. Starte zuerst das Dashboard und prüfe die Loopback-Adresse.
2. Öffne [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) und wähle
   unter **Networks → Connectors → Cloudflare Tunnels** den Tunnel
   **666dev-windows**. Wähle **Windows** und übernimm den angezeigten
   Installationsbefehl in ein lokales Terminal als Administrator. Installiere
   `cloudflared` bei Bedarf nach der
   [Windows-Anleitung von Cloudflare](https://developers.cloudflare.com/tunnel/downloads/).
3. Verwende den Tunnel-Token nur auf deinem Rechner. Halte ihn aus dem
   Checkout, dem Chat und aus Screenshots heraus. Melde dich danach an der
   Subdomain mit dem für diese Access-Anwendung freigegebenen Cloudflare-Konto an.

Der Tunnel kann als Windows-Dienst weiterlaufen. Der Dashboard-Prozess muss
ebenfalls laufen. Bei einem ausgeschalteten PC ist das Live-Dashboard offline.

## Abnahme

- Lokal liefern die Startseite und `/dashboard.json` eine Antwort.
- In einem privaten Browserfenster verlangt der Host für beide Pfade eine
  Anmeldung. Ohne Anmeldung bleiben die Projektdaten gesperrt.
- Nach Anmeldung erscheinen im Dashboard dieselben Projekte wie lokal.
- Cloudflare zeigt `666dev-windows` bei aktivem Connector als verbunden an.
