"""The geographic join must fail closed; names are never used as a fallback."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("geo_catalog", Path(__file__).parents[1] / "scripts/build_geography_catalog.py")
CATALOG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CATALOG)


def fixture():
    feature = {"type": "Feature", "properties": {"shapeID": "exact-shape"},
               "geometry": {"type": "Polygon", "coordinates": [[[75.1, 26.1], [76.2, 26.1], [76.2, 27.2], [75.1, 26.1]]]}}
    raw = json.dumps({"type": "FeatureCollection", "features": [feature]}).encode()
    source = {key: "fixture" for key in ("product", "credit", "citation", "boundary_id", "upstream", "licence", "download")}
    source.update(sha256=hashlib.sha256(raw).hexdigest(), year_represented="2021", districts=1)
    registry = {"boundary_source": source, "districts": [{"id": "in-dist-test", "name": "Test", "state": "Test state", "gb_shape_id": "exact-shape"}]}
    return registry, raw


def test_exact_join_and_attribution():
    registry, raw = fixture()
    rows, source = CATALOG.build_catalog(registry, raw)
    assert rows[0]["bbox"] == [75.1, 26.1, 76.2, 27.2]
    assert rows[0]["boundary_vintage"] == "2021"
    assert source["sha256"] == hashlib.sha256(raw).hexdigest()
    assert source["coordinate_order"] == "west,south,east,north"
    assert "Not parcel outlines" in source["use"]


def test_source_hash_mismatch_is_rejected():
    registry, raw = fixture()
    with pytest.raises(ValueError, match="SHA256"):
        CATALOG.build_catalog(registry, raw + b" ")


def test_names_never_substitute_for_missing_exact_shape():
    registry, raw = fixture()
    registry["districts"][0]["gb_shape_id"] = "missing"
    with pytest.raises(ValueError, match="exact boundary join"):
        CATALOG.build_catalog(registry, raw)


def test_duplicate_registry_is_rejected():
    registry, raw = fixture()
    registry["districts"].append(dict(registry["districts"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        CATALOG.build_catalog(registry, raw)


def test_multipolygon_covers_detached_parts_and_rounds_outwards():
    shape = {"type": "MultiPolygon", "coordinates": [
        [[[75.1234567, 26.1234567], [76, 26], [76, 27], [75.1234567, 26.1234567]]],
        [[[74, 25], [74.2, 25], [74.2, 25.2], [74, 25]]]]}
    assert CATALOG.geometry_bbox(shape) == [74, 25, 76, 27]


@pytest.mark.parametrize("coordinates", [[], [[[True, 26], [76, 27]]], [[[181, 26], [76, 27]]], [[[75, float("nan")], [76, 27]]]])
def test_invalid_coordinates_are_rejected(coordinates):
    with pytest.raises(ValueError):
        CATALOG.geometry_bbox({"type": "Polygon", "coordinates": coordinates})


def test_committed_catalogue_has_complete_attributed_extents():
    root = Path(__file__).parents[1] / "banking/geography"
    places = json.loads((root / "places.json").read_text())
    source = json.loads((root / "places-source.json").read_text())
    assert len(places) == source["district_count"] == 735
    assert len({row["id"] for row in places}) == len({row["gb_shape_id"] for row in places}) == 735
    for row in places:
        west, south, east, north = row["bbox"]
        assert -180 <= west < east <= 180 and -90 <= south < north <= 90
        assert row["boundary_vintage"] == source["year_represented"] == "2021"
