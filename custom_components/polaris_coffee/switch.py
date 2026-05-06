"""Switch platform for Polaris PACM coffee."""
from __future__ import annotations

import copy

from homeassistant.components import mqtt
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .common import PolarisCoffeeBaseEntity
from .const import DEVICEID, DEVPREFIXTOPIC, MQTT_ROOT_TOPIC, MODEL, SWITCHES, PolarisCoffeeSwitchEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up switches."""
    descriptions = copy.deepcopy(SWITCHES)
    for description in descriptions:
        description.mqtt_topic_current = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_current}"
        description.mqtt_topic_command = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_command}"

    async_add_entities(
        [
            PolarisCoffeeSwitch(
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


class PolarisCoffeeSwitch(PolarisCoffeeBaseEntity, SwitchEntity):
    """MQTT switch."""

    entity_description: PolarisCoffeeSwitchEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeSwitchEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self.entity_id = f"{SWITCH_DOMAIN}.polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_is_on = False

    async def async_added_to_hass(self):
        """Subscribe to current state."""
        @callback
        def message_received(message):
            payload = str(message.payload).lower()
            if self.entity_description.key == "power":
                # Machine is on whenever the mode is not 0
                self._attr_is_on = payload != "0"
            else:
                self._attr_is_on = payload == str(self.entity_description.payload_on).lower()
            self.async_write_ha_state()

        await mqtt.async_subscribe(self.hass, self.entity_description.mqtt_topic_current, message_received, 1)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on."""
        self._attr_is_on = True
        mqtt.publish(self.hass, self.entity_description.mqtt_topic_command, self.entity_description.payload_on)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off."""
        self._attr_is_on = False
        mqtt.publish(self.hass, self.entity_description.mqtt_topic_command, self.entity_description.payload_off)
