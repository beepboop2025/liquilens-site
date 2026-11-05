#!/usr/bin/env python3
"""Build reproducible district viewport extents from the rainfall boundary source.

The input GeoJSON must match the SHA256 recorded in the rainfall registry.
The output is an ODbL-attributed derived database of bounding boxes, not parcel
boundaries or a statement about current administrative boundaries.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path


def coordinate_pairs(value):
    if not isinstance(value, list) or not value:
        raise ValueError("Missing or malformed geometry coordinates")
    if isinstance(value[0], (int, float)) and not isinstance(value[0], bool):
        if len(value) < 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in value[:2]
        ):
            raise ValueError("Coordinates must be finite numbers")
        x, y = value[:2]
        if not -180 <= x <= 180 or not -90 <= y <= 90:
            raise ValueError("Coordinates must be WGS84 longitude and latitude")
        yield x, y
    else:
        for child in value:
            yield from coordinate_pairs(child)


def geometry_bbox(geometry):
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Only Polygon and MultiPolygon boundaries are supported")
    pairs = list(coordinate_pairs(geometry.get("coordinates")))
    xs, ys = zip(*pairs)
    box = [min(xs), min(ys), max(xs), max(ys)]
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError("A district extent must have nonzero area")
    # Round outwards so the derived viewport never clips an upstream extreme.
    return [math.floor(box[0] * 1e6) / 1e6, math.floor(box[1] * 1e6) / 1e6,
            math.ceil(box[2] * 1e6) / 1e6, math.ceil(box[3] * 1e6) / 1e6]


def build_catalog(registry, boundary_bytes):
    source = registry["boundary_source"]
    digest = hashlib.sha256(boundary_bytes).hexdigest()
    if digest != source["sha256"]:
        raise ValueError("Boundary SHA256 does not match the pinned rainfall source")
    data = json.loads(boundary_bytes)
    if data.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    by_shape = {}
    for feature in data.get("features", []):
        shape = feature.get("properties", {}).get("shapeID")
        if not isinstance(shape, str) or not shape or shape in by_shape:
            raise ValueError("Missing or duplicate upstream shapeID")
        by_shape[shape] = geometry_bbox(feature.get("geometry"))
    places, ids, matched_shapes = [], set(), set()
    for district in registry["districts"]:
        identifier, shape = district["id"], district["gb_shape_id"]
        if identifier in ids or shape in matched_shapes or shape not in by_shape:
            raise ValueError("Duplicate district or missing exact boundary join")
        ids.add(identifier)
        matched_shapes.add(shape)
        places.append({"id": identifier, "name": district["name"], "state": district["state"],
                       "gb_shape_id": shape, "bbox": by_shape[shape],
                       "boundary_vintage": str(source["year_represented"])})
    if len(places) != source["districts"] or matched_shapes != set(by_shape):
        raise ValueError("Boundary and district registry coverage must match completely")
    metadata = {k: source[k] for k in ("product", "credit", "citation", "boundary_id",
                "year_represented", "upstream", "licence", "download", "sha256")}
    metadata.update({"schema": "liquilens-district-viewports/v1", "district_count": len(places),
                     "coordinate_system": "EPSG:4326", "coordinate_order": "west,south,east,north",
                     "licence_url": "https://opendatacommons.org/licenses/odbl/1-0/",
                     "state_assignment": source.get("state_assignment", {}),
                     "use": "District bounding extents for satellite viewport framing only. Not parcel outlines, current legal boundaries, or measurements derived from imagery."})
    return places, metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("banking/geography"))
    args = parser.parse_args()
    places, metadata = build_catalog(json.loads(args.registry.read_text()), args.boundaries.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "places.json").write_text(json.dumps(places, ensure_ascii=False, separators=(",", ":")) + "\n")
    (args.output / "places-source.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"districts": len(places), "boundary_sha256": metadata["sha256"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
