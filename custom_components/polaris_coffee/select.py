"""Select platform for Polaris PACM coffee."""
from __future__ import annotations

import copy
import json

from homeassistant.components import mqtt
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN, SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .coffeemaker_280 import (
    PROGRAM_DATA_FIRST_RECIPE_INDEX,
    PROGRAM_DATA_RECIPE_COUNT,
    decode_recipe,
    filter_recipe_settings,
    get_store,
    program_data_index_for_mode,
)
from .common import PolarisCoffeeBaseEntity
from .const import DEVICEID, DEVPREFIXTOPIC, MODEL, MQTT_ROOT_TOPIC, SELECTS, PolarisCoffeeSelectEntityDescription


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up selects."""
    descriptions = copy.deepcopy(SELECTS)
    for description in descriptions:
        if description.mqtt_topic_current:
            description.mqtt_topic_current = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_current}"
        if description.mqtt_topic_command:
            description.mqtt_topic_command = f"{config.data[MQTT_ROOT_TOPIC]}/{config.data[DEVPREFIXTOPIC]}/{description.mqtt_topic_command}"

    async_add_entities(
        [
            PolarisCoffeeSelect(
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


class PolarisCoffeeSelect(PolarisCoffeeBaseEntity, SelectEntity):
    """MQTT/config select."""

    entity_description: PolarisCoffeeSelectEntityDescription

    def __init__(self, device_friendly_name: str, description: PolarisCoffeeSelectEntityDescription, mqtt_root: str, device_id: str, device_prefix_topic: str) -> None:
        super().__init__(device_friendly_name, mqtt_root, device_id, device_prefix_topic)
        self.entity_description = description
        self._attr_unique_id = slugify(f"{device_id}_{description.key}")
        self._entity_prefix = f"polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}"
        self.entity_id = f"{SELECT_DOMAIN}.{self._entity_prefix}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_options = list(description.options.keys())
        self._attr_current_option = self._attr_options[0]

    def key_from_mode(self, mode: int):
        """Return drink key by numeric mode."""
        try:
            return next(key for key, value in self.entity_description.options.items() if json.loads(value)[0]["mode"] == mode)
        except StopIteration:
            return None

    async def _async_apply_recipe(self, recipe: str, features: dict | None = None) -> None:
        """Apply selected drink recipe to visible controls."""
        store = get_store(self.hass, self.device_id)
        settings = filter_recipe_settings(decode_recipe(recipe, store.get("current_user", 1)), features)
        base_entity = self._entity_prefix

        for key in ("amount", "pressure", "tank"):
            if key not in settings:
                continue
            entity_id = f"number.{base_entity}_{key}"
            if self.hass.states.get(entity_id) is not None:
                await self.hass.services.async_call("number", "set_value", {"entity_id": entity_id, "value": settings[key]})

        for key in ("coffee_temperature", "preinfusion", "extraction", "coffee_strength"):
            if key not in settings:
                continue
            entity_id = f"select.{base_entity}_{key}"
            if self.hass.states.get(entity_id) is not None:
                await self.hass.services.async_call("select", "select_option", {"entity_id": entity_id, "option": settings[key]})

    async def _async_apply_current_drink(self) -> None:
        """Refresh controls for current drink/user."""
        if self.entity_description.key != "select_mode_cofeemaker":
            return
        store = get_store(self.hass, self.device_id)
        coffee_mode = json.loads(self.entity_description.options[self._attr_current_option])[0]
        recipe = store["program_data"].get(program_data_index_for_mode(coffee_mode["mode"]))
        if recipe:
            await self._async_apply_recipe(recipe, coffee_mode)

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        self._attr_current_option = option
        self.async_write_ha_state()
        if self.entity_description.key == "current_user":
            store = get_store(self.hass, self.device_id)
            store["current_user"] = int(self.entity_description.options[option])
            if self.entity_description.mqtt_topic_command:
                mqtt.publish(self.hass, self.entity_description.mqtt_topic_command, self.entity_description.options[option])
            state = self.hass.states.get(f"select.{self._entity_prefix}_select_mode_cofeemaker")
            if state is not None:
                command_mode = SELECTS[0].options.get(state.state)
                if command_mode is not None:
                    coffee_mode = json.loads(command_mode)[0]
                    recipe = store["program_data"].get(program_data_index_for_mode(coffee_mode["mode"]))
                    if recipe:
                        await self._async_apply_recipe(recipe, coffee_mode)
            return
        if self.entity_description.key == "select_mode_cofeemaker":
            await self._async_apply_current_drink()

    async def async_added_to_hass(self):
        """Subscribe to MQTT state."""
        if self.entity_description.mqtt_topic_current:
            @callback
            def message_received(message):
                payload = message.payload
                if self.entity_description.key == "select_mode_cofeemaker":
                    if payload == "0":
                        return
                    option = self.key_from_mode(int(payload))
                    if option:
                        self._attr_current_option = option
                        self.async_write_ha_state()
                elif self.entity_description.key == "current_user":
                    for key, value in self.entity_description.options.items():
                        if str(value) == str(payload):
                            get_store(self.hass, self.device_id)["current_user"] = int(value)
                            self._attr_current_option = key
                            self.async_write_ha_state()
                            break

            await mqtt.async_subscribe(self.hass, self.entity_description.mqtt_topic_current, message_received, 1)

        if self.entity_description.key == "select_mode_cofeemaker":
            store = get_store(self.hass, self.device_id)

            async def apply_current_recipe(recipe_index: int) -> None:
                coffee_mode = json.loads(self.entity_description.options[self._attr_current_option])[0]
                if recipe_index == program_data_index_for_mode(coffee_mode["mode"]):
                    recipe = store["program_data"].get(recipe_index)
                    if recipe:
                        await self._async_apply_recipe(recipe, coffee_mode)

            for recipe_index in range(PROGRAM_DATA_FIRST_RECIPE_INDEX, PROGRAM_DATA_FIRST_RECIPE_INDEX + PROGRAM_DATA_RECIPE_COUNT):
                @callback
                def program_data_received(message, recipe_index=recipe_index):
                    store["program_data"][recipe_index] = message.payload
                    self.hass.async_create_task(apply_current_recipe(recipe_index))

                await mqtt.async_subscribe(self.hass, f"{self.mqtt_root}/{self.device_prefix_topic}/state/program_data/{recipe_index}", program_data_received, 1)
