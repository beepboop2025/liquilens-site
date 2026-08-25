"""The versioned Postman artifact mirrors the anonymous public OpenAPI."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTION = ROOT / "integrations/postman/liquilens-public-api.postman_collection.json"
PUBLIC_PATHS = {
    "/api",
    "/api/health",
    "/api/failure-radar/board",
    "/api/failure-radar/institution/{{institutionSlug}}",
    "/api/failure-radar/validation",
    "/api/failure-radar/model-card",
    "/api/evidence/markets",
    "/api/universe/search",
}


def test_collection_is_no_auth_read_only_and_complete():
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    assert collection["info"]["schema"].endswith("/v2.1.0/collection.json")
    assert collection["auth"] == {"type": "noauth"}
    assert len(collection["item"]) == 8
    assert {item["request"]["method"] for item in collection["item"]} == {"GET"}
    paths = {
        item["request"]["url"]["raw"].removeprefix("{{baseUrl}}").split("?", 1)[0]
        for item in collection["item"]
    }
    assert paths == PUBLIC_PATHS
    serialized = json.dumps(collection).lower()
    for forbidden in ("bearer", "apikey", "password", "client_secret"):
        assert forbidden not in serialized


def test_collection_preserves_coverage_and_authority_boundaries():
    collection = json.loads(COLLECTION.read_text(encoding="utf-8"))
    assert "not a credit rating" in collection["info"]["description"].lower()
    assert "uncovered institutions remain uncovered" in collection["info"]["description"].lower()
    dossier = next(item for item in collection["item"] if item["name"] == "Institution Dossier")
    assert "uncovered slug returns 404" in dossier["request"]["description"]
    readme = (ROOT / "integrations/postman/README.md").read_text(encoding="utf-8")
    assert "not** live" in readme
    assert "owner-controlled" in readme
