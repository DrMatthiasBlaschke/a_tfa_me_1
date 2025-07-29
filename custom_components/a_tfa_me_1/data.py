"""TFA.me station integration: data.py."""

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry

type TFAmeConfigEntry = ConfigEntry[TFAmeData]


@dataclass
class TFAmeData:
    """Store runtime data."""

    def __init__(self, host: str) -> None:
        """Initialize client with host."""
        self.host = host

    async def get_identifier(self) -> str:
        """Request a unique ID from a device."""
        # We just take the host name
        #    url = f"{self.base_url}/identifier"
        #    async with aiohttp.ClientSession() as session:
        #        async with session.get(url, timeout=10) as response:
        #            if response.status != 200:
        #                raise TFAmeException("Error requesting ID")
        #           data = await response.json()
        #            return data.get("id")
        return self.host


class TFAmeException(Exception):
    """User defined exception for error in client."""
