"""Config flow for Polaris PACM coffee MQTT."""
from __future__ import annotations

import asyncio
import logging

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode
from homeassistant.helpers.service_info.mqtt import MqttServiceInfo

from .const import (
    DEVICE_TYPE,
    DEVICEID,
    DEVPREFIXTOPIC,
    DEVICETYPE,
    DOMAIN,
    MODEL,
    MQTT_ROOT_TOPIC,
    MQTT_ROOT_TOPIC_DEFAULT,
)

_LOGGER = logging.getLogger(__name__)


class PolarisCoffeeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Polaris PACM coffee."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_found: dict[str, dict[str, str]] = {}
        self._device_type = "0"

    async def _discover_devices(self) -> None:
        await mqtt.async_subscribe(self.hass, "polaris/+/state/mac", self._mqtt_message_newdev)
        await mqtt.async_subscribe(self.hass, "polaris/+/+/state/mac", self._mqtt_message_olddev)
        await asyncio.sleep(2)

    @callback
    async def _mqtt_message_newdev(self, message):
        device_id = message.topic.split("/")[1]
        devtype = await self._read_devtype(f"polaris/{device_id}/state/devtype")
        if devtype != DEVICE_TYPE:
            return
        self._device_found[message.payload] = {
            DEVICEID: message.payload,
            DEVICETYPE: devtype,
            MQTT_ROOT_TOPIC: MQTT_ROOT_TOPIC_DEFAULT,
            DEVPREFIXTOPIC: device_id,
        }

    @callback
    async def _mqtt_message_olddev(self, message):
        topic_parts = message.topic.split("/")
        devtype = topic_parts[1]
        if devtype != DEVICE_TYPE:
            return
        self._device_found[message.payload] = {
            DEVICEID: message.payload,
            DEVICETYPE: devtype,
            MQTT_ROOT_TOPIC: MQTT_ROOT_TOPIC_DEFAULT,
            DEVPREFIXTOPIC: f"{topic_parts[1]}/{topic_parts[2]}",
        }

    async def _read_devtype(self, topic: str, timeout: float = 1.0) -> str:
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def message_received(msg):
            if not future.done():
                future.set_result(msg.payload)

        unsub = await mqtt.async_subscribe(self.hass, topic, message_received, qos=0)
        try:
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            return "0"
        finally:
            unsub()

    async def async_step_user(self, user_input=None):
        """Pick a discovered device or open manual setup."""
        await self._discover_devices()
        configured_devices = {
            entry.data[DEVICEID]
            for entry in self._async_current_entries()
            if DEVICEID in entry.data
        }
        devices = {
            device_id: data
            for device_id, data in self._device_found.items()
            if device_id not in configured_devices
        }

        if user_input is not None:
            if user_input.get("manual"):
                return await self.async_step_manual()
            data = devices[user_input[DEVICEID]]
            return await self._create_entry(data)

        if not devices:
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(DEVICEID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=device_id, label=f"{MODEL} (mac: {device_id})")
                                for device_id in devices
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Optional("manual", default=False): bool,
                }
            ),
        )

    async def async_step_manual(self, user_input=None):
        """Set up the device manually."""
        if user_input is not None:
            data = {
                DEVICEID: user_input[DEVICEID],
                DEVICETYPE: DEVICE_TYPE,
                MQTT_ROOT_TOPIC: user_input[MQTT_ROOT_TOPIC],
                DEVPREFIXTOPIC: user_input[DEVPREFIXTOPIC],
            }
            return await self._create_entry(data)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(DEVICEID): str,
                    vol.Required(MQTT_ROOT_TOPIC, default=MQTT_ROOT_TOPIC_DEFAULT): str,
                    vol.Required(DEVPREFIXTOPIC): str,
                }
            ),
        )

    async def async_step_mqtt(self, discovery_info: MqttServiceInfo):
        """Handle MQTT discovery."""
        topic_parts = discovery_info.topic.strip("/").split("/")
        if len(topic_parts) == 4:
            device_prefix_topic = topic_parts[1]
            devtype = await self._read_devtype(f"polaris/{device_prefix_topic}/state/devtype")
        elif len(topic_parts) == 5 and topic_parts[0] == "polaris":
            devtype = topic_parts[1]
            device_prefix_topic = f"{topic_parts[1]}/{topic_parts[2]}"
        else:
            return self.async_abort(reason="unknown_topic")

        if devtype != DEVICE_TYPE:
            return self.async_abort(reason="unsupported_device")

        return await self.async_step_confirm(
            {
                DEVICEID: discovery_info.payload,
                DEVICETYPE: devtype,
                MQTT_ROOT_TOPIC: MQTT_ROOT_TOPIC_DEFAULT,
                DEVPREFIXTOPIC: device_prefix_topic,
            }
        )

    async def async_step_confirm(self, user_input=None):
        """Create entry from discovery."""
        if user_input is None:
            return self.async_show_form(step_id="confirm")
        return await self._create_entry(user_input)

    async def _create_entry(self, data: dict):
        title = f"{MODEL}-{data[DEVICEID]}"
        await self.async_set_unique_id(title)
        self._abort_if_unique_id_configured(error="already_configured")
        return self.async_create_entry(title=title, data=data)
