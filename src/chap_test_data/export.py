"""The same dataset in other formats, read from its Parquet files in batches so memory stays small.

csv           observations.csv (time_period, location, values) and locations.geojson
geojson       locations.geojson next to locations.parquet
json-columns  make-dataset.columns.json: the make-dataset body with providedDataColumns (the Modeling App)
json-rows     make-dataset.rows.json: the make-dataset body with providedData, one object per value
"""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO

import geopandas as gpd
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

FORMATS = ("parquet", "csv", "geojson", "json-columns", "json-rows")
BATCH_ROWS = 500_000


def output_files(fmt: str) -> list[str]:
    return {
        "parquet": ["observations.parquet", "locations.parquet"],
        "csv": ["observations.csv", "locations.geojson"],
        "geojson": ["locations.geojson"],
        "json-columns": ["make-dataset.columns.json"],
        "json-rows": ["make-dataset.rows.json"],
    }[fmt]


def chap_metadata(observations: Path) -> tuple[dict, dict]:
    metadata = pq.read_schema(observations).metadata or {}
    raw = {k.decode(): v.decode() for k, v in metadata.items() if k.startswith(b"chap.")}
    dataset: dict = json.loads(raw.get("chap.dataset", "{}"))
    columns: dict = json.loads(raw.get("chap.columns", "{}"))
    return dataset, columns


def geojson_text(directory: Path) -> str:
    """The locations as a GeoJSON FeatureCollection, with the location id as each feature's id."""
    if (directory / "locations.geojson").exists():
        return (directory / "locations.geojson").read_text()
    frame = gpd.read_parquet(directory / "locations.parquet").set_index("location")
    text: str = frame.to_json(drop_id=False)
    return text


def write_geojson(directory: Path, out: Path) -> None:
    target = out / "locations.geojson"
    if target.exists() and target.resolve() == (directory / "locations.geojson").resolve():
        return  # the dataset's own GeoJSON locations
    target.write_text(geojson_text(directory))


def batches(observations: Path, columns: list[str] | None = None) -> Iterator[pa.RecordBatch]:
    yield from pq.ParquetFile(observations).iter_batches(batch_size=BATCH_ROWS, columns=columns)


def write_csv(directory: Path, out: Path) -> None:
    """observations.csv in the column order models read (time_period, location, values), plus GeoJSON."""
    observations = directory / "observations.parquet"
    names = pq.read_schema(observations).names
    order = [c for c in ("time_period", "location") if c in names] + [
        c for c in names if c not in ("time_period", "location")
    ]
    with pacsv.CSVWriter(
        out / "observations.csv", pa.schema([pq.read_schema(observations).field(c) for c in order])
    ) as w:
        for batch in batches(observations, order):
            w.write_batch(batch)
    write_geojson(directory, out)


def _json_list(f: TextIO, chunks: Iterator[list[Any]]) -> None:
    """Write one JSON array from chunks of values, without holding the whole array."""
    f.write("[")
    first = True
    for chunk in chunks:
        if not chunk:
            continue
        if not first:
            f.write(", ")
        f.write(json.dumps(chunk, allow_nan=False)[1:-1])
        first = False
    f.write("]")


def _common(directory: Path) -> dict:
    """The make-dataset settings, taken from the files' chap.* metadata as Chap would."""
    dataset, columns = chap_metadata(directory / "observations.parquet")
    return {
        "name": dataset.get("name") or directory.name,
        "targetColumn": dataset.get("target_column", "disease_cases"),
        "maskedRanges": dataset.get("masked_ranges", []),
        "dataSources": [
            {"covariate": name, "dataElementId": info["dhis2_data_element"]}
            for name, info in columns.items()
            if info.get("dhis2_data_element")
        ],
    }


def write_make_dataset(directory: Path, out: Path, form: str) -> Path:
    """The make-dataset JSON body: form "columns" (providedDataColumns) or "rows" (providedData)."""
    observations = directory / "observations.parquet"
    names = pq.read_schema(observations).names
    if "location" not in names or "time_period" not in names:
        raise ValueError("a make-dataset body needs location and time_period columns")
    features = [c for c in names if c not in ("location", "time_period")]
    path = out / f"make-dataset.{form}.json"
    common = json.dumps(_common(directory))[:-1]  # keep the object open for the data fields
    with path.open("w") as f:
        f.write(f'{common}, "geojson": {geojson_text(directory)}, ')
        if form == "columns":
            f.write('"providedDataColumns": {"orgUnit": ')
            _json_list(f, (b.column(0).to_pylist() for b in batches(observations, ["location"])))
            f.write(', "period": ')
            _json_list(f, (b.column(0).to_pylist() for b in batches(observations, ["time_period"])))
            f.write(', "values": {')
            for i, name in enumerate(features):
                f.write(("" if i == 0 else ", ") + json.dumps(name) + ": ")
                _json_list(f, (b.column(0).to_pylist() for b in batches(observations, [name])))
            f.write("}}}")
        else:
            f.write('"providedData": ')

            def rows() -> Iterator[list[dict]]:
                for name in features:
                    for b in batches(observations, ["location", "time_period", name]):
                        yield [
                            {"orgUnit": o, "period": p, "featureName": name, "value": v}
                            for o, p, v in zip(*(b.column(i).to_pylist() for i in range(3)), strict=True)
                        ]

            _json_list(f, rows())
            f.write("}")
    return path


def export(directory: Path, fmt: str, out: Path | None = None) -> list[Path]:
    """Write the dataset in directory in another format; returns the files written."""
    out = out or directory
    out.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        for name in output_files("parquet"):
            if out != directory and (directory / name).exists():
                shutil.copy(directory / name, out / name)
    elif fmt == "csv":
        write_csv(directory, out)
    elif fmt == "geojson":
        write_geojson(directory, out)
    elif fmt in ("json-columns", "json-rows"):
        write_make_dataset(directory, out, fmt.removeprefix("json-"))
    else:
        raise ValueError(f"unknown format {fmt}; known: {', '.join(FORMATS)}")
    return [out / name for name in output_files(fmt) if (out / name).exists()]
