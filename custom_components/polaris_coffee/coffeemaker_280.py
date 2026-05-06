"""Helpers for Polaris PACM-2081AC revision 280 recipes."""
from __future__ import annotations

DOMAIN = "polaris_coffee"

PROGRAM_DATA_FIRST_RECIPE_INDEX = 7
PROGRAM_DATA_RECIPE_COUNT = 41

OFFSET_TEMPERATURE = 1
OFFSET_PREINFUSION = 13
OFFSET_COFFEE_VOLUME = 37
OFFSET_MILK_FOAM = 49
OFFSET_EXTRACTION = 55
OFFSET_HOT_WATER = 61
OFFSET_COFFEE_STRENGTH = 67

MAX_USER_INDEX = 5

TEMPERATURE_TO_BYTE = {
    "low": 1,
    "medium": 2,
    "high": 3,
}
BYTE_TO_TEMPERATURE = {value: key for key, value in TEMPERATURE_TO_BYTE.items()}

EXTRACTION_TO_BYTE = {
    "standard": 0,
    "strong": 1,
    "extra_strong": 2,
}
BYTE_TO_EXTRACTION = {value: key for key, value in EXTRACTION_TO_BYTE.items()}


def recipe_setting_keys(features: dict | None = None) -> set[str]:
    """Return setting keys that apply to a drink feature set."""
    features = features or {}
    keys = {"coffee_temperature"}
    if features.get("coffee"):
        keys.update({"amount", "coffee_strength", "preinfusion", "extraction"})
    if features.get("milk"):
        keys.add("pressure")
    if features.get("water"):
        keys.add("tank")
    return keys


def filter_recipe_settings(settings: dict, features: dict | None = None) -> dict:
    """Keep only recipe settings available for a drink."""
    allowed_keys = recipe_setting_keys(features)
    return {key: value for key, value in settings.items() if key in allowed_keys}


def get_store(hass, device_id: str) -> dict:
    """Return shared in-memory state for the rev. 280 coffeemaker."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    coffee_data = domain_data.setdefault("coffeemaker_280", {})
    return coffee_data.setdefault(device_id, {"program_data": {}, "current_user": 0})


def program_data_index_for_mode(mode: int) -> int:
    """Map drink mode 1..41 to program_data topic index 7..47."""
    return PROGRAM_DATA_FIRST_RECIPE_INDEX + mode - 1


def normalize_user(user: int | str | None) -> int:
    """Clamp user index to the recipe slots supported by the device."""
    try:
        user_index = int(user)
    except (TypeError, ValueError):
        user_index = 0
    return max(0, min(user_index, MAX_USER_INDEX))


def user_offset(base_offset: int, user: int | str | None, step: int = 1) -> int:
    """Return the offset for a user-specific recipe field."""
    return base_offset + (normalize_user(user) * step)


def read_byte(recipe: str, offset: int, default: int = 0) -> int:
    """Read one byte from a hex-encoded recipe."""
    start = offset * 2
    end = start + 2
    if not recipe or len(recipe) < end:
        return default
    try:
        return int(recipe[start:end], 16)
    except ValueError:
        return default


def write_byte(recipe: str, offset: int, value: int) -> str:
    """Write one byte to a hex-encoded recipe, extending with zeroes if needed."""
    start = offset * 2
    end = start + 2
    if len(recipe) < end:
        recipe = recipe + ("0" * (end - len(recipe)))
    return f"{recipe[:start]}{int(value) & 0xFF:02x}{recipe[end:]}"


def decode_recipe(recipe: str, user: int | str | None = 0) -> dict:
    """Decode known user-editable fields from a rev. 280 recipe."""
    temperature_byte = read_byte(recipe, user_offset(OFFSET_TEMPERATURE, user, 2), 2)
    preinfusion_byte = read_byte(recipe, user_offset(OFFSET_PREINFUSION, user, 4), 0)
    extraction_byte = read_byte(recipe, user_offset(OFFSET_EXTRACTION, user), 0)
    strength_byte = read_byte(recipe, user_offset(OFFSET_COFFEE_STRENGTH, user, 2), 4)

    return {
        "amount": read_byte(recipe, user_offset(OFFSET_COFFEE_VOLUME, user, 2), 40),
        "pressure": read_byte(recipe, user_offset(OFFSET_MILK_FOAM, user), 1),
        "tank": read_byte(recipe, user_offset(OFFSET_HOT_WATER, user), 20) * 5,
        "coffee_temperature": BYTE_TO_TEMPERATURE.get(temperature_byte, "medium"),
        "preinfusion": f"0:{max(0, min(preinfusion_byte, 5)):02d}",
        "extraction": BYTE_TO_EXTRACTION.get(extraction_byte, "standard"),
        "coffee_strength": str({1: 6, 2: 8, 3: 9, 4: 10, 5: 11}.get(strength_byte, 9)),
    }


def encode_recipe(recipe: str, settings: dict, user: int | str | None = 0) -> str:
    """Apply known user-editable fields to a rev. 280 recipe."""
    result = recipe

    if "coffee_temperature" in settings:
        result = write_byte(result, user_offset(OFFSET_TEMPERATURE, user, 2), TEMPERATURE_TO_BYTE.get(settings["coffee_temperature"], 2))
    if "preinfusion" in settings:
        result = write_byte(result, user_offset(OFFSET_PREINFUSION, user, 4), int(str(settings["preinfusion"]).split(":")[-1]))
    if "amount" in settings:
        result = write_byte(result, user_offset(OFFSET_COFFEE_VOLUME, user, 2), int(float(settings["amount"])))
    if "pressure" in settings:
        result = write_byte(result, user_offset(OFFSET_MILK_FOAM, user), int(float(settings["pressure"])))
    if "extraction" in settings:
        result = write_byte(result, user_offset(OFFSET_EXTRACTION, user), EXTRACTION_TO_BYTE.get(settings["extraction"], 0))
    if "tank" in settings:
        result = write_byte(result, user_offset(OFFSET_HOT_WATER, user), int(float(settings["tank"])) // 5)
    if "coffee_strength" in settings:
        result = write_byte(result, user_offset(OFFSET_COFFEE_STRENGTH, user, 2), {6: 1, 8: 2, 9: 3, 10: 4, 11: 5}.get(int(settings["coffee_strength"]), 3))

    return result
