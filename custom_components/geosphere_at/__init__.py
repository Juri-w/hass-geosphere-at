"""Init for Geosphere Austria integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Geosphere component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Geosphere from a config entry."""
    from .coordinator import async_setup_entry as coordinator_setup
    return await coordinator_setup(hass, entry)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from .coordinator import async_unload_entry as coordinator_unload
    return await coordinator_unload(hass, entry)

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry."""
    from .coordinator import async_reload_entry as coordinator_reload
    await coordinator_reload(hass, entry)