import copy

from sgte.engine import TroubleshootingEngine, no_match_dict, no_match_response
from sgte.official_schema import ContextDeeplinkResponse


def test_valid_sample_output_passes_schema_and_rules(validator, sample_output):
    result = validator.validate(sample_output)
    assert result.ok, result.errors
    assert result.response is not None
    assert result.response.contexts
    assert result.response.contexts[0].actions[0].category.value == "auto"
    assert result.response.contexts[0].actions[1].category.value == "manual"


def test_malformed_response_fails(validator):
    result = validator.validate({"contexts": "not-a-list"})
    assert not result.ok
    assert result.errors


def test_invalid_category_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    payload["response"]["contexts"][0]["actions"][0]["category"] = "not-a-category"
    result = validator.validate(payload)
    assert not result.ok
    assert any("category" in err.lower() or "actioncategory" in err.lower() for err in result.errors)


def test_missing_required_fields_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    del payload["response"]["contexts"][0]["score"]
    result = validator.validate(payload)
    assert not result.ok
    assert any("score" in err.lower() for err in result.errors)


def test_manual_action_with_actionable_deeplink_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    auto_link = payload["response"]["contexts"][0]["actions"][0]["stepGroups"][0]["actionableDeeplink"]
    manual = payload["response"]["contexts"][0]["actions"][1]
    manual["stepGroups"][0]["actionableDeeplink"] = copy.deepcopy(auto_link)
    result = validator.validate(payload)
    assert not result.ok
    assert any("manual" in err.lower() for err in result.errors)


def test_invalid_deeplink_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    payload["response"]["contexts"][0]["actions"][0]["stepGroups"][0]["actionableDeeplink"][
        "deeplink"
    ] = "bixby://masked/act/not-in-catalogue"
    result = validator.validate(payload)
    assert not result.ok
    assert any("catalogue" in err.lower() for err in result.errors)


def test_invalid_validation_deeplink_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    payload["response"]["contexts"][0]["actions"][0]["stepGroups"][0]["validationDeeplink"] = {
        "deeplink": "bixby://masked/val/not-in-catalogue",
        "key": "not-a-real-key",
        "resultType": "boolean",
        "condition": "equal",
        "value": "True",
    }
    result = validator.validate(payload)
    assert not result.ok
    assert any("validation" in err.lower() for err in result.errors)


def test_url_leak_in_step_text_fails(validator, sample_output):
    payload = copy.deepcopy(sample_output)
    payload["response"]["contexts"][0]["actions"][0]["stepGroups"][0]["steps"].append(
        "Then visit https://example.com/support for more help."
    )
    result = validator.validate(payload)
    assert not result.ok
    assert any("url leak" in err.lower() for err in result.errors)


def test_valid_masked_samsung_deeplink_is_not_a_url_leak(validator, sample_output):
    result = validator.validate(sample_output)
    assert result.ok, result.errors
    uri = sample_output["response"]["contexts"][0]["actions"][0]["stepGroups"][0]["actionableDeeplink"][
        "deeplink"
    ]
    assert uri.startswith("bixby://masked/act/")
    assert not any("url leak" in err.lower() for err in result.errors)


def test_no_match_response_is_official_empty_contexts(validator):
    payload = no_match_dict()
    assert payload == {"contexts": []}
    parsed = no_match_response()
    assert isinstance(parsed, ContextDeeplinkResponse)
    assert parsed.contexts == []
    result = validator.validate(payload)
    assert result.ok, result.errors


def test_engine_no_match_when_no_siis_overlap():
    engine = TroubleshootingEngine()
    result = engine.respond("zzzzqxqwy unique-nonoverlap-token-xyzzy")
    assert result.matched is False
    assert result.siis_hits == []
    assert result.response.contexts == []
