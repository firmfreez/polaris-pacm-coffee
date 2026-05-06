"""Button platform for Polaris PACM coffee."""
from __future__ import annotations

import asyncio
import copy
import json

from homeassistant.components import mqtt
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .coffeemaker_280 import encode_recipe, filter_recipe_settings, get_store, program_data_index_for_mode
from .common import PolarisCoffeeBaseEntity
from .const import BUTTONS, DEVICEID, DEVPREFIXTOPIC, MODEL, MQTT_ROOT_TOPIC, SELECTS, PolarisCoffeeButtonEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up buttons."""
    descriptions = copy.deepcopy(BUTTONS)
    for description in descriptions:
        description.mqtt_topic_command = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_command}"

    async_add_entities(
        [
            PolarisCoffeeButton(
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


class PolarisCoffeeButton(PolarisCoffeeBaseEntity, ButtonEntity):
    """Start/stop buttons."""

    entity_description: PolarisCoffeeButtonEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeButtonEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self._entity_prefix = f"polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}"
        self.entity_id = f"{BUTTON_DOMAIN}.{self._entity_prefix}_{description.key}"
        self._attr_has_entity_name = True
        self._select_options = copy.deepcopy(SELECTS[0].options)

    def _get_state(self, entity_domain: str, entity_key: str, default=None):
        entity_id = f"{entity_domain}.{self._entity_prefix}_{entity_key}"
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return default
        return state.state

    async def _async_start(self, state_mode: str) -> None:
        coffee_mode = json.loads(self._select_options[state_mode])[0]
        mode = int(coffee_mode["mode"])
        recipe_index = program_data_index_for_mode(mode)
        store = get_store(self.hass, self.device_id)
        original_recipe = store["program_data"].get(recipe_index)

        if not original_recipe:
            mqtt.publish(self.hass, self.entity_description.mqtt_topic_command + "mode", mode)
            return

        settings = {
            "amount": self._get_state("number", "amount", 40),
            "pressure": self._get_state("number", "pressure", 1),
            "tank": self._get_state("number", "tank", 100),
            "coffee_strength": self._get_state("select", "coffee_strength", "9"),
            "preinfusion": self._get_state("select", "preinfusion", "0:00"),
            "extraction": self._get_state("select", "extraction", "standard"),
            "coffee_temperature": self._get_state("select", "coffee_temperature", "medium"),
        }
        recipe = encode_recipe(original_recipe, filter_recipe_settings(settings, coffee_mode), store.get("current_user", 0))

        mqtt.publish(self.hass, f"{self.mqtt_root}/{self.device_prefix_topic}/control/program_data/{recipe_index}", recipe)
        mqtt.publish(self.hass, self.entity_description.mqtt_topic_command + "mode", mode)
        await asyncio.sleep(0.5)
        mqtt.publish(self.hass, f"{self.mqtt_root}/{self.device_prefix_topic}/control/program_data/{recipe_index}", original_recipe)

    async def async_press(self) -> None:
        """Press button."""
        if self.entity_description.key == "button_stop":
            mqtt.publish(self.hass, self.entity_description.mqtt_topic_command + "mode", "0")
            return

        state_mode = self._get_state("select", "select_mode_cofeemaker")
        if state_mode:
            await self._async_start(state_mode)
