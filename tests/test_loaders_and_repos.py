from sgte.deeplink_repo import DeeplinkRepository
from sgte.loaders import load_deeplinks, load_siis_responses
from sgte.paths import DEEPLINKS_JSON, SIIS_RESPONSES_JSON, INPUT_TXT
from sgte.siis_repo import SiisRepository


def test_siis_loading(siis_records):
    assert SIIS_RESPONSES_JSON.is_file()
    assert len(siis_records) == 20
    row = siis_records[0]
    assert row.id == "row_1"
    assert row.original_query
    assert row.title
    assert row.content
    assert "title" in row.siis_response
    assert "content" in row.siis_response
    reloaded = load_siis_responses()
    assert len(reloaded) == len(siis_records)


def test_deeplink_catalogue_loading(deeplink_records):
    assert DEEPLINKS_JSON.is_file()
    assert len(deeplink_records) == 578
    uris = [row.deeplink for row in deeplink_records]
    assert len(uris) == len(set(uris))
    dummy = next(row for row in deeplink_records if row.id == "DL-DUMMY")
    assert dummy.deeplink == "bixby://dummy_positive"
    backup = next(row for row in deeplink_records if row.deeplink == "bixby://masked/act/b3ed3ed663")
    assert backup.deeplink == "bixby://masked/act/b3ed3ed663"
    assert backup.id == "DL-0542"


def test_metadata_based_deeplink_lookup(deeplink_repo: DeeplinkRepository):
    hits = deeplink_repo.search("Enable Back up data Samsung Cloud")
    assert hits
    top = hits[0]
    assert top.id == "DL-0542"
    assert top.deeplink == "bixby://masked/act/b3ed3ed663"
    assert top.metadata["message"] == "Enable Back up data (Samsung Cloud)"
    assert top.validation is not None
    assert top.validation["deeplink"] == "bixby://masked/val/266037d0c5"


def test_deeplink_search_does_not_use_masked_uri():
    repo = DeeplinkRepository.from_file()
    hits = repo.search("bixby://masked/act/b3ed3ed663")
    assert all(hit.deeplink != "bixby://masked/act/b3ed3ed663" for hit in hits)


def test_siis_lexical_search_on_official_query(siis_repo: SiisRepository):
    query = INPUT_TXT.read_text(encoding="utf-8").splitlines()[0]
    hits = siis_repo.search(query)
    assert hits
    assert hits[0].id == "row_1"
    assert hits[0].title == "Email server not responding on Samsung phone or tablet"
    assert hits[0].original_query
    assert hits[0].siis_response["content"]
