"""Sensor platform for Polaris PACM coffee."""
from __future__ import annotations

import copy

from homeassistant.components import mqtt
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .common import PolarisCoffeeBaseEntity
from .const import DEVICEID, DEVPREFIXTOPIC, MODEL, MQTT_ROOT_TOPIC, SENSORS, PolarisCoffeeSensorEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up sensors."""
    descriptions = copy.deepcopy(SENSORS)
    for description in descriptions:
        description.mqtt_topic_status = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_status}"

    async_add_entities(
        [
            PolarisCoffeeSensor(
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


class PolarisCoffeeSensor(PolarisCoffeeBaseEntity, SensorEntity):
    """MQTT sensor."""

    entity_description: PolarisCoffeeSensorEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeSensorEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self.entity_id = f"{SENSOR_DOMAIN}.polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Subscribe to MQTT state."""
        @callback
        def message_received(message):
            payload = str(message.payload).strip()
            try:
                value = int(payload, 16)
            except ValueError:
                return

            self._attr_native_value = max(0, min(value, 100))
            self.async_write_ha_state()

        await mqtt.async_subscribe(self.hass, self.entity_description.mqtt_topic_status, message_received, 1)
