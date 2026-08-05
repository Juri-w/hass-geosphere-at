"""Geosphere Austria Weather Integration - With Hybrid Data Support."""

import logging
from datetime import datetime, timezone, timedelta
from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_EXCEPTIONAL,
)
from homeassistant.const import UnitOfTemperature, UnitOfSpeed, UnitOfPrecipitationDepth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    MODE_REGIONAL,
    MODE_LOCAL_NEW,
    MODE_LOCAL_UPDATE,
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

SYMBOL_TO_CONDITION = {
    1: ATTR_CONDITION_SUNNY,           # wolkenlos
    2: ATTR_CONDITION_PARTLYCLOUDY,    # heiter
    3: ATTR_CONDITION_PARTLYCLOUDY,    # wolkig
    4: ATTR_CONDITION_CLOUDY,          # stark bewölkt
    5: ATTR_CONDITION_CLOUDY,          # bedeckt
    6: ATTR_CONDITION_FOG,             # Bodennebel
    7: ATTR_CONDITION_FOG,             # Hochnebel
    8: ATTR_CONDITION_RAINY,          # leichter Regen
    9: ATTR_CONDITION_RAINY,          # mäßiger Regen
    10: ATTR_CONDITION_POURING,          # starker Regen
    11: ATTR_CONDITION_SNOWY_RAINY,     # Schneeregen
    12: ATTR_CONDITION_SNOWY_RAINY,     # Schneeregen
    13: ATTR_CONDITION_SNOWY_RAINY,     # Schneeregen
    14: ATTR_CONDITION_SNOWY,           # leichter Schneefall
    15: ATTR_CONDITION_SNOWY,           # mäßiger Schneefall
    16: ATTR_CONDITION_HAIL,          # starker Schneefall
    17: ATTR_CONDITION_RAINY,          # Regenschauer
    18: ATTR_CONDITION_RAINY,          # Regenschauer
    19: ATTR_CONDITION_POURING,       # starker Regenschauer
    20: ATTR_CONDITION_SNOWY_RAINY,       # Schneeregenschauer
    21: ATTR_CONDITION_SNOWY_RAINY,       # Schneeregenschauer
    22: ATTR_CONDITION_SNOWY_RAINY,       # Schneeregenschauer
    23: ATTR_CONDITION_SNOWY,       # Schneeschauer
    24: ATTR_CONDITION_SNOWY,       # Schneeschauer
    25: ATTR_CONDITION_HAIL,       # starker Schneeschauer
    26: ATTR_CONDITION_SNOWY_RAINY,       # Gewitter
    27: ATTR_CONDITION_SNOWY_RAINY,       # Gewitter
    28: ATTR_CONDITION_LIGHTNING,           # starkes Gewitter
    29: ATTR_CONDITION_SNOWY_RAINY,           # Gewitter mit Schneefall
    30: ATTR_CONDITION_LIGHTNING,           # starkes Gewitter mit Schneefall
    31: ATTR_CONDITION_LIGHTNING_RAINY,# Gewitter mit Schneefall
    32: ATTR_CONDITION_LIGHTNING_RAINY,     # Test: Lightning (no rain)
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Set up the Geosphere.at weather platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [GeosphereWeather(coordinator)]
    async_add_entities(entities)
    
class GeosphereWeather(WeatherEntity):
    """Representation of a Geosphere.at weather entity."""
    
    _attr_has_entity_name = True
    _attr_name = "Aktuelles Wetter"
    
    def __init__(self, coordinator):
        """Initialize the weather entity."""
        self.coordinator = coordinator
        
        config_mode = coordinator.config_entry.data.get("mode")
        point_id = coordinator.config_entry.data.get("point_id")
        latitude = coordinator.config_entry.data.get("latitude")
        longitude = coordinator.config_entry.data.get("longitude")
        self.nowcast_enabled = coordinator.config_entry.options.get("nowcast_enabled", False)
        
        # ← NAME basierend auf Konfiguration
        if config_mode == MODE_REGIONAL:
            # if self.nowcast_enabled:
            #     self._attr_unique_id = f"geosphere_at_{point_id}_hybrid"
            # else:
            self._attr_unique_id = f"geosphere_at_{point_id}"
            self._attr_supported_features = (
                WeatherEntityFeature.FORECAST_DAILY |
                WeatherEntityFeature.FORECAST_HOURLY
            )
        else:
            self._attr_unique_id = f"geosphere_at_weather_{latitude}_{longitude}"
            self._attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY
        
        # ← super().__init__() OHNE Parameter aufrufen!
        super().__init__()
        
        self._setup_location_from_config()
    
    def _setup_location_from_config(self):
        """Setup location from config."""
        config_mode = self.coordinator.config_entry.data.get("mode")
        
        if config_mode == MODE_REGIONAL:
            regional_flexi = self.coordinator.get_regional_flexi_data
            if regional_flexi and "features" in regional_flexi:
                coords = regional_flexi["features"][0].get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    self._longitude = coords[0]
                    self._latitude = coords[1]
                    return
        
        self._latitude = self.coordinator.config_entry.data.get("latitude")
        self._longitude = self.coordinator.config_entry.data.get("longitude")
        
        if self._latitude is None or self._longitude is None:
            all_data = self.coordinator.data or {}
            if all_data.get("hybrid") and "features" in all_data["hybrid"]:
                coords = all_data["hybrid"]["features"][0].get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    self._longitude = coords[0]
                    self._latitude = coords[1]
            elif all_data.get("nowcast") and "features" in all_data["nowcast"]:
                coords = all_data["nowcast"]["features"][0].get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    self._longitude = coords[0]
                    self._latitude = coords[1]
            elif all_data.get("regional_flexi") and "features" in all_data["regional_flexi"]:
                coords = all_data["regional_flexi"]["features"][0].get("geometry", {}).get("coordinates", [])
                if len(coords) >= 2:
                    self._longitude = coords[0]
                    self._latitude = coords[1]
    
    @property
    def native_temperature(self):
        """Return the temperature. Priority: Nowcast first, then Hybrid/Regional."""
        config_mode = self.coordinator.config_entry.data.get("mode")
        
        # Priority 1: Nowcast (immer aktuell, 15-min Intervalle)
        nowcast = self.coordinator.get_nowcast_data
        if nowcast and "features" in nowcast:
            params = nowcast["features"][0].get("properties", {}).get("parameters", {})
            t2m_data = params.get("t2m", {}).get("data", [])
            timestamps = nowcast.get("timestamps", [])
            
            if t2m_data and timestamps:
                idx = self._get_current_data_index(timestamps)  # ← Richtiger Index!
                _LOGGER.debug("Nowcast temp: idx=%d/%d, value=%s", idx, len(t2m_data), t2m_data[idx] if idx < len(t2m_data) else "N/A")
                if idx < len(t2m_data) and t2m_data[idx] is not None:
                    temp = float(t2m_data[idx])
                    _LOGGER.debug("Using Nowcast temperature: %s°C", temp)
                    return temp
        
        # Priority 2: Hybrid (nur wenn Nowcast nicht verfügbar)
        hybrid = self.coordinator.get_hybrid_data
        if hybrid and "features" in hybrid:
            params = hybrid["features"][0].get("properties", {}).get("parameters", {})
            t2m_data = params.get("t2m", {}).get("data", [])
            timestamps = hybrid.get("timestamps", [])
            
            if t2m_data and timestamps:
                idx = self._get_current_data_index(timestamps)  # ← Auch hier Index nutzen!
                if idx < len(t2m_data) and t2m_data[idx] is not None:
                    return float(t2m_data[idx])
        
        # Priority 3: Regional Flexi fallback
        flexi = self.coordinator.get_regional_flexi_data
        if flexi:
            timestamps = flexi.get("timestamps", [])
            props = flexi["features"][0].get("properties", {})
            parameters = props.get("parameters", {})
            t2m_data = parameters.get("t2m", {}).get("data", [])
            
            if t2m_data and timestamps:
                idx = self._get_current_data_index(timestamps)
                if idx < len(t2m_data) and t2m_data[idx] is not None:
                    return float(t2m_data[idx])
        
        _LOGGER.warning("Keine Temperatur verfügbar!")
        return None
    
    @property
    def native_wind_speed(self):
        """Return the wind speed. Priority: Hybrid → Nowcast → Regional."""
        hybrid = self.coordinator.get_hybrid_data
        if hybrid and "features" in hybrid:
            params = hybrid["features"][0].get("properties", {}).get("parameters", {})
            ff_data = params.get("ff", {}).get("data", [])
            if ff_data and len(ff_data) > 0 and ff_data[0] is not None:
                return float(ff_data[0]) * 3.6
        
        nowcast = self.coordinator.get_nowcast_data
        if nowcast and "features" in nowcast:
            params = nowcast["features"][0].get("properties", {}).get("parameters", {})
            ff_data = params.get("ff", {}).get("data", [])
            if ff_data and len(ff_data) > 0 and ff_data[0] is not None:
                return float(ff_data[0]) * 3.6
        
        flexi = self.coordinator.get_regional_flexi_data
        if flexi:
            timestamps = flexi.get("timestamps", [])
            idx = self._get_current_data_index(timestamps)
            props = flexi["features"][0].get("properties", {})
            parameters = props.get("parameters", {})
            ff_data = parameters.get("ff", {}).get("data", [])
            if ff_data and idx < len(ff_data) and ff_data[idx] is not None:
                return float(ff_data[idx])
        
        return None
    
    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        flexi = self.coordinator.get_regional_flexi_data
        if flexi:
            timestamps = flexi.get("timestamps", [])
            idx = self._get_current_data_index(timestamps)
            props = flexi["features"][0].get("properties", {})
            parameters = props.get("parameters", {})
            dd_data = parameters.get("dd", {}).get("data", [])
            if dd_data and idx < len(dd_data) and dd_data[idx] is not None:
                return int(dd_data[idx])
        
        return None
    
    @property
    def condition(self):
        """Return the current condition. Uses Hybrid sy if available."""
        hybrid = self.coordinator.get_hybrid_data
        if hybrid and "features" in hybrid:
            params = hybrid["features"][0].get("properties", {}).get("parameters", {})
            sy_data = params.get("sy", {}).get("data", [])
            
            if sy_data and len(sy_data) > 0 and sy_data[0] is not None:
                current_symbol = int(sy_data[0])
                condition = SYMBOL_TO_CONDITION.get(current_symbol, ATTR_CONDITION_EXCEPTIONAL)
                
                current_local_dt = dt_util.as_local(datetime.now(timezone.utc))
                return self._adjust_condition_for_night(condition, current_local_dt, is_daily_forecast=False)
        
        flexi = self.coordinator.get_regional_flexi_data
        if flexi and "features" in flexi:
            timestamps = flexi.get("timestamps", [])
            idx = self._get_current_data_index(timestamps)
            props = flexi["features"][0].get("properties", {})
            parameters = props.get("parameters", {})
            sy_data = parameters.get("sy", {}).get("data", [])
            
            if sy_data and idx < len(sy_data) and sy_data[idx] is not None:
                current_symbol = int(sy_data[idx])
                condition = SYMBOL_TO_CONDITION.get(current_symbol, ATTR_CONDITION_EXCEPTIONAL)
                
                current_local_dt = dt_util.as_local(datetime.now(timezone.utc))
                return self._adjust_condition_for_night(condition, current_local_dt, is_daily_forecast=False)
        
        nowcast = self.coordinator.get_nowcast_data
        if nowcast and "features" in nowcast:
            params = nowcast["features"][0].get("properties", {}).get("parameters", {})
            t2m_data = params.get("t2m", {}).get("data", [])
            rr_data = params.get("rr", {}).get("data", [])
            
            if t2m_data and rr_data:
                precip = float(rr_data[0]) if rr_data[0] is not None else 0
                current_local_dt = dt_util.as_local(datetime.now(timezone.utc))
                is_night = self._is_nighttime_for_forecast(current_local_dt, is_daily_forecast=False)
                
                if precip > 0.5:
                    return ATTR_CONDITION_RAINY
                elif precip > 0:
                    return ATTR_CONDITION_PARTLYCLOUDY
                else:
                    return ATTR_CONDITION_CLEAR_NIGHT if is_night else ATTR_CONDITION_SUNNY
        
        return ATTR_CONDITION_PARTLYCLOUDY
    
    @property
    def native_precipitation_unit(self):
        return UnitOfPrecipitationDepth.MILLIMETERS
    
    @property
    def native_temperature_unit(self):
        return UnitOfTemperature.CELSIUS
    
    @property
    def native_wind_speed_unit(self):
        return UnitOfSpeed.KILOMETERS_PER_HOUR
    
    @property
    def native_pressure(self):
        return None
    
    @property
    def humidity(self):
        return None
    
    @property
    def native_visibility(self):
        return None
    
    @property
    def device_info(self):
        config_mode = self.coordinator.config_entry.data.get("mode")
        point_id = self.coordinator.config_entry.data.get("point_id")
        latitude = self.coordinator.config_entry.data.get("latitude")
        longitude = self.coordinator.config_entry.data.get("longitude")
        location_name = self.coordinator.config_entry.data.get("location_name", "Lokal")
        nowcast_enabled = self.coordinator.nowcast_enabled
        
        if config_mode == MODE_REGIONAL:
            # ← WICHTIG: Device Identifiers bleiben STABIL, egal ob Hybrid oder nicht!
            device_name = f"Geosphere Austria - {location_name}"
            # ← MODEL NICHT ÄNDERN - immer gleichen Wert!
            model = "Geosphere Austria"
            unique_id = f"geosphere_at_device_{point_id}"
        else:
            device_name = f"Geosphere {self.coordinator.name}"
            model = "Geosphere Austria Nowcast"
            unique_id = f"geosphere_at_device_{latitude}_{longitude}"
        
        return {
            "identifiers": {(DOMAIN, unique_id)},
            "name": device_name,
            "manufacturer": "GeoSphere Austria",
            "model": model,  # ← Bleibt gleich bei Hybrid/Regional Switch
            "entry_type": "service",
        }
    
    async def async_added_to_hass(self):
        """Register callbacks."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
    
    async def async_will_remove_from_hass(self):
        """Will be called just before removing the entity."""
        # ← Bereitet saubere Entfernung vor
        await super().async_will_remove_from_hass()
    
    async def async_forecast_daily(self):
        """Return daily forecast - NONE for local mode."""
        config_mode = self.coordinator.config_entry.data.get("mode")
        
        # LOCAL MODE: No daily forecast (only hourly via Nowcast)
        if config_mode in [MODE_LOCAL_NEW, MODE_LOCAL_UPDATE]:
            _LOGGER.debug("Local mode detected - returning no daily forecast")
            return None
        
        # REGIONAL MODE: Return daily forecast
        return self._format_daily_forecast()
    
    async def async_forecast_hourly(self):
        """Return hourly forecast."""
        # ← PRIORITÄT: Hybrid > Nowcast > Flexi
        hybrid = self.coordinator.get_hybrid_data
        if hybrid:
            return self._format_hourly_from_source(
                data=hybrid,  # ← NICHT 'hybrid_data=', sondern 'data='!
                is_hybrid=True,
                use_nowcast_values=False
            )
        
        nowcast = self.coordinator.get_nowcast_data
        if nowcast:
            return self._format_hourly_from_source(
                data=nowcast,  # ← Auch hier 'data='!
                is_hybrid=False,
                nowcast_only=True
            )
        
        flexi = self.coordinator.get_regional_flexi_data
        if flexi:
            return self._format_hourly_from_source(data=flexi, is_hybrid=False)
        
        return None
    
    def _format_daily_forecast(self):
        """Daily forecast from regional data."""
        daily = self.coordinator.get_regional_daily_data
        if not daily or "features" not in daily or len(daily["features"]) == 0:
            return None

        props = daily["features"][0].get("properties", {})
        forecast_list = props.get("forecast", [])
        
        forecasts = []
        for day in forecast_list:
            try:
                dt_str = day.get("time")
                dt_utc = self._parse_timestamp(dt_str)
                local_dt = self._utc_to_local(dt_utc) if dt_utc else None
                
                condition = SYMBOL_TO_CONDITION.get(day.get("symbol", 1), ATTR_CONDITION_EXCEPTIONAL)
                adjusted_condition = self._adjust_condition_for_night(condition, local_dt, is_daily_forecast=True) if local_dt else condition
                
                entry = {
                    "datetime": local_dt.isoformat() if local_dt else dt_str,
                    "condition": adjusted_condition,
                    "temperature": float(day.get("high", 0)),
                    "templow": float(day.get("low", 0)),
                }
                
                if day.get("rr") is not None:
                    entry["precipitation"] = float(day.get("rr", 0))
                
                forecasts.append(entry)
            except Exception as err:
                _LOGGER.warning("Error formatting daily forecast: %s", err)
                continue
        
        return forecasts
    
    def _format_hourly_forecast(self, flexi_data=None, nowcast_data=None, hybrid_data=None, is_hybrid=False):
        """Format hourly forecast from various data sources."""
        if hybrid_data:
            return self._format_hourly_from_source(
                hybrid_data,
                is_hybrid=True,
                use_nowcast_values=is_hybrid
            )
        
        if flexi_data:
            return self._format_hourly_from_source(flexi_data)
        
        if nowcast_data:
            return self._format_hourly_from_source(nowcast_data, is_hybrid=False, nowcast_only=True)
        
        return self._format_hourly_from_source(self.coordinator.get_regional_flexi_data)
    
    def _format_hourly_from_source(self, data, is_hybrid=False, use_nowcast_values=False, nowcast_only=False):
        """Format hourly from given data source."""
        if not data or "features" not in data or len(data["features"]) == 0:
            return None
        
        timestamps = data.get("timestamps", [])
        if not timestamps:
            return None
        
        props = data["features"][0].get("properties", {})
        parameters = props.get("parameters", {})
        
        # Alle Parameter extrahieren
        t2m_data = parameters.get("t2m", {}).get("data", [])
        ff_data = parameters.get("ff", {}).get("data", [])
        dd_data = parameters.get("dd", {}).get("data", []) if "dd" in parameters else []
        fx_data = parameters.get("fx", {}).get("data", []) if "fx" in parameters else []
        rr_data = parameters.get("rr", {}).get("data", [])
        sy_data = parameters.get("sy", {}).get("data", []) if "sy" in parameters else []
        
        forecasts = []
        now_utc = datetime.now(timezone.utc)
        
        for i, ts_str in enumerate(timestamps):
            try:
                ts = self._parse_timestamp(ts_str)
                if not ts:
                    continue
                
                # ← STRIKTE FILTERUNG: Nur Zukunft + 30min Puffer
                # Alles was OLDER 30 Minuten zurückliegt wird gefiltert
                if ts < now_utc - timedelta(minutes=30):
                    continue
                                
                local_dt = self._utc_to_local(ts)
                
                # Wetterbedingung
                if is_hybrid and sy_data and len(sy_data) > i and sy_data[i] is not None:
                    current_symbol = int(sy_data[i])
                    condition = SYMBOL_TO_CONDITION.get(current_symbol, ATTR_CONDITION_EXCEPTIONAL)
                    condition = self._adjust_condition_for_night(condition, local_dt, is_daily_forecast=False)
                else:
                    precip = float(rr_data[i]) if i < len(rr_data) and rr_data[i] is not None else 0
                    if precip > 0.5:
                        condition = ATTR_CONDITION_RAINY
                    elif precip > 0:
                        condition = ATTR_CONDITION_PARTLYCLOUDY
                    else:
                        is_night = self._is_nighttime_for_forecast(local_dt, is_daily_forecast=False)
                        condition = ATTR_CONDITION_CLEAR_NIGHT if is_night else ATTR_CONDITION_SUNNY
                
                entry = {
                    "datetime": local_dt.isoformat(),
                    "condition": condition,
                    "temperature": float(t2m_data[i]) if i < len(t2m_data) and t2m_data[i] is not None else None,
                    "wind_speed": float(ff_data[i]) * 3.6 if i < len(ff_data) and ff_data[i] is not None else None,
                }
                
                if i < len(dd_data) and dd_data[i] is not None:
                    entry["wind_bearing"] = int(dd_data[i])
                
                if i < len(fx_data) and fx_data[i] is not None:
                    entry["wind_gust_speed"] = float(fx_data[i]) * 3.6
                
                if i < len(rr_data) and rr_data[i] is not None:
                    entry["precipitation"] = float(rr_data[i])
                
                forecasts.append(entry)
                                    
            except Exception as err:
                _LOGGER.warning("Error formatting hourly at index %d: %s", i, err)
                continue
        
        return forecasts

    def _parse_timestamp(self, ts_str: str) -> datetime | None:
        try:
            return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            return None
    
    def _utc_to_local(self, utc_dt: datetime) -> datetime:
        return dt_util.as_local(utc_dt)
    
    def _get_current_data_index(self, timestamps: list[str]) -> int:
        if not timestamps:
            return 0
        
        now_utc = datetime.now(timezone.utc)
        best_index = 0
        min_diff = float('inf')
        
        for i, ts_str in enumerate(timestamps):
            ts = self._parse_timestamp(ts_str)
            if ts:
                diff = abs((now_utc - ts).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    best_index = i
        
        return best_index
    
    def _calculate_sun_times_for_date(self, target_date: datetime) -> tuple[datetime, datetime] | None:
        hass = self.coordinator.hass
        sun_state = hass.states.get("sun.sun")
        
        if not sun_state:
            _LOGGER.warning("Sun entity not found, cannot calculate sun times")
            return None
        
        next_dawn_attr = sun_state.attributes.get("next_dawn")
        next_dusk_attr = sun_state.attributes.get("next_dusk")
        
        if not next_dawn_attr or not next_dusk_attr:
            _LOGGER.warning("Next dawn/dusk attributes not found")
            return None
        
        try:
            next_dawn_utc = datetime.fromisoformat(next_dawn_attr.replace('Z', '+00:00'))
            next_dusk_utc = datetime.fromisoformat(next_dusk_attr.replace('Z', '+00:00'))
            
            next_dawn = dt_util.as_local(next_dawn_utc)
            next_dusk = dt_util.as_local(next_dusk_utc)
            
            target_local = dt_util.as_local(target_date)
            target_date_only = target_local.date()
            
            # ← FIX: Dawn und Dusk unabhängig voneinander auf das Zieldatum verschieben,
            #        da next_dawn und next_dusk an unterschiedlichen Kalendertagen liegen können
            dawn_days_ahead = (target_date_only - next_dawn.date()).days
            dusk_days_ahead = (target_date_only - next_dusk.date()).days
            
            dawn_for_target = next_dawn_utc + timedelta(days=dawn_days_ahead)
            dusk_for_target = next_dusk_utc + timedelta(days=dusk_days_ahead)
            
            return dawn_for_target, dusk_for_target
            
        except Exception as err:
            _LOGGER.error("Error calculating sun times for date %s: %s", target_date, err)
            return None
    
    def _is_nighttime_for_forecast(self, forecast_datetime: datetime, is_daily_forecast: bool = False) -> bool:
        if not forecast_datetime:
            return False
        
        if is_daily_forecast:
            return False
        
        sun_times = self._calculate_sun_times_for_date(forecast_datetime)
        
        if not sun_times:
            local_hour = dt_util.as_local(forecast_datetime).hour
            return local_hour >= 20 or local_hour < 5
        
        dawn_utc, dusk_utc = sun_times
        forecast_utc = forecast_datetime.astimezone(timezone.utc)
        is_night = forecast_utc < dawn_utc or forecast_utc >= dusk_utc
        
        return is_night
    
    def _adjust_condition_for_night(self, condition: str, forecast_datetime: datetime, is_daily_forecast: bool = False) -> str:
        if condition != ATTR_CONDITION_SUNNY:
            return condition
        
        if is_daily_forecast:
            return ATTR_CONDITION_SUNNY
        
        is_night = self._is_nighttime_for_forecast(forecast_datetime, is_daily_forecast=False)
        
        if is_night:
            return ATTR_CONDITION_CLEAR_NIGHT
        else:
            return ATTR_CONDITION_SUNNY