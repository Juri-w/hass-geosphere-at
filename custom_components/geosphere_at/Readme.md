# Geosphere Austria Home Assistant Integration

Diese Custom Component für Home Assistant ermöglicht die Integration von Wetterdaten von [GeoSphere Austria](https://www.geosphere.at).

## Installation via HACS

1. Installiere HACS falls noch nicht vorhanden
2. Füge diese Integration als benutzerdefinierte Repository hinzu: `https://github.com/juri-w/hass-geosphere-at`
3. Klicke auf "Install"
4. Starte Home Assistant neu
5. Gehe zu Einstellungen -> Geräte & Dienste -> Integration hinzufügen
6. Suche nach "Geosphere Austria"
7. Wähle deinen Standort aus der Liste aus

## Funktionen

- **Weather Entity**: Aktuelle Wetterbedingungen und 8-Tage-Vorhersage
- **Sensors**:
  - Windgeschwindigkeit (km/h)
  - Windböen (km/h)
  - Windrichtung (Grad)
  - Niederschlag (mm)
  - Nebelindex
  - Temperatur (°C)

## API Endpoints

Die Integration nutzt folgende GeoSphere.at API Endpoints:

- `/data/forecasts/points` - Alle verfügbaren Standorte
- `/data/forecasts/flexi/{point_id}` - Stündliche Vorhersage
- `/data/forecasts/daily/{point_id}` - Tägliche Vorhersage

## Beispiel-Localisationen

| ID | Name | Bundesland |
|----|------|------------|
| 101 | Leithaprodersdorf | Burgenland |
| 2204 | Wien (Beispiel) | Wien |
| ... | ... | ... |

## Lizenz

MIT License