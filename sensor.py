"""TFA.me station integration: sensor.py."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import TFAmeDataCoordinator

# Used icons for entities, see also
# https://pictogrammers.com/library/mdi/
ICON_MAPPING = {
    "temperature": {
        "default": "mdi:thermometer",
        "high": "mdi:thermometer-high",
        "low": "mdi:thermometer-low",
    },
    "humidity": {"default": "mdi:water-percent", "alert": "mdi:water-percent-alert"},
    "co2": {"default": "mdi:molecule-co2"},
    "barometric_pressure": {"default": "mdi:gauge"},
    "rssi": {
        "default": "mdi:wifi",
        "weak": "mdi:wifi-strength-1",
        "middle": "mdi:wifi-strength-2",
        "good": "mdi:wifi-strength-3",
        "strong": "mdi:wifi-strength-4",
    },
    "lowbatt": {
        "default": "mdi:battery",
        "low": "mdi:battery-alert",
        "full": "mdi:battery",
    },
    "wind_direction": {"default": "mdi:compass-outline"},
    "wind": {
        "default": "mdi:weather-windy",
        "wind": "mdi:weather-windy-variant",
        "gust": "mdi:weather-windy",
    },
    "rain": {
        "none": "mdi:weather-sunny",
        "light": "mdi:weather-partly-rainy",
        "moderate": "mdi:weather-rainy",
        "heavy": "mdi:weather-pouring",
    },
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up TFA.me as Sensor."""

    # Get coordinator
    coordinator = entry.runtime_data
    # Initialize first refresh/request and wait for parsed JSON data from coordinator
    try:
        # await coordinator.async_config_entry_first_refresh()
        # Collect all entities (entities are part of device)
        sensors_start = []
        for entity_id in coordinator.data:
            sensor_id = coordinator.data[entity_id]["sensor_id"]
            sensors_start.append(TFAmeSensorEntity(coordinator, sensor_id, entity_id))

        # Add all entities
        async_add_entities(sensors_start, True)

    except Exception as error:
        raise ConfigEntryNotReady(
            f"Station not available: {error}"
        ) from error  # Fehler direkt hier abfangen

    # await coordinator.async_refresh()


# ----  ----
def update_entities(self, sensor_list: list):
    """Doc string."""
    _LOGGER.info("Test")
    # async_add_entities(sensor_list, True)

    # _my_hass.helpers.  async_add_entities(sensor_list, True)
    # _my_hass.add_job(async_add_entities, [sensor_list])


# ---- TFA.me sensor entity ----
class TFAmeSensorEntity(SensorEntity):
    """Represents in Home Assistant a single measurement of a sensor."""

    def __init__(
        self, coordinator: TFAmeDataCoordinator, sensor_id: str, entity_id: str
    ) -> None:
        """Initialize sensor entity."""
        self.coordinator = coordinator
        self.host = coordinator.host
        self.entity_id = entity_id
        self._attr_icon = ""
        self._attr_unique_id = entity_id  # just the entity ID
        self._attr_name = entity_id  # just the entity ID
        self._attr_device_info = {
            "identifiers": {(DOMAIN, sensor_id)},  # Unique ID for device/sensor
            "name": self.format_string_tfa_id(sensor_id),  # 'TFA.me XXX-XXX-XXX'
            "manufacturer": "TFA/Dostmann",
            "model": self.format_string_tfa_type(sensor_id),  # 'Sensor/Station type XX'
            # "sw_version": "1.0",
            # "hw_version": "1.0",
            # "serial_number": "123"
        }

        hex_value = int(sensor_id[:2], 16)
        if hex_value < 160:
            self._attr_device_info["configuration_url"] = (
                f"http://{coordinator.host}/ha_menu"
            )

        # Add icon for measurement
        measure_name = self.coordinator.data[self.entity_id]["measurement"]
        measure_value = self.coordinator.data[self.entity_id]["value"]
        self._attr_icon = self.get_icon(measure_name, float(measure_value))

    # ---- String helper for sensor names ----
    def format_string_tfa_id(self, s: str):
        """Convert string 'xxxxxxxxx' into 'TFA.me XXX-XXX-XXX'."""
        return f"TFA.me {s[:3].upper()}-{s[3:6].upper()}-{s[6:].upper()}"

    # ---- String helper for sensor/station types ----
    def format_string_tfa_type(self, s: str):
        """Convert string 'xxxxxxxxx' into 'Sensor/station type XX'."""

        # Convert first 2 characters into hex. value
        hex_value = int(s[:2], 16)
        if hex_value < 160:
            category = "Station"
        else:
            category = "Sensor"
        return f"{category} type {s[:2].upper()}"

    # ---- Property: Unique entity ID ----
    # "tfame_sensor.id_measurement" e.g. "tfame_sensor.a12345678_temperature"
    @property
    def unique_id(self) -> str:
        """Unique entity ID for Home Assistant."""
        return f"tfame_{self.entity_id}"

    # ---- Property: Name of sensor entity in HA: "ID MEASUEREMENT",  e.g. "A01234456 Temperature" ----
    @property
    def name(self) -> str:
        """Name of sensors in Home Assistant."""
        try:
            sensor_data = self.coordinator.data[self.entity_id]
            str1 = f"{sensor_data['sensor_name']} {sensor_data['measurement'].capitalize()}"
            str2 = str1.replace("Rssi", "RSSI")
            return str2.replace("_", " ")
        except (ValueError, TypeError, KeyError):
            return None

    # ---- Property: Name of measurement value in HA: "measurement", e.g. "temperature" ----
    @property
    def measurement_name(self):
        """Name of measurement."""
        try:
            measurement_name = self.coordinator.data[self.entity_id]["measurement"]
            # if measurement_name is None:
            #    return None
        except (ValueError, TypeError, KeyError):
            return None

        return measurement_name

    # ---- Property: measurement value of an entity itself ----
    @property
    def state(self):  # -> None | int | float | str | StateType:
        """Actual measurement value."""
        try:
            measurement_value = self.coordinator.data[self.entity_id]["value"]
            # if measurement_value is None:
            #    return None  # Home Assistant shows sensor as "unavailable"
        except (ValueError, TypeError, KeyError):
            return None  # Wrong data, Home Assistant shows sensor as "unavailable"

        return measurement_value

    # ---- Property: Unit of measurement value, e.g. for wind speed unit is "m/s" ----
    @property
    def unit_of_measurement(self):  # -> str | None:
        """Unit of measurement value."""
        try:
            unit = self.coordinator.data[self.entity_id]["unit"]
            if unit is None:
                return None  # Home Assistant shows "unavailable" ?
            return str(unit)
        except (ValueError, TypeError, KeyError):
            return "?"

    # ---- Property: Extra attributes dictionary for an entity ----
    # "sensor_name": Sensor ID, e.g. "A01234456"
    # "measurement": Name of measurement value, e.g. "temperature"
    # "timestamp"  : UTC timestamp, e.g. "2025-03-06T08:46:01Z"
    # "icon"       : Icon for a measurement value, e.g. "mdi:water-percent"
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Additional attributes."""

        try:
            sensor_data = self.coordinator.data[self.entity_id]
            return {
                "sensor_name": sensor_data["sensor_name"],
                "measurement": sensor_data["measurement"],
                "timestamp": sensor_data["timestamp"],
                "icon": self._attr_icon,
            }
        except (ValueError, TypeError, KeyError):
            return {}

    # ---- Property: Icon for a measurement value ----
    @property
    def icon(self) -> str:
        """Returns icon based on actual measurement value."""
        value = self.state  # actual value
        # Verify that "value" is a Float
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "mdi:help"  # Fallback-Icon for invalid values
        # get the icon
        return self.get_icon(self.measurement_name, value)

    # ---- Get an icon for measurement type based on measurement value (see MDI list) ----
    def get_icon(self, measurement_type, value):
        """Return icon for a sensor type."""

        # Temperature & temperatue probe
        if (measurement_type == "temperature") | (
            measurement_type == "temperature_probe"
        ):
            if value >= 25:
                return ICON_MAPPING["temperature"]["high"]
            if value <= 0:
                return ICON_MAPPING["temperature"]["low"]
            return ICON_MAPPING["temperature"]["default"]

        # Humidity
        if measurement_type == "humidity":
            if (value >= 65) | (value <= 30):
                return ICON_MAPPING["humidity"]["alert"]
            return ICON_MAPPING["humidity"]["default"]

        # Air quality CO2
        if measurement_type == "co2":
            return ICON_MAPPING["co2"]["default"]

        # Barometric pressure
        if measurement_type == "barometric_pressure":
            return ICON_MAPPING["barometric_pressure"]["default"]

        # RSSI value for 868 MHz reception: range 0...255
        if measurement_type == "rssi":
            if value < 100:
                return ICON_MAPPING["rssi"]["weak"]
            if value < 150:
                return ICON_MAPPING["rssi"]["middle"]
            if value < 220:
                return ICON_MAPPING["rssi"]["good"]
            return ICON_MAPPING["rssi"]["strong"]

        # Battery: 0 = low battery, 1 = good battery
        if measurement_type == "lowbatt":
            return (
                ICON_MAPPING["lowbatt"]["low"]
                if value == 1
                else ICON_MAPPING["lowbatt"]["full"]
            )

        # Wind direction, speed & gust
        if measurement_type == "wind_direction":
            return self.get_wind_direction_icon(value)
        if measurement_type == "wind_gust":
            return ICON_MAPPING["wind"]["wind"]
        if measurement_type == "wind_speed":
            return ICON_MAPPING["wind"]["gust"]

        # Rain:
        if measurement_type == "rain":
            return ICON_MAPPING["rain"]["moderate"]

        # Unknown measurement type
        return "mdi:help-circle"  # Fallback-Icon

    # ---- Get an icon for wind direction based on values (o...15) ----
    # Remark: there are only 8 arrows for direction but 16 wind direction so icon does not match optimal
    def get_wind_direction_icon(self, value):
        """Return icon for wind direction based on value 0 to 15."""
        if 0 <= value <= 1:
            return "mdi:compass-outline"  # N (North)
        if 2 <= value <= 3:
            return "mdi:arrow-top-right"  # NE (North-East)
        if 4 <= value <= 5:
            return "mdi:arrow-right"  # E (East)
        if 6 <= value <= 7:
            return "mdi:arrow-bottom-right"  # SE (South-East)
        if 8 <= value <= 9:
            return "mdi:arrow-down"  # S (South)
        if 10 <= value <= 11:
            return "mdi:arrow-bottom-left"  # SW (South-West)t
        if 12 <= value <= 13:
            return "mdi:arrow-left"  # W (West)
        if 14 <= value <= 15:
            return "mdi:arrow-top-left"  # NW (North-West)
        return "mdi:compass-outline"  # Fallback, should not happen

    # ----  ----
    async def async_update(self) -> None:
        """Manual Updating."""
        await self.coordinator.async_request_refresh()
