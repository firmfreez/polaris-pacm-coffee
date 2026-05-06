"""Constants for Polaris PACM coffee MQTT."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription
from homeassistant.const import Platform, UnitOfTime, UnitOfVolume
from homeassistant.helpers.entity import EntityCategory

DOMAIN = "polaris_coffee"
MANUFACTURER = "Polaris IQ Home"
MODEL = "PACM-2081AC"
DEVICE_TYPE = "280"

MQTT_ROOT_TOPIC = "MQTT_ROOT_TOPIC"
MQTT_ROOT_TOPIC_DEFAULT = "polaris"
DEVICEID = "DEVICEID"
DEVICETYPE = "DEVICETYPE"
DEVPREFIXTOPIC = "DEVPREFIXTOPIC"

PLATFORMS = [
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.BINARY_SENSOR,
]


@dataclass
class PolarisCoffeeSelectEntityDescription(SelectEntityDescription):
    """Select description with MQTT topics."""

    options: dict[str, str] | None = None
    mqtt_topic_current: str | None = None
    mqtt_topic_command: str | None = None


@dataclass
class PolarisCoffeeNumberEntityDescription(NumberEntityDescription):
    """Number description with MQTT topics."""

    native_value: int | None = None
    available: bool = True


@dataclass
class PolarisCoffeeSwitchEntityDescription(SwitchEntityDescription):
    """Switch description with MQTT topics."""

    mqtt_topic_current: str | None = None
    mqtt_topic_command: str | None = None
    payload_on: str | None = None
    payload_off: str | None = None


@dataclass
class PolarisCoffeeButtonEntityDescription(ButtonEntityDescription):
    """Button description with MQTT command prefix."""

    mqtt_topic_command: str | None = None


@dataclass
class PolarisCoffeeBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Binary sensor description with MQTT topic."""

    mqtt_topic_status: str | None = None


COFFEEMAKER_280_MODES = {
    "hot_espresso": "[{\"mode\": 1, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "hot_ristretto": "[{\"mode\": 2, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "hot_lungo": "[{\"mode\": 3, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "hot_americano": "[{\"mode\": 4, \"coffee\": true, \"milk\": false, \"water\": true}]",
    "hot_cappuccino": "[{\"mode\": 5, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_latte": "[{\"mode\": 6, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_flat_white": "[{\"mode\": 7, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_milk_foam": "[{\"mode\": 8, \"coffee\": false, \"milk\": true, \"water\": false}]",
    "hot_macchiato": "[{\"mode\": 9, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_latte_macchiato": "[{\"mode\": 10, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_milk_coffee": "[{\"mode\": 11, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_double_espresso": "[{\"mode\": 12, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "hot_double_cappuccino": "[{\"mode\": 13, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_double_latte": "[{\"mode\": 14, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_double_lungo": "[{\"mode\": 15, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "hot_double_macchiato": "[{\"mode\": 16, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_green_tea": "[{\"mode\": 17, \"coffee\": false, \"milk\": false, \"water\": true}]",
    "hot_black_tea": "[{\"mode\": 18, \"coffee\": false, \"milk\": false, \"water\": true}]",
    "hot_cortado": "[{\"mode\": 19, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "hot_cocoa": "[{\"mode\": 20, \"coffee\": false, \"milk\": true, \"water\": false}]",
    "hot_water": "[{\"mode\": 21, \"coffee\": false, \"milk\": false, \"water\": true}]",
    "cold_coffee": "[{\"mode\": 22, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "cold_double_espresso": "[{\"mode\": 23, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "cold_cappuccino": "[{\"mode\": 24, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_latte": "[{\"mode\": 25, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_flat_white": "[{\"mode\": 26, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_cortado": "[{\"mode\": 27, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_macchiato": "[{\"mode\": 28, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_latte_macchiato": "[{\"mode\": 29, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_milk_coffee": "[{\"mode\": 30, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_double_cappuccino": "[{\"mode\": 31, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_double_latte": "[{\"mode\": 32, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "cold_double_lungo": "[{\"mode\": 33, \"coffee\": true, \"milk\": false, \"water\": false}]",
    "cold_double_macchiato": "[{\"mode\": 34, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_americano": "[{\"mode\": 35, \"coffee\": true, \"milk\": false, \"water\": true}]",
    "takeaway_cappuccino": "[{\"mode\": 36, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_latte": "[{\"mode\": 37, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_flat_white": "[{\"mode\": 38, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_macchiato": "[{\"mode\": 39, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_latte_macchiato": "[{\"mode\": 40, \"coffee\": true, \"milk\": true, \"water\": false}]",
    "takeaway_milk_coffee": "[{\"mode\": 41, \"coffee\": true, \"milk\": true, \"water\": false}]",
}

NUMBERS = [
    PolarisCoffeeNumberEntityDescription(
        key="amount",
        translation_key="coffee_volume",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        native_min_value=10,
        native_max_value=240,
        native_step=5,
        native_value=40,
        mode="slider",
        available=False,
    ),
    PolarisCoffeeNumberEntityDescription(
        key="pressure",
        translation_key="milk_foam",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=1,
        native_max_value=70,
        native_step=1,
        native_value=30,
        mode="slider",
        available=False,
    ),
    PolarisCoffeeNumberEntityDescription(
        key="tank",
        translation_key="hot_water",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.WATER,
        native_unit_of_measurement=UnitOfVolume.MILLILITERS,
        native_min_value=5,
        native_max_value=300,
        native_step=5,
        native_value=100,
        mode="slider",
        available=False,
    ),
]


SELECTS = [
    PolarisCoffeeSelectEntityDescription(
        key="select_mode_cofeemaker",
        translation_key="select_mode_cofeemaker_280",
        mqtt_topic_current="state/mode",
        mqtt_topic_command="control/mode",
        options=COFFEEMAKER_280_MODES,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:receipt-text",
    ),
    PolarisCoffeeSelectEntityDescription(
        key="coffee_strength",
        translation_key="coffee_strength",
        options={"6": "6", "8": "8", "9": "9", "10": "10", "11": "11"},
        entity_category=EntityCategory.CONFIG,
        icon="mdi:coffee",
    ),
    PolarisCoffeeSelectEntityDescription(
        key="preinfusion",
        translation_key="preinfusion",
        options={"0:00": "0", "0:01": "1", "0:02": "2", "0:03": "3", "0:04": "4", "0:05": "5"},
        entity_category=EntityCategory.CONFIG,
        icon="mdi:timer-sand",
    ),
    PolarisCoffeeSelectEntityDescription(
        key="extraction",
        translation_key="extraction",
        options={"standard": "0", "strong": "1", "extra_strong": "2"},
        entity_category=EntityCategory.CONFIG,
        icon="mdi:coffee-maker",
    ),
    PolarisCoffeeSelectEntityDescription(
        key="coffee_temperature",
        translation_key="coffee_temperature",
        options={"low": "0", "medium": "1", "high": "2"},
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer",
    ),
    PolarisCoffeeSelectEntityDescription(
        key="current_user",
        translation_key="current_user",
        mqtt_topic_current="state/current_user",
        mqtt_topic_command="control/current_user",
        options={"1": "0", "2": "1", "3": "2", "4": "3", "5": "4", "6": "5"},
        entity_category=EntityCategory.CONFIG,
        icon="mdi:account",
    ),
]

SWITCHES = [
    PolarisCoffeeSwitchEntityDescription(
        key="power",
        translation_key="power_switch",
        entity_category=EntityCategory.CONFIG,
        mqtt_topic_current="state/mode",
        mqtt_topic_command="control/mode",
        payload_on="1",
        payload_off="0",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:power-standby",
    ),
    PolarisCoffeeSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock_switch",
        entity_category=EntityCategory.CONFIG,
        mqtt_topic_current="state/child_lock",
        mqtt_topic_command="control/child_lock",
        payload_on="true",
        payload_off="false",
        device_class=SwitchDeviceClass.SWITCH,
    ),
]

BUTTONS = [
    PolarisCoffeeButtonEntityDescription(
        key="button_stop",
        translation_key="button_stop_coffee",
        mqtt_topic_command="control/",
        entity_category=EntityCategory.CONFIG,
    ),
    PolarisCoffeeButtonEntityDescription(
        key="button_start",
        translation_key="button_start_coffee",
        mqtt_topic_command="control/",
        entity_category=EntityCategory.CONFIG,
    ),
]

BINARY_SENSORS = [
    PolarisCoffeeBinarySensorEntityDescription(
        key="available",
        translation_key="available_binary_sensor",
        mqtt_topic_status="state/error/connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
]
