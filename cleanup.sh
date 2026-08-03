#!/bin/bash
set -e

echo "🧹 Cleaning up local HA environment..."

# Stoppe alle Container
docker compose down

# Lösche Volume-Daten (WARNUNG: Verliert alle HA-Einstellungen!)
if [ "$1" == "--full" ]; then
    echo "⚠️  Lösche auch persisted Daten..."
    rm -rf ha-config/
    docker volume prune -f
fi

echo "✅ Cleanup abgeschlossen"