"""TFA.me station integration: ___init___.py."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_INTERVAL, DOMAIN
from .coordinator import TFAmeDataCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


# ---- TFA.me station setup ----
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a TFA.me station."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_IP_ADDRESS]
    up_interval = entry.data[CONF_INTERVAL]
    # Get option for alter user changes
    interval_opt = entry.options.get(CONF_INTERVAL, -1)
    if interval_opt != -1:
        up_interval = interval_opt
    # Update time
    msg: str = "Pull interval: " + str(up_interval)
    _LOGGER.info(msg)

    delta_interval = timedelta(seconds=up_interval)

    # DataUpdateCoordinator for cyclic requests
    coordinator = TFAmeDataCoordinator(hass, host, delta_interval)

    # Register listener for option changes
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    # Save coordinator for later usage
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # First request for sensor data
    await coordinator.async_config_entry_first_refresh()
    # Save coordinator
    entry.runtime_data = coordinator

    _LOGGER.debug("Setting up platforms")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ---- Options update listener: option is pull/request interval ----
async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Will be called when options are changed."""
    new_interval = entry.options.get(CONF_INTERVAL, 10)
    msg: str = "Options changed new pull interval: " + str(new_interval)
    _LOGGER.info(msg)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval = timedelta(seconds=new_interval)
    await coordinator.async_refresh()
