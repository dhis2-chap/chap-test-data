import json
from pathlib import Path

import pyarrow.parquet as pq
from typer.testing import CliRunner

from chap_test_data.cli import app
from chap_test_data.client import Answer, matches
from chap_test_data.export import export
from chap_test_data.files import Expected
from chap_test_data.generate import DatasetSpec, build

runner = CliRunner()


def dataset(tmp_path: Path) -> Path:
    directory = tmp_path / "small"
    build(
        DatasetSpec(name="small", org_units=3, periods=4, period="monthly", columns=3, seed=1, missing=0.2), directory
    )
    return directory


def test_json_columns_holds_every_value_of_the_parquet_file(tmp_path):
    directory = dataset(tmp_path)
    body = json.loads(export(directory, "json-columns")[0].read_text())
    table = pq.read_table(directory / "observations.parquet")
    columns = body["providedDataColumns"]
    assert columns["orgUnit"] == table.column("location").to_pylist()
    assert columns["period"] == table.column("time_period").to_pylist()
    assert columns["values"]["disease_cases"] == table.column("disease_cases").to_pylist()  # nulls stay null
    assert body["name"] == "small" and body["targetColumn"] == "disease_cases"
    assert body["dataSources"] == [
        {"covariate": "disease_cases", "dataElementId": "DeCases0001"},
        {"covariate": "population", "dataElementId": "DePopulat01"},
    ]
    assert len(body["geojson"]["features"]) == 3


def test_json_rows_has_one_object_per_value(tmp_path):
    directory = dataset(tmp_path)
    body = json.loads(export(directory, "json-rows")[0].read_text())
    assert len(body["providedData"]) == 3 * 4 * 3
    assert set(body["providedData"][0]) == {"orgUnit", "period", "featureName", "value"}


def test_csv_puts_time_period_first_and_writes_geojson(tmp_path):
    directory = dataset(tmp_path)
    files = export(directory, "csv", tmp_path / "csv")
    assert [f.name for f in files] == ["observations.csv", "locations.geojson"]
    header = files[0].read_text().splitlines()[0]
    assert header == '"time_period","location","disease_cases","population","rainfall"'


def test_generate_command_writes_the_folder_and_the_formats(tmp_path):
    result = runner.invoke(
        app,
        ["generate", "cli", "--org-units", "2", "--periods", "3", "--seed", "42", "--out", str(tmp_path)]
        + ["--format", "csv", "--format", "json-columns"],
    )
    assert result.exit_code == 0, result.output
    assert "(seed 42)" in result.output
    names = {p.name for p in (tmp_path / "cli").iterdir()}
    assert {"observations.parquet", "locations.parquet", "expected.json", "observations.csv"} <= names
    assert "make-dataset.columns.json" in names


def test_generate_command_needs_a_name():
    assert runner.invoke(app, ["generate"]).exit_code != 0


def test_time_checks_command_reports_each_check(tmp_path):
    result = runner.invoke(app, ["time-checks", str(dataset(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "duplicate (location, time_period)" in result.output and "all checks" in result.output


def test_an_answer_matches_its_expected_json():
    imported = Expected(http=200, imported_count=17, rejected=3)
    assert matches(imported, Answer(http=200, seconds=0, bytes=0, body={"importedCount": 17, "rejected": [1, 2, 3]}))
    assert not matches(imported, Answer(http=200, seconds=0, bytes=0, body={"importedCount": 20, "rejected": []}))
    refused = Expected(http=422, detail="not a Parquet file")
    assert matches(refused, Answer(http=422, seconds=0, bytes=0, body={"detail": "observations is not a Parquet file"}))
    assert not matches(refused, Answer(http=413, seconds=0, bytes=0, body={"detail": "too large"}))
