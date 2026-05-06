"""Binary sensor platform for Polaris PACM coffee."""
from __future__ import annotations

import copy

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .common import PolarisCoffeeBaseEntity
from .const import BINARY_SENSORS, DEVICEID, DEVPREFIXTOPIC, MODEL, MQTT_ROOT_TOPIC, PolarisCoffeeBinarySensorEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up binary sensors."""
    descriptions = copy.deepcopy(BINARY_SENSORS)
    for description in descriptions:
        description.mqtt_topic_status = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_status}"

    async_add_entities(
        [
            PolarisCoffeeBinarySensor(
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


class PolarisCoffeeBinarySensor(PolarisCoffeeBaseEntity, BinarySensorEntity):
    """MQTT binary sensor."""

    entity_description: PolarisCoffeeBinarySensorEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeBinarySensorEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self.entity_id = f"{BINARY_SENSOR_DOMAIN}.polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Subscribe to MQTT state."""
        @callback
        def message_received(message):
            self._attr_is_on = str(message.payload).lower() not in ("1", "true")
            self.async_write_ha_state()

        await mqtt.async_subscribe(self.hass, self.entity_description.mqtt_topic_status, message_received, 1)
