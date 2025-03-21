"""TFA.me station integration: ___init___.py."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_IP_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_INTERVAL, CONF_MULTIPLE_ENTITIES, DOMAIN
from .coordinator import TFAmeDataCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


@dataclass
class TFAmeData:
    """Store runtime data."""

    def __init__(self, host: str) -> None:
        """Initialisiert den Client mit der Zieladresse."""
        self.host = host

    async def get_identifier(self) -> str:
        """Request a unique ID from a device."""
        # We just take the host name
        #    url = f"{self.base_url}/identifier"
        #    async with aiohttp.ClientSession() as session:
        #        async with session.get(url, timeout=10) as response:
        #            if response.status != 200:
        #                raise MyException("Fehler beim Abrufen der ID")
        #           data = await response.json()
        #            return data.get("id")
        return self.host


class MyException(Exception):
    """User definined exception for error in client."""


type TFAmeConfigEntry = ConfigEntry[TFAmeData]


# ---- TFA.me station setup ----
async def async_setup_entry(hass: HomeAssistant, entry: TFAmeConfigEntry) -> bool:
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

    # Use multiple entities
    multiple_entities = entry.data[CONF_MULTIPLE_ENTITIES]

    # DataUpdateCoordinator for cyclic requests
    coordinator = TFAmeDataCoordinator(hass, host, delta_interval, multiple_entities)

    # Register listener for option changes
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    # Save coordinator for later usage
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # First request for sensor data
    await coordinator.async_config_entry_first_refresh()
    # Save coordinator
    entry.runtime_data = coordinator

    assert entry.unique_id

    _LOGGER.debug("Setting up platforms")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Get running instances
    instances = await get_instances(hass)
    msg = f"Instances: {len(instances)}"
    _LOGGER.info(msg)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


# ---- Options update listener: option is pull/request interval ----
async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Will be called when options are changed."""

    reset_rain = entry.options.get("action_rain", False)
    msg: str = "Options 'reset rain': " + str(reset_rain)
    _LOGGER.info(msg)

    new_interval = entry.options.get(CONF_INTERVAL, 10)
    msg: str = "Options 'pull interval': " + str(new_interval)
    _LOGGER.info(msg)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval = timedelta(seconds=new_interval)

    await coordinator.async_refresh()


async def get_instances(hass: HomeAssistant):
    """Find all instances of this integration."""
    return hass.config_entries.async_entries("a_tfa_me_1")


async def get_running_instances(hass: HomeAssistant):
    """Find all running instances of this integration."""
    entries = hass.config_entries.async_entries("a_tfa_me_1")

    running_instances = {}
    for entry in entries:
        if entry.state == "loaded":  # Verifies wether integration is active or not
            running_instances.append(entry)

    return running_instances
