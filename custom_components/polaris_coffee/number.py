"""Number platform for Polaris PACM coffee."""
from __future__ import annotations

import copy
import json

from homeassistant.components import mqtt
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN, NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .coffeemaker_280 import (
    decode_recipe,
    filter_recipe_settings,
    get_store,
    program_data_index_for_mode,
)
from .common import PolarisCoffeeBaseEntity
from .const import DEVICEID, DEVPREFIXTOPIC, MQTT_ROOT_TOPIC, NUMBERS, MODEL, SELECTS, PolarisCoffeeNumberEntityDescription


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
        self._attr_available = description.available
        self._entity_prefix = f"polaris_{MODEL.lower().replace('-', '_')}_{slugify(device_id)}"

    async def async_set_native_value(self, value: float) -> None:
        """Update local config value."""
        self._attr_native_value = int(value)
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Subscribe to drink mode changes to update availability and values from program_data."""
        @callback
        def on_mode_changed(event):
            """Handle drink mode changes."""
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state in ("unknown", "unavailable"):
                return

            # Get the current drink mode
            drink_mode_key = new_state.state
            select_options = SELECTS[0].options
            if drink_mode_key not in select_options:
                return

            # Parse the drink mode to get features
            try:
                coffee_mode = json.loads(select_options[drink_mode_key])[0]
                self._current_mode_value = coffee_mode.get("mode")
            except (json.JSONDecodeError, IndexError, KeyError):
                self._current_mode_value = None
                return

            # Determine if this field is available for the current drink
            features = coffee_mode
            available_keys = set()
            if features.get("coffee"):
                available_keys.update({"amount", "coffee_strength", "preinfusion", "extraction"})
            if features.get("milk"):
                available_keys.add("pressure")
            if features.get("water"):
                available_keys.add("tank")
            available_keys.add("coffee_temperature")

            # Update availability
            self._attr_available = self.entity_description.key in available_keys
            
            # Update value from the recipe if available
            if self._attr_available and self.entity_description.key in ("amount", "pressure", "tank"):
                store = get_store(self.hass, self.device_id)
                recipe = store["program_data"].get(program_data_index_for_mode(int(coffee_mode["mode"])))
                if recipe:
                    settings = decode_recipe(recipe, store.get("current_user", 0))
                    filtered_settings = filter_recipe_settings(settings, coffee_mode)
                    if self.entity_description.key in filtered_settings:
                        self._attr_native_value = int(filtered_settings[self.entity_description.key])

            self.async_write_ha_state()

        # Subscribe to mode changes
        mode_entity_id = f"select.{self._entity_prefix}_select_mode_cofeemaker"
        self.async_on_remove(
            self.hass.helpers.event.async_track_state_change_event(
                [mode_entity_id],
                on_mode_changed,
            )
        )

        # Subscribe to MQTT mode and current_user topics directly so numbers update reliably.
        self._current_mode_value: int | None = None

        if SELECTS[0].mqtt_topic_current:
            mode_topic = f"{self.mqtt_root}/{self.device_prefix_topic}/{SELECTS[0].mqtt_topic_current}"

            @callback
            def mode_message_received(message):
                payload = str(message.payload)
                if payload == "0":
                    self._attr_available = False
                    self._current_mode_value = None
                    self.async_write_ha_state()
                    return

                try:
                    mode_value = int(payload)
                except ValueError:
                    return

                self._current_mode_value = mode_value
                select_options = SELECTS[0].options
                option = next((key for key, value in select_options.items() if json.loads(value)[0]["mode"] == mode_value), None)
                if option is None:
                    return

                coffee_mode = json.loads(select_options[option])[0]
                available_keys = set()
                if coffee_mode.get("coffee"):
                    available_keys.update({"amount", "coffee_strength", "preinfusion", "extraction"})
                if coffee_mode.get("milk"):
                    available_keys.add("pressure")
                if coffee_mode.get("water"):
                    available_keys.add("tank")

                self._attr_available = self.entity_description.key in available_keys
                if self._attr_available and self.entity_description.key in ("amount", "pressure", "tank"):
                    store = get_store(self.hass, self.device_id)
                    recipe = store["program_data"].get(program_data_index_for_mode(mode_value))
                    if recipe:
                        settings = decode_recipe(recipe, store.get("current_user", 0))
                        filtered_settings = filter_recipe_settings(settings, coffee_mode)
                        if self.entity_description.key in filtered_settings:
                            self._attr_native_value = int(filtered_settings[self.entity_description.key])
                self.async_write_ha_state()

            await mqtt.async_subscribe(self.hass, mode_topic, mode_message_received, 1)

        if SELECTS[5].mqtt_topic_current:
            user_topic = f"{self.mqtt_root}/{self.device_prefix_topic}/{SELECTS[5].mqtt_topic_current}"

            @callback
            def user_message_received(message):
                payload = str(message.payload)
                try:
                    user_index = int(payload)
                except ValueError:
                    return

                if self._current_mode_value is None:
                    return

                if self._attr_available and self.entity_description.key in ("amount", "pressure", "tank"):
                    store = get_store(self.hass, self.device_id)
                    recipe = store["program_data"].get(program_data_index_for_mode(self._current_mode_value))
                    if recipe:
                        select_options = SELECTS[0].options
                        option = next((key for key, value in select_options.items() if json.loads(value)[0]["mode"] == self._current_mode_value), None)
                        if option is None:
                            return
                        coffee_mode = json.loads(select_options[option])[0]
                        settings = decode_recipe(recipe, user_index)
                        filtered_settings = filter_recipe_settings(settings, coffee_mode)
                        if self.entity_description.key in filtered_settings:
                            self._attr_native_value = int(filtered_settings[self.entity_description.key])
                        self.async_write_ha_state()

            await mqtt.async_subscribe(self.hass, user_topic, user_message_received, 1)

        current_state = self.hass.states.get(mode_entity_id)
        if current_state is not None:
            class _Event:
                pass
            event = _Event()
            event.data = {"new_state": current_state}
            on_mode_changed(event)

