"""Options flow for Geosphere Austria integration."""

import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    MODE_REGIONAL,
)

_LOGGER = logging.getLogger(__name__)

class GeosphereOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Geosphere Austria."""
    
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.current_options = dict(config_entry.options) if config_entry.options else {}
    
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        
        entry_mode = self.config_entry.data.get("mode")
        _LOGGER.info("Options flow started for mode: %s", entry_mode)
        
        if user_input is not None:
            _LOGGER.info("Options received: %s", user_input)
            
            new_options = {
                "nowcast_enabled": user_input.get("nowcast_enabled", False),
            }
            
            if user_input.get("nowcast_enabled", False):
                try:
                    lat = user_input.get("nowcast_latitude")
                    lon = user_input.get("nowcast_longitude")
                    
                    if not lat or not lon:
                        errors["base"] = "invalid_coordinates"
                    else:
                        lat = float(lat)
                        lon = float(lon)
                        
                        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                            errors["base"] = "invalid_coordinates"
                        else:
                            new_options["nowcast_latitude"] = lat
                            new_options["nowcast_longitude"] = lon
                except (ValueError, TypeError):
                    errors["base"] = "invalid_coordinates"
            
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=new_options
                )
                
                await self.hass.config_entries.async_reload(
                    self.config_entry.entry_id
                )
                
                return self.async_create_entry(title="Konfiguration gespeichert", data=new_options)
        else:
            _LOGGER.debug("Initialising options form")
        
        # ← Defaults für Formular
        nowcast_enabled = self.current_options.get("nowcast_enabled", False)
        nowcast_lat = self.current_options.get("nowcast_latitude", 48.2082)
        nowcast_lon = self.current_options.get("nowcast_longitude", 16.3738)
        
        # ← Unterschiedliches Formular je nach Modus
        schema_dict = {
            vol.Optional("nowcast_enabled", default=nowcast_enabled): bool,
        }
        
        # ← Nur bei REGIONAL-Modus Koordinaten anzeigen (Hybrid möglich)
        if entry_mode == MODE_REGIONAL:
            schema_dict.update({
                vol.Optional("nowcast_latitude", default=nowcast_lat): vol.Coerce(float),
                vol.Optional("nowcast_longitude", default=nowcast_lon): vol.Coerce(float),
            })
            _LOGGER.info("Showing Hybrid config for regional entry")
        else:
            _LOGGER.info("Local mode - no Hybrid option available")
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )