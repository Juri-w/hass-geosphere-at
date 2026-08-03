"""Config flow for Geosphere Austria integration."""

import logging
from typing import Any
import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .options_flow import GeosphereOptionsFlowHandler
from .const import (
    DOMAIN,
    API_POINTS,
    MODE_REGIONAL,
    MODE_LOCAL_NEW,
    MODE_LOCAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

class GeosphereConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Geosphere Austria."""
    
    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._mode: str | None = None
    
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input and len(user_input) > 0:
            mode = user_input.get("mode")
            self._mode = mode
            if mode and hasattr(self, f"async_step_{mode}"):
                return await getattr(self, f"async_step_{mode}")(user_input)
        
        # ← ANZEIGEN: Welche Einträge gibt's schon?
        existing_entries = {}
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            entry_mode = entry.data.get("mode")
            title = entry.title
            
            # Hybrid-Markierung für bereits konfigurierte Einträge
            if entry.options.get("nowcast_enabled"):
                title += " ⚡ Hybrid"
            elif entry_mode == MODE_REGIONAL:
                title += " (Regional)"
            else:
                title += " (Lokal)"
            
            existing_entries[entry.entry_id] = title
        
        # ← HINZUFÜGEN: Nur diese beiden Modi (keine local_update!)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("mode"): vol.In({
                    MODE_REGIONAL: "Regional (Neuer Standort nach Bezirk/Gemeinde)",
                    MODE_LOCAL_NEW: "Lokal (Neuer Hub mit Lat/Lon - Nur Nowcast)",
                }),
            }),
            errors=errors,
        )
    
    async def async_step_regional(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Regional setup - point selection."""
        errors: dict[str, str] = {}
        
        # ← IMMER Locations laden (auch bei leerem user_input!)
        locations = await self._fetch_locations()
        
        # ← NUR bei echter Eingabe verarbeiten (nicht bei leerem Dict/None)
        if user_input and len(user_input) > 0:
            selected_point_id = user_input.get("point_id")
            
            # ← Erst jetzt validieren
            if selected_point_id is None or str(selected_point_id).strip() == "":
                errors["base"] = "invalid_selection"
            else:
                selected_loc = next(
                    (loc for loc in locations if str(loc["point_id"]) == str(selected_point_id)),
                    None
                )
                
                if not selected_loc:
                    errors["base"] = "invalid_selection"
                else:
                    await self.async_set_unique_id(f"regional_{selected_point_id}")
                    self._abort_if_unique_id_configured()
                    
                    final_point_id = str(selected_point_id).strip()
                    data = {
                        "mode": MODE_REGIONAL,
                        "point_id": final_point_id,
                        "location_name": selected_loc["name"],
                        "bundesland": selected_loc.get("bundesland"),
                    }
                    
                    return self.async_create_entry(
                        title=f"Geosphere {selected_loc['name']}",
                        data=data,
                    )
        
        # ← FORMULAR zeigen (bei user_input=None oder bei Fehlern)
        location_map = {
            str(loc["point_id"]): f"{loc['name']} ({loc.get('bundesland', 'Unbekannt')})" 
            for loc in locations
        }
        
        return self.async_show_form(
            step_id="regional",
            data_schema=vol.Schema({
                vol.Required("point_id"): vol.In(location_map),
            }),
            errors=errors,
        )
    
    async def async_step_local_new(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Local mode - new hub with lat/lon."""
        errors: dict[str, str] = {}
        
        if user_input and len(user_input) > 0:
            try:
                name = user_input.get("name", "")
                lat = user_input.get("latitude")
                lon = user_input.get("longitude")
                
                if not name:
                    name = f"Lokal {lat:.4f}, {lon:.4f}"
                
                if not lat or not lon:
                    errors["base"] = "invalid_coordinates"
                else:
                    lat = float(lat)
                    lon = float(lon)
                    
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        errors["base"] = "invalid_coordinates"
                    else:
                        await self.async_set_unique_id(f"local_{lat}_{lon}")
                        self._abort_if_unique_id_configured()
                        
                        data = {
                            "mode": MODE_LOCAL_NEW,
                            "name": name,
                            "latitude": lat,
                            "longitude": lon,
                        }
                        
                        return self.async_create_entry(
                            title=name,
                            data=data,
                        )
            except (ValueError, TypeError) as err:
                _LOGGER.error("Coordinate conversion failed: %s", err)
                errors["base"] = "invalid_coordinates"
        
        return self.async_show_form(
            step_id="local_new",
            data_schema=vol.Schema({
                vol.Optional("name"): str,
                vol.Required("latitude"): vol.Coerce(float),
                vol.Required("longitude"): vol.Coerce(float),
            }),
            errors=errors,
        )
    
    # async def async_step_local_update(self, user_input: dict[str, Any] | None = None) -> FlowResult:
    #     """Local mode - update existing regional sensor with Nowcast."""
    #     errors: dict[str, str] = {}
        
    #     if user_input and len(user_input) > 0:
    #         try:
    #             lat = user_input.get("latitude")
    #             lon = user_input.get("longitude")
    #             entry_id = user_input.get("existing_entry_id")
                
    #             if not lat or not lon:
    #                 errors["base"] = "invalid_coordinates"
    #             elif not entry_id:
    #                 errors["base"] = "no_entry_selected"
    #             else:
    #                 target_entry = self.hass.config_entries.async_get_entry(entry_id)
                    
    #                 if not target_entry:
    #                     errors["base"] = "invalid_entry"
    #                 elif target_entry.data.get("mode") != MODE_REGIONAL:
    #                     errors["base"] = "wrong_mode"
    #                 else:
    #                     lat = float(lat)
    #                     lon = float(lon)
                        
    #                     if not (-90 <= lat <= 90 and -180 <= lon <= 180):
    #                         errors["base"] = "invalid_coordinates"
    #                     else:
    #                         new_options = dict(target_entry.options) if target_entry.options else {}
    #                         new_options.update({
    #                             "nowcast_enabled": True,
    #                             "nowcast_latitude": lat,
    #                             "nowcast_longitude": lon,
    #                         })
                            
    #                         self.hass.config_entries.async_update_entry(
    #                             target_entry,
    #                             options=new_options
    #                         )
                            
    #                         self.hass.async_create_task(
    #                             self.hass.config_entries.async_reload(entry_id)
    #                         )
                            
    #                         return self.async_create_entry(
    #                             title="Nowcast aktiviert",
    #                             data={},
    #                         )
    #         except (ValueError, TypeError) as err:
    #             _LOGGER.error("Coordinate conversion failed: %s", err)
    #             errors["base"] = "invalid_coordinates"
        
    #     existing_entries = {}
    #     for entry in self.hass.config_entries.async_entries(DOMAIN):
    #         if entry.data.get("mode") == MODE_REGIONAL:
    #             existing_entries[entry.entry_id] = entry.title
        
    #     schema_dict = {}
    #     if existing_entries:
    #         schema_dict[vol.Optional("existing_entry_id")] = vol.In(existing_entries)
        
    #     schema_dict.update({
    #         vol.Required("latitude"): vol.Coerce(float),
    #         vol.Required("longitude"): vol.Coerce(float),
    #     })

    #     return self.async_show_form(
    #         step_id="local_update",
    #         data_schema=vol.Schema(schema_dict),
    #         errors=errors,
    #     )
    
    async def _fetch_locations(self):
        """Fetch available locations from API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(API_POINTS, timeout=10) as resp:
                    if resp.status == 200:
                        points = await resp.json()
                        return [
                            {
                                "point_id": str(p["point_id"]),
                                "name": p.get("name", f"Location {p['point_id']}"),
                                "bundesland": p.get("bundesland", "Unbekannt"),
                            }
                            for p in points
                        ]
        except Exception as err:
            _LOGGER.error("Could not fetch locations: %s", err)
            return [
                {"point_id": "2204", "name": "Wien", "bundesland": "Wien"},
                {"point_id": "101", "name": "Leithaprodersdorf", "bundesland": "Burgenland"},
            ]
        return []

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return GeosphereOptionsFlowHandler(config_entry)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
    pass

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
    pass