"""TFA.me station integration: coordinator.py."""

import asyncio
import logging
import socket

import aiohttp
from requests import HTTPError

from homeassistant.components.sensor import Entity, timedelta
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TFAmeDataCoordinator(DataUpdateCoordinator):
    """Class for managing data updates."""

    def __init__(self, hass: HomeAssistant, host: str, interval: timedelta) -> None:
        """Initialize data update coordinator."""
        self.host = host
        # self.sensors_x = {}
        self.first_init = 0
        self.ha = hass
        self.sensor_entity_list = {Entity}
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=interval
        )  # SCAN_INTERVAL)

    async def _async_update_data(self):
        """Request and update data."""
        parsed_data = {}  # dict

        # Try to get an IP for a mDNS host name:
        # - when IP can be solved it returns the IP
        # - when it is an IP it just returns the IP
        resolved_host = await self.resolve_mdns(self.host)

        # Build the URL to the device and request all available sensors
        url = f"http://{resolved_host}/sensors"
        msg: str = "Request URL " + url
        _LOGGER.info(msg)
        try:
            async with aiohttp.ClientSession() as session:
                async with asyncio.timeout(5):  # 10 seconds timeout
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"HTTP Error {response.status}")  # noqa: TRY301

                        # Get JSON reply from response
                        json_data = await response.json()

                        # Parse JSON data
                        # sensors_new = {}
                        for sensor in json_data.get("sensors", []):
                            sensor_id = sensor["sensor_id"]

                            for measurement, values in sensor.get(
                                "measurements", {}
                            ).items():
                                entity_id = (
                                    f"sensor.{sensor_id}_{measurement}"  # Entity ID
                                )
                                parsed_data[entity_id] = {
                                    "sensor_id": sensor_id,
                                    "sensor_name": sensor["name"],
                                    "measurement": measurement,
                                    "value": values["value"],
                                    "unit": values["unit"],
                                    "timestamp": sensor.get("timestamp", "unknown"),
                                }

                        if self.first_init < 2:
                            self.first_init += 1
                        return parsed_data

        except HTTPError as error:
            msg: str = "HTTP Error requesting data: " + str(error.__doc__)
            _LOGGER.error(msg)
            if self.first_init == 0:
                raise ConfigEntryNotReady(msg) from error  # Never updated
            raise UpdateFailed(msg) from error  # After first update

        except Exception as error:
            msg: str = "Exception requesting data: " + str(error.__doc__)
            _LOGGER.error(msg)
            if self.first_init == 0:
                raise ConfigEntryNotReady(msg) from error  # Never updated
            raise UpdateFailed(msg) from error  # After first update

    # ---- Try to resolve host name ----
    async def resolve_mdns(self, host_str: str) -> str:
        """Try to resolve host name and to get IP."""
        try:
            return socket.gethostbyname(host_str)  # Resolve: name to IP
        except socket.gaierror:
            return host_str  # Error, just return original string
