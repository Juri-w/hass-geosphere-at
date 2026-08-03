#!/bin/bash

echo "=== Checking Config Flow Setup ==="
echo ""

echo "1. Manifest.json domain check:"
grep '"domain"' ./manifest.json
echo ""

echo "2. const.py DOMAIN check:"
grep "DOMAIN\s*=" ./const.py
echo ""

echo "3. config_flow.py class definition:"
grep "class.*ConfigFlow" ./config_flow.py
echo ""

echo "4. __init__.py async_setup_entry:"
grep "async_setup_entry" ./__init__.py
echo ""

echo "5. Python syntax check:"
python3 -m py_compile ./*.py && echo "✅ All files valid" || echo "❌ Syntax errors found"
echo ""

echo "6. Manifest JSON check:"
python3 -m json.tool ./manifest.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
echo ""

echo "7. Translations JSON check:"
python3 -m json.tool ./translations/*.json > /dev/null && echo "✅ Valid JSON" || echo "❌ Invalid JSON"
echo ""

echo "8. Docker container running?"
docker compose ps
echo ""

echo "9. Last HA logs (last 30 lines):"
docker logs -fn 30 homeassistant-local
echo ""