"""Number platform for Polaris PACM coffee."""
from __future__ import annotations

import copy

from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .common import PolarisCoffeeBaseEntity
from .const import DEVICEID, DEVPREFIXTOPIC, MQTT_ROOT_TOPIC, NUMBERS, MODEL, PolarisCoffeeNumberEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up number entities."""
    descriptions = copy.deepcopy(NUMBERS)
    async_add_entities(
        [
            PolarisCoffeeNumber(
                description=description,
                device_friendly_name=config.data[DEVICEID],
                mqtt_root=config.data[MQTT_ROOT_TOPIC],
                device_id=config.data[DEVICEID],
                device_prefix_topic=config.data[DEVPREFIXTOPIC],
            )
            for description in descriptions
        ],
        update_before_add=True,
    )


class PolarisCoffeeNumber(PolarisCoffeeBaseEntity, NumberEntity):
    """Config-only number entity."""

    entity_description: PolarisCoffeeNumberEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeNumberEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self.entity_id = f"{NUMBER_DOMAIN}.polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_native_value = description.native_value

    def set_native_value(self, value: float) -> None:
        """Update local config value."""
        self._attr_native_value = int(value)
        self.async_write_ha_state()
