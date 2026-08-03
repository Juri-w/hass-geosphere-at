"""Data coordinator for Geosphere Austria integration."""

import logging
from datetime import datetime, timezone, timedelta
import aiohttp
import asyncio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    API_FLEXI,
    API_DAILY,
    API_NOWCAST,
    MODE_REGIONAL,
    MODE_LOCAL_NEW,
    MODE_LOCAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["weather"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up this integration using YAML is not supported."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Geosphere Austria from a config entry."""
    
    # ← NEU: Erst prüfen ob Entry gültig ist
    if not entry.data or len(entry.data) == 0:
        _LOGGER.error("CRITICAL: Entry %s has EMPTY data! Skipping setup.", entry.entry_id)
        return False
    
    point_id = entry.data.get("point_id")
    location_name = entry.data.get("location_name", "Unbekannt")
    name = entry.data.get("name", location_name)
    latitude = entry.data.get("latitude")
    longitude = entry.data.get("longitude")
    mode = entry.data.get("mode", MODE_REGIONAL)
    
    _LOGGER.info(
        "Setting up Geosphere %s: mode=%s, point_id='%s' (type=%s), name=%s, lat=%s, lon=%s",
        entry.entry_id, mode, point_id, type(point_id).__name__, name, latitude, longitude
    )
    _LOGGER.info("Entry data dump: %s", entry.data)
    
    # ← VALIDIERUNG: Modus-spezifische Prüfungen
    if mode == MODE_REGIONAL:
        if not point_id or str(point_id).strip() == "":
            _LOGGER.error("=" * 60)
            _LOGGER.error("CRITICAL ERROR: No valid point_id for regional mode!")
            _LOGGER.error("Entry ID: %s", entry.entry_id)
            _LOGGER.error("Entry data: %s", entry.data)
            _LOGGER.error("=" * 60)
            return False  # ← Entry ablehnen, nicht weitermachen
    
    if mode in [MODE_LOCAL_NEW, MODE_LOCAL_UPDATE]:
        if latitude is None or longitude is None:
            _LOGGER.error("No latitude/longitude configured for local mode in entry %s", entry.entry_id)
            return False
    
    # ← REST: Normaler Setup-Code
    coordinator = GeosphereDataCoordinator(hass, entry)
    
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to initialize coordinator: %s", err)
        raise ConfigEntryNotReady(err) from err
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True

class GeosphereDataCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch and update Geosphere.at weather data."""
    
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the coordinator."""
        self.config_entry = config_entry
        self._session: aiohttp.ClientSession | None = None
        
        self.mode = config_entry.data.get("mode", MODE_REGIONAL)
        self.point_id = config_entry.data.get("point_id")
        self.name = config_entry.data.get("name", config_entry.data.get("location_name", "Lokal"))
        # self.latitude = config_entry.data.get("latitude")
        # self.longitude = config_entry.data.get("longitude")
        self.location_name = config_entry.data.get("location_name", "Lokal")
        self.nowcast_enabled = config_entry.options.get("nowcast_enabled", False)
        if self.mode == MODE_REGIONAL and self.nowcast_enabled:
            self.latitude = config_entry.options.get("nowcast_latitude")
            self.longitude = config_entry.options.get("nowcast_longitude")
        else:
            self.latitude = config_entry.data.get("latitude")
            self.longitude = config_entry.data.get("longitude")
        
        if self.mode == MODE_REGIONAL:
            self.name = f"geosphere_at_{self.point_id}"
        else:
            self.name = f"geosphere_at_{self.latitude}_{self.longitude}"
        
        super().__init__(
            hass,
            _LOGGER,
            name=self.name,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
    
    async def _async_update_data(self):
        """Fetch data from Geosphere.at APIs."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        
        try:
            tasks = {}
            
            if self.mode == MODE_REGIONAL:
                tasks["regional_flexi"] = self._fetch_json(f"{API_FLEXI}/{self.point_id}")
                tasks["regional_daily"] = self._fetch_json(f"{API_DAILY}/{self.point_id}")
            
            if self.mode in [MODE_LOCAL_NEW, MODE_LOCAL_UPDATE] or self.nowcast_enabled:
                if self.latitude and self.longitude:
                    # ← WICHTIGER FIX: History ausschalten, Offset auf 0
                    nowcast_params = (
                        f"?lat_lon={self.latitude},{self.longitude}"
                        f"&forecast_offset=0"
                        f"&parameters=t2m,rr,td,ff"
                        f"&format=geojson"
                        f"&history=false"  # ← KEINE vergangenen Daten!
                    )
                    nowcast_url = f"{API_NOWCAST}{nowcast_params}"
                    _LOGGER.debug("Nowcast URL: %s", nowcast_url[:150])
                    tasks["nowcast"] = self._fetch_json(nowcast_url)
            
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            
            data = {}
            for i, key in enumerate(tasks.keys()):
                result = results[i]
                if isinstance(result, Exception):
                    _LOGGER.warning("%s fetch failed: %s", key, result)
                    data[key] = None
                else:
                    data[key] = result
            
            # ← DEBUG: Bevor Hybrid gemacht wird!
            if data.get("nowcast"):
                nowcast_ts = data["nowcast"].get("timestamps", [])
                _LOGGER.info("=== NOWCAST DEBUG ===")
                _LOGGER.info("Nowcast timestamp count: %d", len(nowcast_ts))
                _LOGGER.info("First 4 timestamps: %s", nowcast_ts[:4] if len(nowcast_ts) >= 4 else nowcast_ts)
                _LOGGER.info("Timestamp interval check:")
                for i in range(len(nowcast_ts)-1):
                    dt1 = self._parse_timestamp(nowcast_ts[i])
                    dt2 = self._parse_timestamp(nowcast_ts[i+1])
                    if dt1 and dt2:
                        interval_min = abs((dt2 - dt1).total_seconds()) / 60
                        _LOGGER.info("  [%d] to [%d]: %.1f min", i, i+1, interval_min)
                _LOGGER.info("====================")
            
            if data.get("regional_flexi"):
                flexi_ts = data["regional_flexi"].get("timestamps", [])
                _LOGGER.info("Regional Flexi timestamp count: %d", len(flexi_ts))
            
            # Hybrid sync
            if data.get("nowcast") and data.get("regional_flexi"):
                data["hybrid"] = self._sync_data_sources(
                    data["nowcast"],
                    data["regional_flexi"]
                )
            else:
                data["hybrid"] = data.get("nowcast") or data.get("regional_flexi")
            
            data["last_updated"] = utcnow().isoformat()
            data["mode"] = self.mode
            
            return data
            
        except Exception as err:
            _LOGGER.error("Error fetching Geosphere.at data: %s", err)
            raise UpdateFailed(f"Could not fetch data: {err}") from err
        
    def _sync_data_sources(self, nowcast_data, regional_data):
        """Combine Nowcast (fine, 15-min) + Regional (long-term, hourly) into one dataset.

        Nowcast liefert KEIN 'sy' (Wettersymbol) - das kommt ausschließlich aus Regional
        und wird für jeden Hybrid-Zeitpunkt auf den zeitlich nächstgelegenen Regional-Wert
        gemappt (max. 15 Min Toleranz), analog zu den anderen Parametern.
        """
        if not nowcast_data and not regional_data:
            return None

        if not nowcast_data:
            return regional_data

        if not regional_data:
            return nowcast_data

        nowcast_props = nowcast_data.get("features", [{}])[0].get("properties", {})
        nowcast_params = nowcast_props.get("parameters", {})
        nowcast_timestamps = nowcast_data.get("timestamps", [])

        regional_props = regional_data.get("features", [{}])[0].get("properties", {})
        regional_params = regional_props.get("parameters", {})
        regional_timestamps = regional_data.get("timestamps", [])

        # ← Zeitachse: Erst alle feinen Nowcast-Zeitpunkte (15-min),
        #   danach Regional-Zeitpunkte, die NACH dem letzten Nowcast-Zeitpunkt liegen
        #   (damit die Vorhersage stündlich weiterläuft statt abzubrechen)
        if nowcast_timestamps:
            last_nowcast_dt = self._parse_timestamp(nowcast_timestamps[-1])
            later_regional_ts = [
                ts for ts in regional_timestamps
                if last_nowcast_dt and self._parse_timestamp(ts)
                and self._parse_timestamp(ts) > last_nowcast_dt
            ]
            hybrid_timestamps = nowcast_timestamps + later_regional_ts
        else:
            hybrid_timestamps = regional_timestamps[:]

        # ← "sy" mit in der Parameter-Schleife behandeln, NICHT separat.
        #   Da Nowcast kein "sy" liefert, ist nc_data für "sy" automatisch leer
        #   und der Wert fällt für jeden Zeitpunkt korrekt auf Regional zurück.
        hybrid_params = {}

        for param_key in ["t2m", "rr", "td", "ff", "sy"]:
            nc_data = nowcast_params.get(param_key, {}).get("data", [])
            rg_data = regional_params.get(param_key, {}).get("data", [])

            merged_data = []
            for ts in hybrid_timestamps:
                ts_dt = self._parse_timestamp(ts)

                # Nächstgelegenen Nowcast-Wert suchen (falls Parameter dort existiert)
                best_nc_val = None
                best_nc_diff = float('inf')
                for j, nc_ts in enumerate(nowcast_timestamps):
                    nc_dt = self._parse_timestamp(nc_ts)
                    if nc_dt and ts_dt:
                        diff = abs((ts_dt - nc_dt).total_seconds())
                        if diff < best_nc_diff and diff < 900:  # 15min Toleranz
                            best_nc_diff = diff
                            best_nc_val = nc_data[j] if j < len(nc_data) else None

                # Fallback: nächstgelegenen Regional-Wert suchen
                rg_val = None
                best_rg_diff = float('inf')
                for j, rg_t in enumerate(regional_timestamps):
                    rg_dt = self._parse_timestamp(rg_t)
                    if rg_dt and ts_dt:
                        diff = abs((ts_dt - rg_dt).total_seconds())
                        if diff < best_rg_diff and diff < 900:  # 15min Toleranz
                            best_rg_diff = diff
                            rg_val = rg_data[j] if j < len(rg_data) else None

                # Nowcast hat Vorrang, "sy" landet automatisch immer bei Regional
                merged_data.append(best_nc_val if best_nc_val is not None else rg_val)

            hybrid_params[param_key] = {
                "data": merged_data,
                "name": nowcast_params.get(param_key, {}).get(
                    "name", regional_params.get(param_key, {}).get("name", "")
                ),
                "unit": nowcast_params.get(param_key, {}).get(
                    "unit", regional_params.get(param_key, {}).get("unit", "")
                ),
            }

        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": regional_data.get("features", [{}])[0].get("geometry", {}),
                "properties": {
                    "parameters": hybrid_params,
                }
            }],
            "timestamps": hybrid_timestamps,
            "source": "hybrid"
        }
    
    async def _fetch_json(self, url: str) -> dict | None:
        """Fetch JSON data from a URL."""
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        
        try:
            _LOGGER.debug("Fetching URL: %s", url[:100] + "..." if len(url) > 100 else url)
            
            async with self._session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    _LOGGER.error(
                        "HTTP error %s for URL %s: %s",
                        resp.status, url[:50], error_text[:200]
                    )
                    raise aiohttp.ClientError(f"HTTP error {resp.status}")
                
                return await resp.json()
                
        except aiohttp.ClientConnectorError as err:
            _LOGGER.error("Connection error to %s: %s", url[:50], err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout fetching %s: %s", url[:50], err)
            raise
        except Exception as err:
            _LOGGER.error("Unexpected error fetching %s: %s", url[:50], err)
            raise
    
    @property
    def get_regional_flexi_data(self):
        """Get the latest regional flexible forecast data."""
        if not self.data:
            return None
        return self.data.get("regional_flexi")
    
    @property
    def get_regional_daily_data(self):
        """Get the latest regional daily forecast data."""
        if not self.data:
            return None
        return self.data.get("regional_daily")
    
    @property
    def get_nowcast_data(self):
        """Get the latest nowcast data (15-min intervals)."""
        if not self.data:
            return None
        return self.data.get("nowcast")
    
    @property
    def get_hybrid_data(self):
        """Get synced hybrid data (Regional sy + Nowcast values)."""
        if not self.data:
            return None
        return self.data.get("hybrid")
    
    @property
    def get_latest_temperature(self):
        """Get latest temperature from available source."""
        hybrid = self.get_hybrid_data
        if hybrid and "features" in hybrid:
            params = hybrid["features"][0].get("properties", {}).get("parameters", {})
            t2m_data = params.get("t2m", {}).get("data", [])
            if t2m_data and len(t2m_data) > 0 and t2m_data[0] is not None:
                return float(t2m_data[0])
        
        nowcast = self.get_nowcast_data
        if nowcast and "features" in nowcast:
            params = nowcast["features"][0].get("properties", {}).get("parameters", {})
            t2m_data = params.get("t2m", {}).get("data", [])
            if t2m_data and len(t2m_data) > 0 and t2m_data[0] is not None:
                return float(t2m_data[0])
        
        flexi = self.get_regional_flexi_data
        if flexi:
            timestamps = flexi.get("timestamps", [])
            idx = self._get_current_data_index(timestamps)
            props = flexi["features"][0].get("properties", {})
            parameters = props.get("parameters", {})
            t2m_data = parameters.get("t2m", {}).get("data", [])
            if t2m_data and idx < len(t2m_data) and t2m_data[idx] is not None:
                return float(t2m_data[idx])
        
        return None
    
    @property
    def get_location_name(self):
        """Get the location name from config."""
        return self.location_name
    
    @property
    def get_unique_id(self):
        """Get the unique ID for this coordinator."""
        if self.mode == MODE_REGIONAL:
            return f"geosphere_at_{self.point_id}"
        else:
            return f"geosphere_at_{self.latitude}_{self.longitude}"
    
    @property
    def get_device_info(self):
        """Return device information."""
        if self.mode == MODE_REGIONAL:
            device_name = f"Geosphere Austria - {self.location_name}"
            model = "Hybrid Forecast" if self.nowcast_enabled else "Regional Forecast API"
        else:
            device_name = f"Geosphere {self.name}"
            model = "Nowcast API"
        
        return {
            "identifiers": {(DOMAIN, self.get_unique_id)},
            "name": device_name,
            "manufacturer": "GeoSphere Austria",
            "model": model,
            "entry_type": "service",
        }
    
    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        """Parse ISO format timestamp."""
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def _get_current_data_index(self, timestamps: list[str]) -> int:
        """Get index closest to current time."""
        if not timestamps:
            return 0
        
        now_utc = datetime.now(timezone.utc)
        best_index = 0
        min_diff = float('inf')
        
        for i, ts_str in enumerate(timestamps):
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                diff = abs((now_utc - ts).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    best_index = i
            except Exception as err:
                _LOGGER.warning("Failed to parse timestamp %s: %s", ts_str, err)
                continue
        
        return best_index
    
    async def close_session(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when updated."""
    _LOGGER.info("Reloading Geosphere entry: %s", entry.entry_id)
    _LOGGER.info("Entry data before reload: %s", entry.data)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Geosphere entry: %s", entry.entry_id)
    
    # ← VOR DEM UNLOAD: Koordinatoren-Session schließen
    coordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.close_session()
    
    # ← Platformen entladen
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # ← Daten bereinigen
        if entry.entry_id in hass.data[DOMAIN]:
            del hass.data[DOMAIN][entry.entry_id]
    
    return unload_ok