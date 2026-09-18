"""Tests for polygon loading and point-in-polygon lookup."""

from __future__ import annotations

import pytest

from common.wards import WardIndex, get_index, reset_index


# ------------------------------------------------------------------- loading

def test_only_usable_features_are_indexed(ward_index):
    """Features without a ward_id or geometry are skipped, not fatal.

    Real boundary exports contain junk rows. One bad feature must not take down
    the lookup for all 250 wards.
    """
    assert len(ward_index) == 2
    assert {w.ward_id for w in ward_index.wards} == {"DEL-0001", "DEL-0002"}


def test_ward_metadata_is_preserved(ward_index):
    ward = ward_index.get("DEL-0001")
    assert ward.ward_name == "Westside"
    assert ward.zone == "City-SP"


def test_ward_name_falls_back_to_id_when_absent():
    index = WardIndex.from_geojson(
        {
            "features": [
                {
                    "properties": {"ward_id": "DEL-0099"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                }
            ]
        }
    )
    assert index.get("DEL-0099").ward_name == "DEL-0099"


def test_empty_collection_is_handled():
    index = WardIndex.from_geojson({"features": []})
    assert len(index) == 0
    assert index.lookup(28.05, 77.05) is None


def test_self_intersecting_polygon_is_repaired_not_dropped():
    """A bowtie ring is repaired with buffer(0) rather than discarded.

    Boundary exports from real sources routinely contain these.
    """
    bowtie = {
        "features": [
            {
                "properties": {"ward_id": "DEL-0500", "ward_name": "Bowtie"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [2, 2], [2, 0], [0, 2], [0, 0]]],
                },
            }
        ]
    }
    index = WardIndex.from_geojson(bowtie)
    assert len(index) == 1


# -------------------------------------------------------------------- lookup

def test_point_inside_resolves_to_the_right_ward(ward_index):
    assert ward_index.lookup(28.05, 77.05).ward_id == "DEL-0001"
    assert ward_index.lookup(28.05, 77.15).ward_id == "DEL-0002"


def test_lat_lng_order_is_not_transposed(ward_index):
    """GeoJSON is (lng, lat) and the API is (lat, lng).

    Getting this backwards is the single easiest way to ship a lookup that
    silently returns the wrong ward, so it is asserted directly.
    """
    # (28.05, 77.05) is inside; the transposition (77.05, 28.05) is not.
    assert ward_index.lookup(28.05, 77.05) is not None
    assert ward_index.lookup(77.05, 28.05) is None


def test_point_outside_all_polygons_returns_none(ward_index):
    assert ward_index.lookup(19.07, 72.87) is None  # Mumbai


def test_point_in_the_bounding_box_but_outside_the_polygon():
    """The R-tree narrows by bounding box; containment must still be confirmed.

    An L-shape has a large bbox and a hole in it. Returning a ward for a point
    in that hole would be the classic STRtree bug.
    """
    l_shape = {
        "features": [
            {
                "properties": {"ward_id": "DEL-0600", "ward_name": "L"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2], [0, 0]]
                    ],
                },
            }
        ]
    }
    index = WardIndex.from_geojson(l_shape)
    assert index.lookup(0.5, 0.5).ward_id == "DEL-0600"  # in the L
    assert index.lookup(1.5, 1.5) is None  # in the bbox, outside the L


def test_point_on_a_shared_edge_resolves_deterministically(ward_index):
    """Two wards meet at lng 77.1. A citizen standing there gets an answer."""
    first = ward_index.lookup(28.05, 77.1)
    assert first is not None
    assert ward_index.lookup(28.05, 77.1).ward_id == first.ward_id


@pytest.mark.parametrize("lat,lng", [(91, 77), (-91, 77), (28, 181), (28, -181)])
def test_out_of_range_coordinates_raise(ward_index, lat, lng):
    with pytest.raises(ValueError):
        ward_index.lookup(lat, lng)


def test_get_by_unknown_id_returns_none(ward_index):
    assert ward_index.get("DEL-9999") is None
    assert ward_index.get("") is None


# ------------------------------------------------------------ module caching

def test_index_is_built_once_and_cached(wards_file):
    reset_index()
    first = get_index()
    second = get_index()
    assert first is second, "index must be cached at module level across invocations"
    assert len(first) == 2


def test_reset_index_forces_a_rebuild(wards_file):
    first = get_index()
    reset_index()
    assert get_index() is not first
