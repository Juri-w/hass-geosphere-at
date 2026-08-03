import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfSpeed, UnitOfPrecipitationDepth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Deutsche Bezeichnungen
SENSOR_NAMES = {
    "wind_speed": "Windgeschwindigkeit",
    "gusts": "Windböen",
    "wind_direction": "Windrichtung",
    "precipitation": "Niederschlag",
    "fog_index": "Sichtindex",
    "temperature": "Lufttemperatur",
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Set up the Geosphere.at sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    entities = [
        GeosphereSensor(coordinator, "wind_speed", UnitOfSpeed.KILOMETERS_PER_HOUR, "ff", 1),
        GeosphereSensor(coordinator, "gusts", UnitOfSpeed.KILOMETERS_PER_HOUR, "fx", 0),
        GeosphereSensor(coordinator, "wind_direction", None, "dd", 0),
        GeosphereSensor(coordinator, "precipitation", UnitOfPrecipitationDepth.MILLIMETERS, "rr", 1),
        GeosphereSensor(coordinator, "fog_index", None, "sy", 0),
        GeosphereSensor(coordinator, "temperature", UnitOfTemperature.CELSIUS, "t2m", 1),
    ]
    
    async_add_entities(entities)

class GeosphereSensor(SensorEntity):
    """Representation of a Geosphere.at sensor."""
    
    _attr_has_entity_name = True
    
    def __init__(self, coordinator, sensor_type, unit_of_measurement, data_key, decimal_precision):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.sensor_type = sensor_type
        self.unit = unit_of_measurement
        self.data_key = data_key
        self.decimal = decimal_precision
        
        # Entity-ID ohne ID-Zahl am Ende
        self._attr_unique_id = f"geosphere_at_{coordinator.point_id}_{sensor_type}"
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_class = self._get_device_class(sensor_type)
        self._attr_state_class = SensorStateClass.MEASUREMENT
        
    def _get_device_class(self, sensor_type):
        """Return the appropriate device class."""
        device_classes = {
            "temperature": SensorDeviceClass.TEMPERATURE,
            "wind_speed": SensorDeviceClass.WIND_SPEED,
            "precipitation": SensorDeviceClass.PRECIPITATION,  # ← KORREKTUR: ohne _RATE
        }
        return device_classes.get(sensor_type)
    
    @property
    def name(self):
        """Return the display name of the sensor (German)."""
        german_name = SENSOR_NAMES.get(self.sensor_type, self.sensor_type.title())
        return f"{german_name} {self.coordinator.location_name}"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        flexi = self.coordinator.get_flexi_data
        
        if not flexi or "features" not in flexi or len(flexi["features"]) == 0:
            return None
        
        props = flexi["features"][0].get("properties", {})
        params = props.get("parameters", {})
        
        data_array = params.get(self.data_key, {}).get("data", [])
        if data_array:
            val = data_array[-1]
            # Decimal precision rounding
            if self.decimal == 0:
                return int(val)
            return round(float(val), self.decimal)
        
        return None
    
    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.point_id)},
            "name": f"Geosphere Austria - {self.coordinator.location_name}",
            "manufacturer": "GeoSphere Austria",
            "model": "Forecast API",
            "entry_type": "service",
        }
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))