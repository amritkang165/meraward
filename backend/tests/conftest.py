"""Shared fixtures.

The ward fixture is a deliberately tiny, synthetic grid rather than a sample of
real Delhi boundaries: these tests assert lookup *behaviour*, and a hand-checkable
square makes a failure obvious. Real polygon quality is verified by eye on a map
before upload, which is a different job.
"""

from __future__ import annotations

import json

import pytest

from common.wards import WardIndex, reset_index


def _square(lng0: float, lat0: float, lng1: float, lat1: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [[lng0, lat0], [lng1, lat0], [lng1, lat1], [lng0, lat1], [lng0, lat0]]
        ],
    }


#: Two adjacent unit squares sharing the edge at lng = 77.1.
WARD_GEOJSON: dict = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"ward_id": "DEL-0001", "ward_name": "Westside", "zone": "City-SP"},
            "geometry": _square(77.0, 28.0, 77.1, 28.1),
        },
        {
            "type": "Feature",
            "properties": {"ward_id": "DEL-0002", "ward_name": "Eastside", "zone": "City-SP"},
            "geometry": _square(77.1, 28.0, 77.2, 28.1),
        },
        # No ward_id — must be skipped, not crash the build.
        {
            "type": "Feature",
            "properties": {"ward_name": "Nameless"},
            "geometry": _square(77.2, 28.0, 77.3, 28.1),
        },
        # Null geometry — must be skipped.
        {
            "type": "Feature",
            "properties": {"ward_id": "DEL-0004", "ward_name": "Ghost"},
            "geometry": None,
        },
    ],
}


@pytest.fixture
def ward_index() -> WardIndex:
    return WardIndex.from_geojson(WARD_GEOJSON)


@pytest.fixture
def wards_file(tmp_path, monkeypatch):
    """Point the module-level loader at a local file instead of S3."""
    path = tmp_path / "wards.geojson"
    path.write_text(json.dumps(WARD_GEOJSON), encoding="utf-8")
    monkeypatch.setenv("WARDS_GEOJSON_PATH", str(path))
    reset_index()
    yield path
    reset_index()


@pytest.fixture(autouse=True)
def _clean_config_cache():
    """``load_config`` is lru_cached; drop it between tests that set env vars."""
    from common.config import load_config

    load_config.cache_clear()
    yield
    load_config.cache_clear()
