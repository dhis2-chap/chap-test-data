"""Synthetic datasets of any size, written in batches of org units so memory stays small.

Options also make the files Chap must reject or partly reject, and expected.json records the
answer Chap's Phase 1 endpoint should give.
"""

import itertools
import json
import secrets
import shutil
import string
from collections.abc import Callable
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq
import shapely
from pydantic import BaseModel

from chap_test_data.files import (
    MAX_FILE_BYTES,
    MAX_ROWS,
    MAX_UPLOAD_BYTES,
    ROW_GROUP_SIZE,
    SPEC_VERSION,
    Expected,
    write_locations,
)

ROWS_PER_BATCH = 1_000_000
WEEKS_PER_YEAR = 52.1775

COLUMNS = {
    "disease_cases": {"description": "Confirmed cases", "dhis2_data_element": "DeCases0001"},
    "population": {"unit": "people", "dhis2_data_element": "DePopulat01"},
    "rainfall": {"unit": "mm", "source": "ERA5-Land"},
    "mean_temperature": {"unit": "degC", "source": "ERA5-Land"},
    "min_temperature": {"unit": "degC", "source": "ERA5-Land"},
    "max_temperature": {"unit": "degC", "source": "ERA5-Land"},
    "relative_humidity": {"unit": "%", "source": "ERA5-Land"},
    "soil_moisture": {"unit": "m3/m3", "source": "ERA5-Land"},
    "ndvi": {"description": "Vegetation index", "source": "MODIS"},
    "elevation": {"unit": "m", "source": "SRTM"},
}


class DatasetSpec(BaseModel):
    """Everything that decides what a generated dataset looks like."""

    name: str
    org_units: int = 100
    years: int = 10
    periods: int | None = None
    period: str = "weekly"
    start_year: int = 2016
    columns: int = 10
    column_names: list[str] = []
    geometry: str = "point"
    corners: int = 800
    missing: float = 0.002
    seed: int | None = None  # None: a random seed, recorded in expected.json
    about: str = ""
    # Settings in the files' chap.* metadata.
    metadata: bool = True
    spec_version: str = SPEC_VERSION
    masked: list[tuple[str, str]] = []
    # Faults: data Chap rejects in part or in whole.
    covariate_gaps: int = 0
    drop_locations: int = 0
    duplicate_rows: int = 0
    text_column: str | None = None
    drop_time_period: bool = False
    not_parquet: bool = False
    geojson: bool = False


def org_unit_ids(n: int, seed: int) -> np.ndarray:
    """n unique DHIS2-style ids (11 characters, starting with a letter), sorted."""
    rng = np.random.default_rng(seed)
    letters = np.array(list(string.ascii_letters))
    alnum = np.array(list(string.ascii_letters + string.digits))
    ids: set[str] = set()
    while len(ids) < n:
        k = n - len(ids)
        chars = np.column_stack([rng.choice(letters, k), rng.choice(alnum, (k, 10))])
        ids.update("".join(row) for row in chars)
    return np.array(sorted(ids))


def period_strings(spec: DatasetSpec) -> tuple[list[str], int]:
    """Consecutive periods in Chap's form (2016W01, 201601), and the periods per year."""
    if spec.period == "weekly":
        n = spec.periods or round(spec.years * WEEKS_PER_YEAR)
        first_monday = pd.Timestamp.fromisocalendar(spec.start_year, 1, 1)
        dates = pd.date_range(first_monday, periods=n, freq="7D")
        return [f"{d.isocalendar().year}W{d.isocalendar().week:02d}" for d in dates], 52
    n = spec.periods or spec.years * 12
    return [p.strftime("%Y%m") for p in pd.period_range(f"{spec.start_year}-01", periods=n, freq="M")], 12


def column_names(spec: DatasetSpec) -> list[str]:
    """The value columns: the names given, or the first --columns of COLUMNS. The first is the target."""
    if spec.column_names:
        return spec.column_names
    names = list(COLUMNS)[: spec.columns]
    return names + [f"covariate_{i}" for i in range(len(names) + 1, spec.columns + 1)]


def batch(
    ids: np.ndarray, periods: list[str], per_year: int, names: list[str], missing: float, rng: np.random.Generator
) -> pa.Table:
    """Rows for a batch of org units, sorted by location then time_period.

    The values follow chapkit's TestDataGenerator (chapkit/data/generator.py), so models tested with
    either tool see the same kind of data: each org unit has its own seasonal phase, rainfall follows
    that season, temperature follows one regional cycle, and cases follow the season and rainfall.
    """
    n_ou, n_p = len(ids), len(periods)
    n = n_ou * n_p
    year_fraction = np.tile((np.arange(n_p) % per_year) / per_year, n_ou)

    def per_ou(low: float, high: float) -> np.ndarray:
        return np.repeat(rng.uniform(low, high, n_ou), n_p)

    def noise(half_width: float) -> np.ndarray:
        return rng.uniform(-half_width, half_width, n)

    season = np.sin(2 * np.pi * (year_fraction - per_ou(0, 1)))  # in [-1, 1], peaking at each org unit's own time
    rainfall = np.maximum(0.0, 150 + 130 * season + noise(25))  # mm per period
    temperature = 24 + 7 * np.sin(2 * np.pi * (year_fraction - 0.08)) + noise(1.5)  # degC, regional cycle

    def cases() -> np.ndarray:
        level = per_ou(20, 70) * (1 + per_ou(0.45, 0.7) * season) + 0.06 * rainfall + rng.normal(0, 4, n)
        result: np.ndarray = np.maximum(0, np.round(level))
        return result

    def seasonal_0_100(position: int, count: int) -> np.ndarray:
        """A smooth seasonal covariate in [0, 100] with its own phase, as chapkit's extra covariates."""
        phase = (position + 1) / (count + 1)
        result: np.ndarray = np.round(
            np.clip(50 + 35 * np.sin(2 * np.pi * (year_fraction - phase)) + noise(8), 0, 100), 2
        )
        return result

    extra = [name for name in names[1:] if name not in COLUMNS]
    values: dict[str, Callable[[], np.ndarray]] = {
        "disease_cases": cases,
        "population": lambda: np.repeat(rng.integers(50_000, 1_500_000, n_ou), n_p).astype(float),
        "rainfall": lambda: np.round(rainfall, 2),
        "mean_temperature": lambda: np.round(temperature, 2),
        "min_temperature": lambda: np.round(temperature - per_ou(4, 8), 2),
        "max_temperature": lambda: np.round(temperature + per_ou(4, 8), 2),
        "relative_humidity": lambda: np.round(np.clip(65 + 20 * season + noise(8), 0, 100), 2),
        "soil_moisture": lambda: np.round(np.clip(0.25 + 0.1 * season + noise(0.03), 0, 1), 3),
        "ndvi": lambda: np.round(np.clip(0.45 + 0.2 * season + noise(0.05), -1, 1), 3),
        "elevation": lambda: np.round(per_ou(0, 2_500)),
    }
    columns: dict[str, pa.Array] = {
        "location": pa.array(np.repeat(ids, n_p)),
        "time_period": pa.array(np.tile(periods, n_ou)),
    }
    for position, name in enumerate(names):
        if position == 0:
            column = cases()  # the first column is the target, whatever its name
        elif name in values:
            column = values[name]()
        else:
            column = seasonal_0_100(extra.index(name), len(extra))
        mask = rng.random(n) < missing if position == 0 and missing > 0 else None
        columns[name] = pa.array(column, type=pa.float64(), mask=mask)
    return pa.table(columns)


def with_faults(table: pa.Table, spec: DatasetSpec, n_periods: int, first: bool) -> pa.Table:
    """Apply the faults the spec asks for; gaps and duplicates go into the first batch only."""
    if first and spec.covariate_gaps:
        # One missing value of the last covariate in each of the first org units: Chap rejects those org units.
        name = table.column_names[-1]
        values = table.column(name).to_numpy(zero_copy_only=False).copy()
        values[[i * n_periods + min(5, n_periods - 1) for i in range(spec.covariate_gaps)]] = np.nan
        index = table.schema.get_field_index(name)
        table = table.set_column(index, name, pa.array(values, mask=np.isnan(values)))
    if first and spec.duplicate_rows:
        table = pa.concat_tables([table, table.slice(0, spec.duplicate_rows)])
    if spec.text_column:
        table = table.append_column(spec.text_column, pa.array(["district-1"] * table.num_rows))
    if spec.drop_time_period:
        table = table.drop_columns(["time_period"])
    return table


def chap_keys(spec: DatasetSpec, names: list[str]) -> dict[bytes, bytes]:
    keys = {"chap.spec_version": spec.spec_version}
    if spec.metadata:
        dataset: dict[str, Any] = {"name": spec.name, "target_column": names[0]}
        if spec.masked:
            dataset["masked_ranges"] = [{"start": s, "end": e, "name": "masked"} for s, e in spec.masked]
        keys["chap.dataset"] = json.dumps(dataset)
        keys["chap.columns"] = json.dumps({c: COLUMNS.get(c, {"description": "Synthetic covariate"}) for c in names})
        keys["chap.provenance"] = json.dumps({"from": "chap-test-data", "license": "CC0-1.0", "note": "synthetic"})
    return {k.encode(): v.encode() for k, v in keys.items()}


def _room(t: np.ndarray, apex: float, height: float) -> np.ndarray:
    """Height at t of a triangle on the base [0, 1] whose apex is above `apex` at `height`."""
    rise = t / apex if apex > 1e-9 else np.full_like(t, np.inf)
    fall = (1 - t) / (1 - apex) if apex < 1 - 1e-9 else np.full_like(t, np.inf)
    result: np.ndarray = height * np.minimum(np.minimum(rise, fall), 1.0)
    return result


def jagged_areas(n: int, corners: int, rng: np.random.Generator) -> tuple[np.ndarray, Any]:
    """n areas that tile a country-like map: no gaps, no overlaps, jagged shared borders.

    The areas start as Voronoi cells of a jittered grid, and the country is an irregular blob of them. Every border between two neighbours, and
    every piece of the outline, is then drawn once as a jagged line (a Brownian bridge, so its ends
    stay put) and shared by both sides. Each line stays inside the triangles from the border to the
    two centre points; those triangles never overlap, so borders never cross. Borders get about
    `corners` points per area, and the jaggedness grows slowly with the points as real borders do:
    the border is 1.7 times the perimeter of a circle of the same area at 800 points (chap-core's
    example boundaries: 1.4 to 1.9). Returns the centre points and the polygons.
    """
    # Tile about 70% more areas than needed on a grid, then keep the n whose centres fall inside an
    # irregular blob: the country. Its outline is then made of ordinary shared borders, so it is as
    # jagged and irregular as the borders inside.
    total = max(n, int(np.ceil(n * 1.7)) + 4)
    side = int(np.ceil(np.sqrt(total)))
    rows = int(np.ceil(total / side))
    cell = min(0.8, 18 / np.sqrt(n))
    origin_lon, origin_lat = 36.8 - side * cell / 2, -1.3 - rows * cell / 2
    grid = np.stack(
        [
            origin_lon + (np.arange(total) % side + 0.5 + rng.uniform(-0.3, 0.3, total)) * cell,
            origin_lat + (np.arange(total) // side + 0.5 + rng.uniform(-0.3, 0.3, total)) * cell,
        ],
        axis=1,
    )
    centre = np.array([origin_lon + side * cell / 2, origin_lat + rows * cell / 2])
    angle = np.arctan2(grid[:, 1] - centre[1], grid[:, 0] - centre[0])
    phase = rng.uniform(0, 2 * np.pi, 3)
    reach = 1 + 0.25 * sum(np.sin(h * angle + phase[i]) for i, h in enumerate((2, 3, 4))) / 3
    chosen = np.sort(np.argsort(np.linalg.norm(grid - centre, axis=1) / reach)[:n])
    sites = grid
    bounds = shapely.box(origin_lon, origin_lat, origin_lon + side * cell, origin_lat + rows * cell)
    cells = shapely.intersection(
        shapely.get_parts(shapely.voronoi_polygons(shapely.multipoints(sites), extend_to=bounds, ordered=True)),
        bounds,
    )
    # Each straight border once, with the areas on its sides (one for the outline, two inside).
    rings = []
    sides: dict[tuple[tuple[float, float], tuple[float, float]], list[int]] = {}
    for i, polygon in enumerate(cells):
        ring = np.round(shapely.get_coordinates(shapely.get_exterior_ring(polygon)), 9)
        ring = ring[np.r_[True, np.any(np.diff(ring, axis=0) != 0, axis=1)]]  # no zero-length borders
        rings.append(ring)
        for a, b in itertools.pairwise(ring):
            key = (tuple(a), tuple(b)) if tuple(a) < tuple(b) else (tuple(b), tuple(a))
            sides.setdefault(key, []).append(i)  # type: ignore[arg-type]
    per_degree = corners / (4 * cell)
    amplitude = 0.21 * (corners / 800) ** -0.3
    lines = {}
    for key, owners in sides.items():
        a, b = np.array(key[0]), np.array(key[1])
        length = float(np.linalg.norm(b - a))
        direction = (b - a) / length
        normal = np.array([-direction[1], direction[0]])
        t = np.linspace(0, 1, max(2, round(length * per_degree)))
        offset = np.zeros_like(t)
        if len(t) > 2:
            walk = np.concatenate([[0.0], np.cumsum(rng.normal(0, 1, len(t) - 1))])
            bridge = walk - t * walk[-1]
            bridge /= max(1e-12, float(np.abs(bridge).max()))
            room = {}
            for owner in owners:
                relative = sites[owner] - a
                across = float(relative @ normal)
                room[np.sign(across)] = _room(t, float(relative @ direction) / length, abs(across))
            if len(owners) == 1:  # the outline: as much room outside, with the apex kept over the border
                ((inside, _),) = room.items()
                relative = sites[owners[0]] - a
                apex = float(np.clip(relative @ direction / length, 0.2, 0.8))
                room[-inside] = _room(t, apex, abs(float(relative @ normal)))
            zero = np.zeros_like(t)
            offset = amplitude * bridge * np.where(bridge >= 0, room.get(1.0, zero), room.get(-1.0, zero))
        lines[key] = a + t[:, None] * (b - a) + offset[:, None] * normal
    polygons = np.empty(n, dtype=object)
    for position, i in enumerate(chosen):
        ring = rings[i]
        pieces = []
        for a, b in itertools.pairwise(ring):
            forward = (tuple(a), tuple(b))
            line = lines[forward] if forward in lines else lines[(tuple(b), tuple(a))][::-1]  # type: ignore[index]
            pieces.append(line[:-1])
        polygons[position] = shapely.Polygon(np.concatenate(pieces))
    return sites[chosen], polygons


def facility_points(n: int, rng: np.random.Generator, per_district: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """n facilities spread over a country of districts, clustered around a few towns per district.

    The districts are jagged_areas, one per `per_district` facilities, and each facility lies inside
    its own district, so the `parent` column matches the map. Returns the points and their district.
    """
    district_count = max(1, int(np.ceil(n / per_district)))
    _, districts = jagged_areas(district_count, 64, rng)
    district = np.arange(n) // per_district
    bounds = shapely.bounds(districts)
    x = np.empty(n)
    y = np.empty(n)
    for d in range(district_count):
        members = np.flatnonzero(district == d)
        min_x, min_y, max_x, max_y = bounds[d]
        spread = 0.15 * min(max_x - min_x, max_y - min_y)
        towns = _inside(districts[d], 3, bounds[d], rng)
        town = towns[rng.integers(0, len(towns), len(members))]
        points = town + rng.normal(0, spread, (len(members), 2))
        outside = ~shapely.contains_xy(districts[d], points[:, 0], points[:, 1])
        points[outside] = _inside(districts[d], int(outside.sum()), bounds[d], rng)  # the far strays, anywhere inside
        x[members], y[members] = points[:, 0], points[:, 1]
    return np.stack([x, y], axis=1), district


def _inside(polygon: Any, count: int, bounds: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """count random points inside polygon, by drawing in its bounding box and keeping those inside."""
    found = np.empty((0, 2))
    while len(found) < count:
        draw = rng.uniform(bounds[:2], bounds[2:], (max(8, 2 * (count - len(found))), 2))
        found = np.concatenate([found, draw[shapely.contains_xy(polygon, draw[:, 0], draw[:, 1])]])
    return found[:count]


def locations(ids: np.ndarray, corners: int | None, seed: int) -> gpd.GeoDataFrame:
    """Org units near Nairobi on a country-like map, about 0.8 degrees apart (as chapkit's generator).

    With corners, each org unit is an area with a jagged border of that many points (a district; see
    jagged_areas). Without, it is a facility point, clustered around towns inside districts of 50
    (see facility_points). Either way the parent column holds one parent id per 50 org units.
    """
    rng = np.random.default_rng(seed)
    n = len(ids)
    geometry: Any
    if corners:
        _, geometry = jagged_areas(n, corners, rng)
    else:
        points, _ = facility_points(n, rng)
        geometry = shapely.points(points)
    parents = org_unit_ids(max(1, int(np.ceil(n / 50))), seed + 1)
    return gpd.GeoDataFrame(
        {
            "location": ids,
            "name": [f"Org unit {i + 1}" for i in range(n)],
            "parent": parents[np.arange(n) // 50],
            "level": 3 if corners else 5,
        },
        geometry=geometry,
        crs=4326,
    )


def expected_answer(spec: DatasetSpec, rows: int, observations: Path, locations_path: Path) -> Expected:
    """The dry-run answer Chap's Phase 1 endpoint should give for these files."""
    sizes = [observations.stat().st_size, locations_path.stat().st_size]
    if sum(sizes) > MAX_UPLOAD_BYTES or max(sizes) > MAX_FILE_BYTES:
        return Expected(http=413, detail="larger than")
    if spec.not_parquet:
        return Expected(http=422, detail="not a Parquet file")
    if rows > MAX_ROWS:
        return Expected(http=422, detail=f"at most {MAX_ROWS} are accepted")
    if spec.spec_version != SPEC_VERSION:
        return Expected(http=422, detail="this Chap reads version")
    if spec.drop_time_period:
        return Expected(http=422, detail="no time_period column")
    if spec.text_column:
        return Expected(http=422, detail=f"not numeric: {spec.text_column}")
    if spec.duplicate_rows:
        return Expected(http=422, detail="more than one row")
    rejected = spec.covariate_gaps + spec.drop_locations
    return Expected(http=200, imported_count=spec.org_units - rejected, rejected=rejected)


def build(spec: DatasetSpec, directory: Path, progress: Callable[[int, int], None] | None = None) -> Expected:
    """Write observations, locations and expected.json into directory; returns what expected.json says."""
    names = column_names(spec)
    if len(set(names)) != len(names) or {"location", "time_period"} & set(names):
        raise ValueError("column names must be unique and not location or time_period")
    if spec.covariate_gaps and len(names) < 2:
        raise ValueError("covariate gaps go into the last covariate, so there must be at least 2 columns")
    if spec.geometry == "polygon" and spec.corners < 3:
        raise ValueError("a polygon needs at least 3 points")
    if spec.covariate_gaps + spec.drop_locations > spec.org_units:
        raise ValueError("more org units rejected than there are")
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir(parents=True)
    periods, per_year = period_strings(spec)
    seed = spec.seed if spec.seed is not None else secrets.randbelow(2**31)
    ids = org_unit_ids(spec.org_units, seed)
    rng = np.random.default_rng(seed)
    per_batch = max(1, ROWS_PER_BATCH // len(periods))
    observations = directory / "observations.parquet"

    def batches() -> Any:
        for start in range(0, len(ids), per_batch):
            table = batch(ids[start : start + per_batch], periods, per_year, names, spec.missing, rng)
            yield with_faults(table, spec, len(periods), first=start == 0)
            if progress:
                progress(min(start + per_batch, len(ids)), len(ids))

    rows = 0
    if spec.not_parquet:
        # A CSV file named observations.parquet: a mistake Chap must catch from the first bytes.
        table = next(batches())
        pacsv.write_csv(table.slice(0, 10), observations)
        rows = table.num_rows
    else:
        writer: pq.ParquetWriter | None = None
        for table in batches():
            if writer is None:
                schema = table.schema.with_metadata(chap_keys(spec, names))
                writer = pq.ParquetWriter(observations, schema, compression="zstd", write_page_index=True)
            writer.write_table(table.cast(schema), row_group_size=ROW_GROUP_SIZE)
            rows += table.num_rows
        assert writer is not None
        writer.close()

    frame = locations(ids, spec.corners if spec.geometry == "polygon" else None, seed)
    if spec.drop_locations:
        frame = frame.iloc[: len(frame) - spec.drop_locations]
    if spec.geojson:
        locations_path = directory / "locations.geojson"
        locations_path.write_text(frame.set_index("location").to_json(drop_id=False))
    else:
        locations_path = directory / "locations.parquet"
        write_locations(frame, locations_path)

    shape = f"jagged polygons of {spec.corners} points" if spec.geometry == "polygon" else "points"
    about = spec.about or (
        f"{spec.org_units:,} org units x {len(periods)} {spec.period} periods "
        f"({periods[0]} to {periods[-1]}), {len(names)} value columns, {shape}"
    )
    expected = expected_answer(spec, rows, observations, locations_path).model_copy(
        update={"about": about, "seed": seed, "rows": rows, "values": rows * len(names)}
    )
    expected.write(directory)
    return expected
