import json

import pytest

from sgte.deeplink_repo import DeeplinkRepository
from sgte.loaders import load_deeplinks, load_siis_responses
from sgte.paths import SAMPLE_OUTPUT_JSON
from sgte.siis_repo import SiisRepository
from sgte.validator import ResponseValidator


@pytest.fixture(scope="session")
def sample_output():
    with SAMPLE_OUTPUT_JSON.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def deeplink_records():
    return load_deeplinks()


@pytest.fixture(scope="session")
def siis_records():
    return load_siis_responses()


@pytest.fixture(scope="session")
def deeplink_repo(deeplink_records):
    return DeeplinkRepository(deeplink_records)


@pytest.fixture(scope="session")
def siis_repo(siis_records):
    return SiisRepository(siis_records)


@pytest.fixture(scope="session")
def validator(deeplink_repo):
    return ResponseValidator(deeplink_repo)
