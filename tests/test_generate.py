import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyarrow.parquet as pq
import pytest

from chap_test_data.checks import run_checks
from chap_test_data.files import Expected
from chap_test_data.generate import DatasetSpec, build


def generate(tmp_path: Path, **options: object) -> tuple[Path, Expected]:
    settings = {"location_count": 6, "periods": 12, "period": "monthly", "columns": 4, "seed": 42} | options
    spec = DatasetSpec(name="test", **settings)
    directory = tmp_path / spec.name
    return directory, build(spec, directory)


def observations(directory: Path):
    return pq.read_table(directory / "observations.parquet").to_pandas()


def test_a_dataset_has_one_sorted_row_per_location_and_period(tmp_path):
    directory, expected = generate(tmp_path)
    frame = observations(directory)
    assert len(frame) == 6 * 12 == expected.rows
    assert not frame.duplicated(["location", "time_period"]).any()
    assert frame.equals(frame.sort_values(["location", "time_period"], ignore_index=True))
    assert list(frame.columns) == [
        "location",
        "time_period",
        "disease_cases",
        "population",
        "rainfall",
        "mean_temperature",
    ]
    assert Expected.read(directory) == expected
    assert (expected.http, expected.imported_count, expected.rejected) == (200, 6, 0)


def test_periods_are_in_the_form_chap_stores():
    _, monthly = generate_periods(period="monthly", periods=13)
    assert monthly[:2] == ["201601", "201602"] and monthly[-1] == "201701"
    _, weekly = generate_periods(period="weekly", years=10)
    # Real ISO weeks: 2020 has a week 53.
    assert weekly[0] == "2016W01" and "2020W53" in weekly and len(weekly) == 522


def generate_periods(**options):
    from chap_test_data.generate import period_strings

    return None, period_strings(DatasetSpec(name="p", **options))[0]


def test_the_same_seed_gives_the_same_files(tmp_path):
    first, _ = generate(tmp_path / "a")
    second, _ = generate(tmp_path / "b")
    assert (first / "observations.parquet").read_bytes() == (second / "observations.parquet").read_bytes()


def test_without_a_seed_a_random_one_is_recorded(tmp_path):
    spec = DatasetSpec(name="random", location_count=2, periods=3)
    expected = build(spec, tmp_path / "random")
    assert expected.seed is not None
    assert Expected.read(tmp_path / "random").seed == expected.seed


def test_values_stay_within_chapkit_ranges(tmp_path):
    directory, _ = generate(tmp_path, columns=12, location_count=20, periods=48, missing=0)
    frame = observations(directory)
    assert frame["disease_cases"].min() >= 0
    assert frame["population"].between(50_000, 1_500_000 * 1.03**3).all()
    assert frame["rainfall"].between(0, 305).all()
    assert frame["mean_temperature"].between(15, 33).all()
    assert frame[["covariate_11", "covariate_12"]].stack().between(0, 100).all()
    # Population is a yearly estimate: the same all year, growing 2 to 3% from one year to the next.
    frame["year"] = frame["time_period"].str[:4]
    assert (frame.groupby(["location", "year"])["population"].nunique() == 1).all()
    yearly = frame.groupby(["location", "year"])["population"].first().unstack()
    growth = (yearly.iloc[:, 1:].to_numpy() / yearly.iloc[:, :-1].to_numpy()).ravel()
    assert ((growth > 1.019) & (growth < 1.031)).all()


def test_metadata_carries_the_settings(tmp_path):
    directory, _ = generate(tmp_path, masked=[("201603", "201605")])
    metadata = pq.read_schema(directory / "observations.parquet").metadata
    dataset = json.loads(metadata[b"chap.dataset"])
    assert metadata[b"chap.spec_version"] == b"1"
    assert dataset["target_column"] == "disease_cases"
    assert dataset["masked_ranges"] == [{"start": "201603", "end": "201605", "name": "masked"}]
    assert set(json.loads(metadata[b"chap.columns"])) == {"disease_cases", "population", "rainfall", "mean_temperature"}


def test_without_metadata_only_the_spec_version_is_written(tmp_path):
    directory, _ = generate(tmp_path, metadata=False)
    keys = {k for k in pq.read_schema(directory / "observations.parquet").metadata if k.startswith(b"chap.")}
    assert keys == {b"chap.spec_version"}


def test_named_columns_replace_the_defaults_and_the_first_is_the_target(tmp_path):
    directory, _ = generate(tmp_path, column_names=["malaria_cases", "precipitation"])
    assert list(observations(directory).columns) == ["location", "time_period", "malaria_cases", "precipitation"]
    dataset = json.loads(pq.read_schema(directory / "observations.parquet").metadata[b"chap.dataset"])
    assert dataset["target_column"] == "malaria_cases"


def test_polygons_tile_a_country_like_map(tmp_path):
    import shapely

    directory, _ = generate(tmp_path, location_count=40, geometry="polygon")
    polygons = gpd.read_parquet(directory / "locations.parquet").geometry.to_numpy()
    assert len(polygons) == 40 and shapely.is_valid(polygons).all()
    assert set(shapely.get_type_id(polygons)) == {3}  # Polygon, one piece each
    # About 800 points per area, the default.
    assert 600 < np.median(shapely.get_num_coordinates(polygons)) < 1000
    # No gaps and no overlaps: the areas add up to the country they tile (to floating-point noise).
    country = shapely.union_all(polygons)
    assert country.geom_type == "Polygon"
    assert sum(shapely.Polygon(hole).area for hole in country.interiors) < 1e-12 * country.area
    assert abs(country.area - shapely.area(polygons).sum()) < 1e-9 * country.area
    # As real boundaries: a border much longer than a circle of the same area (chap-core's examples: 1.4 to 1.9).
    ratio = np.median([p.length / (2 * np.sqrt(np.pi * p.area)) for p in polygons])
    assert 1.4 < ratio < 2.1
    metadata = pq.read_schema(directory / "locations.parquet").metadata
    assert b"geo" in metadata and metadata[b"chap.spec_version"] == b"1"


def test_points_are_the_default_and_geojson_replaces_geoparquet(tmp_path):
    directory, _ = generate(tmp_path, geojson=True)
    assert not (directory / "locations.parquet").exists()
    collection = json.loads((directory / "locations.geojson").read_text())
    assert {f["geometry"]["type"] for f in collection["features"]} == {"Point"}
    assert len(collection["features"]) == 6


@pytest.mark.parametrize(
    ("options", "http", "detail"),
    [
        ({"duplicate_rows": 1}, 422, "more than one row"),
        ({"text_column": "parent"}, 422, "not numeric: parent"),
        ({"drop_time_period": True}, 422, "no time_period column"),
        ({"spec_version": "2"}, 422, "this Chap reads version"),
        ({"not_parquet": True}, 422, "not a Parquet file"),
    ],
)
def test_faults_expect_the_upload_to_be_refused(tmp_path, options, http, detail):
    directory, expected = generate(tmp_path, **options)
    assert (expected.http, expected.detail) == (http, detail)
    if options.get("not_parquet"):
        assert not (directory / "observations.parquet").read_bytes().startswith(b"PAR1")


def test_gaps_and_missing_locations_reject_those_locations(tmp_path):
    directory, expected = generate(tmp_path, covariate_gaps=2, drop_locations=1)
    assert (expected.http, expected.imported_count, expected.rejected) == (200, 3, 3)
    found = {result.name: result.found for result in run_checks(directory)[1]}
    assert found["locations with a covariate gap"] == 2
    assert found["locations missing from locations"] == 1
    assert found["duplicate (location, time_period)"] == 0


def test_too_many_rows_expect_a_422(tmp_path, monkeypatch):
    import chap_test_data.generate as generate_module

    monkeypatch.setattr(generate_module, "MAX_ROWS", 10)
    _, expected = generate(tmp_path)
    assert (expected.http, expected.detail) == (422, "at most 10 are accepted")


@pytest.mark.parametrize(
    "options",
    [
        {"column_names": ["location"]},
        {"column_names": ["a", "a"]},
        {"geometry": "polygon", "corners": 2},
        {"districts_per_region": 0},
        {"facilities_per_district": 0},
    ],
)
def test_impossible_settings_are_refused(tmp_path, options):
    with pytest.raises(ValueError):
        generate(tmp_path, **options)


def read_hierarchy(directory):
    return gpd.read_file(directory / "hierarchy.geojson").set_index("id")


def assert_tree(location_count, hierarchy, levels):
    """Each location and area lies inside the area its parent names, one level up, ending at the country."""
    import shapely

    assert sorted(hierarchy["level"].unique()) == levels
    country = hierarchy[hierarchy["level"] == 1]
    assert len(country) == 1 and country["parent"].isna().all()
    for _, area in hierarchy[hierarchy["level"] > 1].iterrows():
        parent = hierarchy.loc[area["parent"]]
        assert parent["level"] == area["level"] - 1
        assert parent.geometry.buffer(1e-9).contains(area.geometry)
    for row in location_count.itertuples():
        parent = hierarchy.loc[row.parent]
        assert parent["level"] == row.level - 1
        assert parent.geometry.buffer(1e-9).contains(row.geometry)
    # The areas of each level tile the country: their union is the country, without gaps or overlaps.
    for level in levels[1:]:
        areas = hierarchy[hierarchy["level"] == level].geometry.to_numpy()
        assert abs(shapely.area(areas).sum() - country.geometry.iloc[0].area) < 1e-6 * country.geometry.iloc[0].area


def test_facilities_sit_at_level_4_under_districts_regions_and_the_country(tmp_path):
    directory, _ = generate(tmp_path, location_count=600)
    facilities = gpd.read_parquet(directory / "locations.parquet")
    hierarchy = read_hierarchy(directory)
    assert set(facilities["level"]) == {4}
    assert (hierarchy["level"] == 3).sum() == 12  # one district per 50 facilities
    assert_tree(facilities, hierarchy, [1, 2, 3])


def test_districts_sit_at_level_3_under_regions_and_the_country(tmp_path):
    directory, _ = generate(tmp_path, location_count=120, geometry="polygon", corners=64)
    districts = gpd.read_parquet(directory / "locations.parquet")
    hierarchy = read_hierarchy(directory)
    assert set(districts["level"]) == {3}
    assert (hierarchy["level"] == 2).sum() == 12  # one region per 10 districts
    assert_tree(districts, hierarchy, [1, 2])


def test_polygons_follow_the_geojson_right_hand_rule(tmp_path):
    import shapely

    directory, _ = generate(tmp_path, location_count=60, geometry="polygon", corners=64)
    polygons = gpd.read_parquet(directory / "locations.parquet").geometry.to_numpy()
    assert all(shapely.is_ccw(p.exterior) for p in polygons)
    assert all(shapely.is_ccw(p.exterior) for p in read_hierarchy(directory).geometry)


def test_the_hierarchy_sizes_can_be_chosen(tmp_path):
    directory, _ = generate(tmp_path, location_count=100, geometry="polygon", corners=16, districts_per_region=25)
    assert (read_hierarchy(directory)["level"] == 2).sum() == 4
    directory, _ = generate(
        tmp_path / "facilities", location_count=300, facilities_per_district=100, districts_per_region=1
    )
    hierarchy = read_hierarchy(directory)
    assert (hierarchy["level"] == 3).sum() == 3 and (hierarchy["level"] == 2).sum() == 3
    assert_tree(gpd.read_parquet(directory / "locations.parquet"), hierarchy, [1, 2, 3])
