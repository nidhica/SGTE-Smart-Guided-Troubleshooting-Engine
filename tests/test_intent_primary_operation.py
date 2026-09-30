"""Regression: primary enable/disable must survive incidental secondary op tokens."""

from sgte.intent import extract_intent


def test_enable_full_screen_split_view_is_enable():
    intent = extract_intent("Enable Full screen in Split screen view")
    assert intent.operation == "enable"


def test_enable_voice_access_is_enable():
    intent = extract_intent("Enable Voice Access")
    assert intent.operation == "enable"


def test_disable_allow_apps_is_disable():
    intent = extract_intent("Disable Allow apps to be pinned")
    assert intent.operation == "disable"


def test_enable_palm_touch_to_turn_off_is_enable():
    intent = extract_intent("Enable Palm touch to turn off screen")
    assert intent.operation == "enable"


def test_how_do_i_enable_split_view_is_enable():
    intent = extract_intent("How do I enable Full screen in Split screen view?")
    assert intent.operation == "enable"


def test_turn_off_voice_access_is_disable():
    intent = extract_intent("Turn off Voice Access")
    assert intent.operation == "disable"


def test_genuinely_ambiguous_multi_operation_stays_unknown():
    intent = extract_intent("Enable WiFi and disable Bluetooth")
    assert intent.operation == "unknown"


def test_single_open_operation_still_open():
    intent = extract_intent("View Bluetooth")
    assert intent.operation == "open"
