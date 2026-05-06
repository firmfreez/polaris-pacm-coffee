"""Common entities for Polaris coffee."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL


class PolarisCoffeeBaseEntity:
    """Base entity for Polaris PACM coffee machine."""

    def __init__(
        self,
        device_friendly_name: str,
        mqtt_root: str,
        device_id: str,
        device_prefix_topic: str,
    ) -> None:
        self.device_friendly_name = device_friendly_name
        self.mqtt_root = mqtt_root
        self.device_id = device_id
        self.device_prefix_topic = device_prefix_topic

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            name=f"Polaris {MODEL}",
            identifiers={(DOMAIN, self.device_id, self.mqtt_root)},
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
