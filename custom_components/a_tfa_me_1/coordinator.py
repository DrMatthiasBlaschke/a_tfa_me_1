"""TFA.me station integration: coordinator.py."""

import asyncio
import logging
import socket

import aiohttp
from requests import HTTPError

from homeassistant.components.sensor import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# from homeassistant.helpers import aiohttp_client
# "requirements": ["aiohttp==3.11.12"],
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TFAmeDataCoordinator(DataUpdateCoordinator):
    """Class for managing data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        interval: timedelta,
        multiple_entities: bool,
    ) -> None:
        """Initialize data update coordinator."""
        self.host = host
        self.first_init = 0
        self.ha = hass
        self.sensor_entity_list = [str]  # [Entity ID strings]
        self.reset_rain_sensors = False
        self.multiple_entities = multiple_entities
        self.gateway_id = ""
        self.poll_interval = interval

        # self.devices = hass.config_entry.data.get("tfa_me_stations", [])

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=self.poll_interval)

    async def _async_update_data(self):
        """Request and update data."""
        parsed_data = {}  # dict

        # Try to get an IP for a mDNS host name:
        # - when IP can be solved it returns the IP
        # - when it is an IP it just returns the IP
        if "-" in self.host:
            # station ID, contains "-"
            mdns_name = f"tfa-me-{self.host:}.local"
            resolved_host = await self.resolve_mdns(mdns_name)
        else:
            resolved_host = self.host

        # Build the URL to the device and request all available sensors
        url = f"http://{resolved_host}/sensors"
        msg: str = "Request URL " + url
        _LOGGER.info(msg)
        try:
            async with aiohttp.ClientSession() as session:
                async with asyncio.timeout(5):  # 5 seconds timeout
                    async with session.get(url) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"HTTP Error {response.status}")  # noqa: TRY301

                        # Get JSON reply from response
                        json_data = await response.json()

                        # Parse JSON data
                        gateway_id: str = json_data.get("gateway_id", "tfame")
                        gateway_id = gateway_id.lower()
                        self.gateway_id = gateway_id

                        for sensor in json_data.get("sensors", []):
                            sensor_id = sensor["sensor_id"]

                            for measurement, values in sensor.get(
                                "measurements", {}
                            ).items():
                                if self.multiple_entities:
                                    entity_id = f"sensor.{gateway_id}_{sensor_id}_{measurement}"  # Entity ID
                                else:
                                    entity_id = (
                                        f"sensor.{sensor_id}_{measurement}"  # Entity ID
                                    )

                                parsed_data[entity_id] = {
                                    "sensor_id": sensor_id,
                                    "gateway_id": gateway_id,
                                    "sensor_name": sensor["name"],
                                    "measurement": measurement,
                                    "value": values["value"],
                                    "unit": values["unit"],
                                    "timestamp": sensor.get(
                                        "timestamp", "unknown"
                                    ),  # datetime.utcnow()
                                    "ts": sensor["ts"],
                                }

                                if measurement == "rain":
                                    entity_id_2 = f"{entity_id}_rel"  # Entity ID
                                    parsed_data[entity_id_2] = {
                                        "sensor_id": sensor_id,
                                        "gateway_id": gateway_id,
                                        "sensor_name": f"{sensor['name']} rel",
                                        "measurement": measurement,
                                        "value": values["value"],
                                        "unit": values["unit"],
                                        "timestamp": sensor.get(
                                            "timestamp", "unknown"
                                        ),  # datetime.utcnow()
                                        "ts": sensor["ts"],
                                        "reset_rain": self.reset_rain_sensors,
                                    }
                                    entity_id_3 = f"{entity_id}_hour"  # Entity ID
                                    parsed_data[entity_id_3] = {
                                        "sensor_id": sensor_id,
                                        "gateway_id": gateway_id,
                                        "sensor_name": f"{sensor['name']} hour",
                                        "measurement": measurement,
                                        "value": values["value"],
                                        "unit": values["unit"],
                                        "timestamp": sensor.get(
                                            "timestamp", "unknown"
                                        ),  # datetime.utcnow()
                                        "ts": sensor["ts"],
                                        "reset_rain": self.reset_rain_sensors,
                                    }

                        self.reset_rain_sensors = False
                        if self.first_init < 2:
                            self.first_init += 1
                        return parsed_data  # values are available with self.coordinator.data[self.entity_id]["keyword"]

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
