#!/bin/bash
set -e

echo "🏠 Starting Local Home Assistant Environment..."

# Erstelle benötigte Ordner
mkdir -p ha-config/custom_components

# Wenn custom_components existiert, mounten wir es bereits oben
if [ ! -d "./custom_components" ]; then
    echo "⚠️  Warnung: custom_components Ordner nicht gefunden!"
    echo "Erstelle einen leeren Ordner oder platziere deine Integration hier."
    mkdir -p custom_components/geosphere_at
fi

# Kopiere die Integration in den custom_components Ordner
cp *.py custom_components/geosphere_at/
cp manifest.json custom_components/geosphere_at/
cp README.md custom_components/geosphere_at/
cp -r translations custom_components/geosphere_at/

# Pullneuestes HA Image
echo "📥 Pulling Home Assistant image..."
docker pull ghcr.io/home-assistant/home-assistant:stable

# Starte den Container
echo "🚀 Starting containers..."
docker compose up -d

# Warte auf Start
sleep 5

echo ""
echo "✅ Home Assistant läuft!"
echo ""
echo "📡 Zugriffsadressen:"
echo "   - Lokales UI: http://localhost:8123"
echo "   - API Health: http://localhost:8123/api/health"
echo "   - Developer:  http://localhost:8123/developer-tool/state"
echo ""
echo "📋 Nützliche Befehle:"
echo "   docker compose logs -f homeassistant      # HA Logs ansehen"
echo "   docker compose ps                         # Status prüfen"
echo "   docker compose down                       # Alles stoppen"
echo "   docker compose down -v                    # Mit Daten löschen"
echo ""