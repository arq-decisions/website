# www.arqdecisions.com

Die Website von arq decisions als statische Seiten, gehostet über GitHub Pages.

**Ziel:** Die Seite läuft ohne Contentful und ohne Agentur-Code. Sie lädt keine externen Schriften, setzt keine Cookies und
zählt keine Besuche. Damit fällt die Ursache der Ausfälle im Oktober und November 2026 weg: Contentful hatte die
Auslieferung wegen des Kontingents gesperrt.

**Stand (21.11.2026):** Alle 13 veröffentlichten Seiten sind aus dem Contentful-Export vom 21.11.2026 nachgebaut, im
arq-Hausstil (Roboto, Roboto Condensed, Palette aus dem arq-Manual). Alte Adressen (`/beta-…`, `/home`, `/podcasts` …)
leiten weiter.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `content/entries.json` | Texte und Struktur aller Seiten (veröffentlichte Contentful-Einträge, Locale de-DE) |
| `content/assets.json` | Bilder: Datei, Titel, Beschreibung, Größe |
| `content/site.json` | Seitentitel, Beschreibungen, Weiterleitungen alter Adressen, Navigation-Button, Domain |
| `static/` | CSS, JavaScript, Schriften, Bilder |
| `build.py` | baut die Seiten nach `docs/` |
| `tools/hero_art.py` | erzeugt die Hero-Grafik (Prognosepfade) `static/img/hero_prognosepfade_v7.svg` |
| `docs/` | fertige Seite, die GitHub Pages ausliefert |

## Ändern und veröffentlichen

1. Text in `content/entries.json` ändern (Rich Text wie in Contentful) oder Bild in `static/img/` ablegen und in
   `content/assets.json` eintragen.
2. `python build.py --serve` baut die Seite und startet eine Vorschau auf http://localhost:8000.
3. Committen und pushen. GitHub Pages veröffentlicht `docs/` nach ein bis zwei Minuten.

Der vollständige Rohexport aus Contentful (alle 799 Einträge, auch Entwürfe) liegt nicht hier, sondern im
SharePoint-Ordner `04 market/459 website mit claude/contentful_export_2026-11-21/`.

## Domain

DNS liegt bei All-Inkl (kasserver). Für GitHub Pages:

- `www` als CNAME auf `arq-decisions.github.io`
- `arqdecisions.com` mit vier A-Einträgen: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
- MX- und andere Mail-Einträge bleiben unverändert.
