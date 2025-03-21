"""TFA.me station integration: button.py."""

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the button entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReloadSensorsButton(coordinator, entry)])


class ReloadSensorsButton(CoordinatorEntity, ButtonEntity):
    """Button entity to trigger sensor reload."""

    def __init__(self, coordinator, entry):
        """Initialize the button."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = "Reload Sensors"
        self._attr_unique_id = f"{entry.entry_id}_reload"
        self._attr_icon = "mdi:refresh"  # MDI-Icon für den Button

    async def async_press(self):
        """Handle the button press."""
        await self.coordinator.async_request_refresh()
