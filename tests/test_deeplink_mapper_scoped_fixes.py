"""Focused regressions for narrowly scoped HybridDeeplinkMapper fixes."""

from __future__ import annotations

from sgte.catalogue_index import CatalogueIndex
from sgte.hybrid_mapper import HybridDeeplinkMapper


def _mapper(deeplink_repo, tmp_path) -> HybridDeeplinkMapper:
    index = CatalogueIndex.build(deeplink_repo, tmp_path, dense_name="hashing")
    return HybridDeeplinkMapper(deeplink_repo, index)


def test_enable_touch_sensitivity_with_evidence(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Touch Sensitivity Setting",
        [
            "If you wish to keep your screen protector on, enable the Touch sensitivity option.",
            "Go to Settings, tap Display, and then tap the switch next to Touch sensitivity.",
        ],
        "enable Touch sensitivity for screen protector",
    )
    assert hit is not None
    assert hit.id == "DL-0126"
    assert hit.deeplink == "bixby://masked/act/14eb42b895"
    assert "Enable" in (hit.metadata.get("message") or "")


def test_disable_touch_sensitivity_with_evidence(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Touch Sensitivity Setting",
        [
            "If Touch sensitivity is enabled when you are not using a protective film, "
            "disable Touch sensitivity.",
        ],
        "turn off Touch sensitivity",
    )
    assert hit is not None
    assert hit.id == "DL-0125"
    assert hit.deeplink == "bixby://masked/act/1b0d34e9b4"
    assert "Disable" in (hit.metadata.get("message") or "")


def test_ambiguous_touch_sensitivity_polarity_abstains(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Touch Sensitivity Setting",
        ["Go to Settings, tap Display, and then tap the switch next to Touch sensitivity."],
        "Touch sensitivity setting",
    )
    assert hit is None


def test_full_screen_gesture_maps_to_navigation_bar(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Full Screen Gesture Function",
        [
            "If you are using the full screen gesture function, go to Settings, tap Display, "
            "and then tap Navigation bar. Select Buttons to turn off full screen gestures.",
        ],
        "full screen gesture function navigation bar buttons",
    )
    assert hit is not None
    assert hit.id == "DL-0169"
    assert hit.deeplink == "bixby://masked/act/2f3dd95259"
    assert "Navigation bar" in (hit.metadata.get("message") or "")


def test_internet_connection_maps_to_primary_wifi(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Verify Your Phone's Internet Connection",
        [
            "Ensure your phone is connected to a stable Wi-Fi or mobile data network.",
            "Touch and hold the Wi-Fi icon to check your connection status.",
        ],
        "verify internet connection wi-fi",
    )
    assert hit is not None
    assert hit.id == "DL-0313"
    assert hit.deeplink == "bixby://masked/act/cb03ac7425"
    key = (hit.validation or {}).get("key") or (hit.record.validation or {}).get("key")
    assert key == "Wi-Fi"


def test_factory_data_reset_does_not_map_to_auto_factory_reset(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    hit = mapper.find_best_deeplink(
        "Perform a Factory Data Reset",
        [
            "If the previous steps did not resolve the issue, perform a factory data reset.",
            "Navigate to Settings, search for and select Factory data reset.",
        ],
        "factory data reset",
    )
    assert hit is None or hit.id != "DL-0022"
    ranked = mapper.debug_rank(
        "Perform a Factory Data Reset",
        ["Perform a factory data reset from Settings."],
        "factory data reset",
        limit=8,
    )
    auto = [c for c in ranked if c.catalogue_id == "DL-0022"]
    assert auto
    assert all(c.rejection_reason for c in auto)


def test_edge_panels_only_with_toggle_evidence(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    # Howto without enable/disable polarity → abstain.
    assert (
        mapper.find_best_deeplink(
            "Customize the Edge panel",
            ["Swipe left on the gray Edge panel handle to find the panel."],
            "customize edge panel",
        )
        is None
    )
    # Explicit enable polarity → Enable Edge panels.
    hit = mapper.find_best_deeplink(
        "Customize the Edge panel",
        ["Enable Edge panels in Settings so you can customize the panel."],
        "enable Edge panels",
    )
    assert hit is not None
    assert hit.id == "DL-0096"
    assert hit.deeplink == "bixby://masked/act/3008ce1d3b"


def test_multi_window_only_with_toggle_evidence(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    assert (
        mapper.find_best_deeplink(
            "Use Multi window",
            ["From the screen's right side, swipe left to open the Edge panel."],
            "use multi window",
        )
        is None
    )
    hit = mapper.find_best_deeplink(
        "Use Multi window",
        ["Enable Multi window for all apps in Settings."],
        "enable Multi window for all apps",
    )
    assert hit is not None
    assert hit.id == "DL-0168"
    assert hit.deeplink == "bixby://masked/act/a70dd5e0ef"


def test_existing_time_format_and_mouse_keys_unchanged(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    time_hit = mapper.find_best_deeplink("Switch Time Format 24-hour format")
    assert time_hit is not None and time_hit.id == "DL-0001"
    mouse_on = mapper.find_best_deeplink("Enable Mouse Keys")
    mouse_off = mapper.find_best_deeplink("Disable Mouse Keys")
    assert mouse_on is not None and mouse_on.id == "DL-0008"
    assert mouse_off is not None and mouse_off.id == "DL-0007"
    assert mouse_on.deeplink != mouse_off.deeplink


def test_missing_catalogue_entries_remain_unmapped(deeplink_repo, tmp_path):
    mapper = _mapper(deeplink_repo, tmp_path)
    assert mapper.find_best_deeplink("Mirror Your TV with Smart View") is None
    assert mapper.find_best_deeplink("Clear the Email App's Cache and Data") is None
    assert mapper.find_best_deeplink("Safe Mode") is None
    assert mapper.find_best_deeplink("Force a Restart") is None
