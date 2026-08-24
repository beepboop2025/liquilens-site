import json
from pathlib import Path

from scripts.verify_catalog_edge import response_problem


ROOT = Path(__file__).resolve().parents[1]


def test_edge_parity_accepts_only_the_exact_committed_catalog():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert response_problem(expected, body, "application/ai-catalog+json") is None


def test_edge_parity_accepts_the_exact_protocol_catalog():
    expected = json.loads(
        (ROOT / "protocol/catalog.json").read_text(encoding="utf-8")
    )
    body = json.dumps(expected, separators=(",", ":")).encode()
    assert response_problem(
        expected,
        body,
        "application/json; charset=utf-8",
        "application/json",
    ) is None


def test_edge_parity_explains_a_missing_carrier_entry():
    expected = json.loads(
        (ROOT / ".well-known/ai-catalog.json").read_text(encoding="utf-8")
    )
    actual = dict(expected)
    actual["entries"] = [
        row for row in expected["entries"]
        if row["identifier"] != "urn:air:liquilens.in:protocol:evidence-carrier"
    ]
    problem = response_problem(
        expected,
        json.dumps(actual).encode(),
        "application/ai-catalog+json; charset=utf-8",
    )
    assert problem is not None
    assert "urn:air:liquilens.in:protocol:evidence-carrier" in problem
