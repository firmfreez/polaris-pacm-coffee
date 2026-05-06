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
    DEFAULT_SELECTED_MODE,
    EVENT_SELECTED_MODE_CHANGED,
    decode_recipe,
    filter_recipe_settings,
    get_store,
    program_data_index_for_mode,
    recipe_setting_keys,
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
        def option_from_mode(mode: int | None = None) -> str:
            selected_mode = mode if mode is not None else get_store(self.hass, self.device_id).get("selected_mode", DEFAULT_SELECTED_MODE)
            return next(
                (key for key, value in SELECTS[0].options.items() if json.loads(value)[0]["mode"] == selected_mode),
                next(key for key, value in SELECTS[0].options.items() if json.loads(value)[0]["mode"] == DEFAULT_SELECTED_MODE),
            )

        def update_availability_from_option(drink_mode_key: str):
            """Update availability from the selected recipe, not live state/mode."""
            select_options = SELECTS[0].options
            if drink_mode_key not in select_options:
                drink_mode_key = option_from_mode()

            try:
                coffee_mode = json.loads(select_options[drink_mode_key])[0]
            except (json.JSONDecodeError, IndexError, KeyError):
                self._attr_available = False
                return

            mode_value = int(coffee_mode["mode"])
            self._current_mode_value = mode_value
            get_store(self.hass, self.device_id)["selected_mode"] = mode_value
            available_keys = recipe_setting_keys(coffee_mode)
            self._attr_available = self.entity_description.key in available_keys

            # Update value from recipe if available
            if self._attr_available and self.entity_description.key in ("amount", "pressure", "tank"):
                store = get_store(self.hass, self.device_id)
                recipe = store["program_data"].get(program_data_index_for_mode(mode_value))
                if recipe:
                    settings = decode_recipe(recipe, store.get("current_user", 0))
                    filtered_settings = filter_recipe_settings(settings, coffee_mode)
                    if self.entity_description.key in filtered_settings:
                        self._attr_native_value = int(filtered_settings[self.entity_description.key])

        @callback
        def on_selected_mode_changed(event):
            """Handle selected drink mode changes."""
            if event.data.get("device_id") != self.device_id:
                return

            update_availability_from_option(option_from_mode(event.data.get("mode")))
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_SELECTED_MODE_CHANGED,
                on_selected_mode_changed,
            )
        )

        # Subscribe to MQTT mode and current_user topics directly so numbers update reliably.
        self._current_mode_value: int | None = None

        if SELECTS[0].mqtt_topic_current:
            mode_topic = f"{self.mqtt_root}/{self.device_prefix_topic}/{SELECTS[0].mqtt_topic_current}"

            @callback
            def mode_message_received(message):
                payload = str(message.payload)
                try:
                    mode_value = int(payload)
                except ValueError:
                    return

                if mode_value == 0:
                    return

                option = next(
                    (key for key, value in SELECTS[0].options.items() if json.loads(value)[0]["mode"] == mode_value),
                    None,
                )
                if option is None:
                    return
                update_availability_from_option(option)
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

                if self._current_mode_value is None or self.entity_description.key not in ("amount", "pressure", "tank"):
                    return

                store = get_store(self.hass, self.device_id)
                recipe = store["program_data"].get(program_data_index_for_mode(self._current_mode_value))
                if recipe:
                    select_options = SELECTS[0].options
                    option = next((key for key, value in select_options.items() if json.loads(value)[0]["mode"] == self._current_mode_value), None)
                    if option is not None:
                        try:
                            coffee_mode = json.loads(select_options[option])[0]
                            settings = decode_recipe(recipe, user_index)
                            filtered_settings = filter_recipe_settings(settings, coffee_mode)
                            if self.entity_description.key in filtered_settings:
                                self._attr_native_value = int(filtered_settings[self.entity_description.key])
                                self.async_write_ha_state()
                        except (json.JSONDecodeError, IndexError, KeyError):
                            pass

            await mqtt.async_subscribe(self.hass, user_topic, user_message_received, 1)

        # Initialize availability from the selected recipe if available.
        mode_entity_id = f"select.{self._entity_prefix}_select_mode_cofeemaker"
        current_state = self.hass.states.get(mode_entity_id)
        if current_state is not None and current_state.state not in ("unknown", "unavailable"):
            drink_mode_key = current_state.state
            select_options = SELECTS[0].options
            if drink_mode_key in select_options:
                try:
                    mode_value = json.loads(select_options[drink_mode_key])[0].get("mode")
                    if mode_value is not None:
                        update_availability_from_option(drink_mode_key)
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass
            else:
                update_availability_from_option(option_from_mode())
        else:
            update_availability_from_option(option_from_mode())
        self.async_write_ha_state()
