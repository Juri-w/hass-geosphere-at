# Lokales Test-Guide für Geosphere.at Integration

## Voraussetzungen

- Docker & Docker Compose installiert
- Git (optional, für Code-Versionierung)
- Mindestens 4GB RAM verfügbar

## Schnellanleitung

### 1. Environment vorbereiten

#### Projektverzeichnis erstellen
```bash
mkdir geosphere-ha-integration 
cd geosphere-ha-integration
```
#### Dateien erstellen (alle oben genannten)
```bash
- docker-compose.yaml
- .env
- start.sh, debug.sh, cleanup.sh
- custom_components/geosphere_at/*
```
#### Scripts ausführbar machen

```bash
chmod +x *.sh
```

### 2. Integration starten

```bash
./start.sh
```

### 3. Integration laden

1. Öffne http://localhost:8123
2. Erstelle ersten Account
3. Gehe zu Einstellungen → Geräte & Dienste
4. Klicke unten auf "+ Integration hinzufügen"
5. Suche nach "Geosphere Austria"
6. Füge deine Konfiguration hinzu

### 4. Debugging

#### HA Logs in Echtzeit ansehen
```bash
./debug.sh
```
#### Spezifische Integration Logs filtern
```bash
docker compose logs -f homeassistant | grep -i geosphere
```
#### HA Core neu laden ohne Neustart
```bash
curl -X POST http://localhost:8123/api/services/homeassistant/reload
```
### 5. Typische Test-Szenarien

#### API-Verbindungs-Test

Im HA Python Console (Developer Tools → Template)
```python
import aiohttp async with aiohttp.ClientSession() as session: async with session.get("https://www.geosphere.at/data/forecasts/points") as resp: print(await resp.json())
```
#### Integration Reload

Ohne Restart neu laden
```bash
curl -X POST
-H "Authorization: Bearer YOUR_LONG_LIVED_TOKEN"
-H "Content-Type: application/json"
http://localhost:8123/api/services/homeassistant/reload
```

### 6. Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| `ConfigEntryNotReady` | API erreichbar? Logs prüfen (`docker compose logs`) |
| Integration nicht auffindbar | Manifest-Version stimmt mit `__init__.py` überein? |
| `ImportError` | Missing dependencies im manifest.json? |
| Kein Datenfluss | coordinator async_update_data erfolgreich? |

### 7. Vor Push prüfen

#### Linting (falls ruff installiert)
```bash
pip install ruff ruff check custom_components/geosphere_at/
```
#### Formatierung
```bash
black custom_components/geosphere_at/
```

#### Manifest Validation
```bash
python -c "import json; m=json.load(open('custom_components/geosphere_at/manifest.json')); print('✓', m['name'], m['version'])"
```
#### Python Syntax
```bash
python -m py_compile custom_components/geosphere_at/*.py
```
#### HA Config Check
```bash
docker exec homeassistant-local python -m homeassistant --config /config --script check_config
```
### 8. Clean Test Environment

#### Nach jedem Test runterfahren:

Nur Container stoppen

```bash
docker compose down
```

Komplett resetten (löscht HA-Konfiguration)

```bash
./cleanup.sh --full
```

## Nächste Schritte nach Testing

1. ✅ Alle Tests bestanden
2. README.md aktualisieren mit echten Screenshots
3. CHANGELOG.md erstellen
4. GitHub Repository initialisieren
5. Version 1.0.0 taggen
6. HACS Validation Tool nutzen vor Einreichung