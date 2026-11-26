"""The chap-test-data command line."""

import json
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from chap_test_data import compare as comparison
from chap_test_data.checks import run_checks
from chap_test_data.client import Target, matches, summary, upload_files, wait_for_job
from chap_test_data.export import export
from chap_test_data.files import Expected
from chap_test_data.generate import DatasetSpec, build

app = typer.Typer(
    help="Test data and upload tools for Chap's Parquet dataset upload (POST /v1/crud/datasets/files).",
    no_args_is_help=True,
    add_completion=False,
)

DATASETS = Path("datasets")
RESULTS = Path("results")
DEFAULT = Target()


class Format(StrEnum):
    parquet = "parquet"
    csv = "csv"
    geojson = "geojson"
    json_columns = "json-columns"
    json_rows = "json-rows"


class Geometry(StrEnum):
    point = "point"
    polygon = "polygon"


class Period(StrEnum):
    weekly = "weekly"
    monthly = "monthly"


Dhis2 = Annotated[bool, typer.Option("--dhis2", help="Go through the DHIS2 route, as the Modeling App would.")]
DryRun = Annotated[bool, typer.Option("--dry-run", help="Validate only (dryRun=true); nothing is imported.")]


class State:
    target = Target()


@app.callback()
def connection(
    chap_url: Annotated[str, typer.Option(envvar="CHAP_URL", help="Chap's API.")] = DEFAULT.chap_url,
    chap_token: Annotated[
        str | None, typer.Option(envvar="CHAP_API_TOKEN", help="Bearer token for Chap, if it needs one.")
    ] = None,
    dhis2_url: Annotated[str, typer.Option(envvar="DHIS2_URL", help="DHIS2, used with --dhis2.")] = DEFAULT.dhis2_url,
    dhis2_user: Annotated[str, typer.Option(envvar="DHIS2_USER")] = DEFAULT.dhis2_user,
    dhis2_password: Annotated[str, typer.Option(envvar="DHIS2_PASSWORD")] = DEFAULT.dhis2_password,
    route_code: Annotated[
        str, typer.Option(envvar="ROUTE_CODE", help="The route's code in DHIS2.")
    ] = DEFAULT.route_code,
) -> None:
    """Connection settings apply to upload, check and compare; each can also come from the environment."""
    State.target = Target(
        chap_url=chap_url,
        chap_token=chap_token,
        dhis2_url=dhis2_url,
        dhis2_user=dhis2_user,
        dhis2_password=dhis2_password,
        route_code=route_code,
    )


def target(dhis2: bool) -> Target:
    State.target.dhis2 = dhis2
    return State.target


@app.command()
def generate(
    name: Annotated[str, typer.Argument(help="Dataset name; the folder under --out.")],
    org_units: Annotated[int, typer.Option(help="Number of org units.")] = 100,
    years: Annotated[int, typer.Option(help="Years of data.")] = 10,
    periods: Annotated[int | None, typer.Option(help="Number of periods, instead of --years.")] = None,
    period: Annotated[Period, typer.Option(help="Period type.")] = Period.weekly,
    start_year: Annotated[int, typer.Option(help="First year of data.")] = 2016,
    columns: Annotated[
        int,
        typer.Option(
            help="Value columns, in this order: disease_cases, population, rainfall, mean_temperature, "
            "min_temperature, max_temperature, relative_humidity, soil_moisture, ndvi, elevation; "
            "more adds covariate_11, ..."
        ),
    ] = 10,
    column: Annotated[
        list[str] | None,
        typer.Option(
            help="Name the value columns instead, in order; repeatable. The first is the target. "
            "Names from the --columns list get realistic values, others a generic covariate."
        ),
    ] = None,
    geometry: Annotated[Geometry, typer.Option(help="Locations as points (facilities) or polygons (areas).")] = (
        Geometry.point
    ),
    corners: Annotated[
        int, typer.Option(help="Corners of each polygon, for --geometry polygon: 3 is a triangle, 64 nearly round.")
    ] = 64,
    missing: Annotated[float, typer.Option(help="Share of missing disease_cases values.")] = 0.002,
    seed: Annotated[
        int | None,
        typer.Option(help="Random seed for the same files every time (default: random, recorded in expected.json)."),
    ] = None,
    about: Annotated[str, typer.Option(help="Description for expected.json (default: from the settings).")] = "",
    geojson: Annotated[bool, typer.Option("--geojson", help="Write locations as GeoJSON, not GeoParquet.")] = False,
    metadata: Annotated[
        bool, typer.Option(help="Write the chap.* settings; without, Chap names it after the file.")
    ] = True,
    masked: Annotated[
        list[str] | None, typer.Option(help="Masked range of the target, START:END (e.g. 201801:201803); repeatable.")
    ] = None,
    spec_version: Annotated[str, typer.Option(help="chap.spec_version; Chap refuses anything but 1.")] = "1",
    covariate_gaps: Annotated[
        int, typer.Option(help="Org units missing one rainfall value; Chap rejects those org units.")
    ] = 0,
    drop_locations: Annotated[
        int, typer.Option(help="Org units left out of the locations file; Chap rejects them.")
    ] = 0,
    duplicate_rows: Annotated[int, typer.Option(help="Rows written twice; Chap refuses the upload.")] = 0,
    text_column: Annotated[
        str | None, typer.Option(help="Add a text column with this name; Chap refuses the upload.")
    ] = None,
    drop_time_period: Annotated[
        bool, typer.Option("--drop-time-period", help="Leave out time_period; Chap refuses the upload.")
    ] = False,
    not_parquet: Annotated[
        bool, typer.Option("--not-parquet", help="Write a CSV file named observations.parquet; Chap refuses it.")
    ] = False,
    formats: Annotated[
        list[Format] | None,
        typer.Option(
            "--format",
            help="Also write the dataset as: csv (observations.csv and locations.geojson), geojson "
            "(locations.geojson), json-columns or json-rows (make-dataset bodies, as the Modeling App sends "
            "today). Repeatable; Parquet is always written.",
        ),
    ] = None,
    out: Annotated[Path, typer.Option(help="Parent folder.")] = DATASETS,
) -> None:
    """Write a synthetic dataset of any size, with the answer Chap should give in expected.json.

    The observations are written in batches of org units, so memory stays small even for tens of
    millions of rows.
    """
    ranges = []
    for item in masked or []:
        start, sep, end = item.partition(":")
        if not sep:
            raise typer.BadParameter(f"--masked takes START:END, got {item}")
        ranges.append((start, end))
    spec = DatasetSpec(
        name=name,
        org_units=org_units,
        years=years,
        periods=periods,
        period=period.value,
        start_year=start_year,
        columns=columns,
        column_names=column or [],
        geometry=geometry.value,
        corners=corners,
        missing=missing,
        seed=seed,
        about=about,
        metadata=metadata,
        spec_version=spec_version,
        masked=ranges,
        covariate_gaps=covariate_gaps,
        drop_locations=drop_locations,
        duplicate_rows=duplicate_rows,
        text_column=text_column,
        drop_time_period=drop_time_period,
        not_parquet=not_parquet,
        geojson=geojson,
    )
    directory = out / name

    def progress(done: int, total: int) -> None:
        if total > 1_000:
            typer.echo(f"\r{done:,} of {total:,} org units", nl=False, err=True)

    extra = [f.value for f in formats or [] if f is not Format.parquet]
    if extra and not_parquet:
        raise typer.BadParameter("--format needs real Parquet files to convert; leave out --not-parquet")
    try:
        expected = build(spec, directory, progress)
        for fmt in extra:
            export(directory, fmt)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    sizes = ", ".join(
        f"{p.name} {p.stat().st_size / 1e6:,.2f} MB" for p in sorted(directory.iterdir()) if p.suffix != ".json"
    )
    answer = f"{expected.http} {expected.detail}" if expected.detail else expected.summary()
    typer.echo(f"{name:<34} {expected.rows or 0:>12,} rows  {sizes}  -> {answer}  (seed {expected.seed})")


@app.command()
def upload(
    directory: Annotated[Path, typer.Argument(help="A dataset folder, such as datasets/03-facility-points.")],
    dhis2: Dhis2 = False,
    dry_run: DryRun = False,
    wait: Annotated[bool, typer.Option(help="Wait for the import job and report how it ended.")] = False,
) -> None:
    """Upload one dataset folder."""
    answer = upload_files(target(dhis2), directory, dry_run)
    typer.echo(json.dumps(answer.body, indent=2) if not isinstance(answer.body, str) else answer.body)
    typer.echo(f"HTTP {answer.http} in {answer.seconds:.2f} s, {answer.bytes / 1e6:,.2f} MB sent")
    job = answer.body.get("id") if isinstance(answer.body, dict) else None
    if wait and job and not dry_run:
        status, seconds = wait_for_job(State.target, job)
        typer.echo(f"job {job}: {status}" + (f" in {seconds:.1f} s" if seconds is not None else ""))
    if answer.http != 200:
        raise typer.Exit(1)


@app.command()
def check(
    root: Annotated[Path, typer.Argument(help="Folder of dataset folders.")] = DATASETS,
    dhis2: Dhis2 = False,
) -> None:
    """Dry-run every dataset under ROOT and compare Chap's answer with its expected.json."""
    failed = 0
    typer.echo(f"{'dataset':<34} {'result':<6} {'expected':<38} got")
    for directory in sorted(p for p in root.iterdir() if (p / "expected.json").exists()):
        expected = Expected.read(directory)
        answer = upload_files(target(dhis2), directory, dry_run=True)
        ok = matches(expected, answer)
        failed += not ok
        result = "ok" if ok else "FAIL"
        typer.echo(f"{directory.name:<34} {result:<6} {expected.summary():<38} {summary(answer)}")
    typer.echo("\nall datasets gave the expected answer" if not failed else f"\n{failed} dataset(s) differ")
    if failed:
        raise typer.Exit(1)


@app.command()
def compare(
    datasets: Annotated[list[str] | None, typer.Argument(help="Dataset names under --root.")] = None,
    all_: Annotated[bool, typer.Option("--all", help="Every dataset expected to import (HTTP 200).")] = False,
    root: Annotated[Path, typer.Option(help="Folder of dataset folders.")] = DATASETS,
    dhis2: Dhis2 = False,
    dry_run: DryRun = False,
    wait: Annotated[bool, typer.Option(help="After an import, wait for the job and report the worker's time.")] = False,
    repeat: Annotated[int, typer.Option(help="Upload each format N times and report the median time.")] = 1,
    results: Annotated[Path, typer.Option(help="Markdown file the table is appended to.")] = RESULTS / "compare.md",
) -> None:
    """Upload datasets as Parquet and as today's two JSON bodies, and compare size and time."""
    names = list(datasets or [])
    if all_:
        names = sorted(
            d.name for d in root.iterdir() if (d / "expected.json").exists() and Expected.read(d).http == 200
        )
    if not names:
        raise typer.BadParameter("name datasets or pass --all")
    lines = [comparison.header(target(dhis2), dry_run)]
    typer.echo(lines[0])
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            for line in comparison.compare_dataset(State.target, root / name, Path(tmp), dry_run, wait, repeat):
                lines.append(line)
                typer.echo(line)
    results.parent.mkdir(parents=True, exist_ok=True)
    with results.open("a") as f:
        f.write("\n".join(lines) + "\n")


@app.command("time-checks")
def time_checks(
    datasets: Annotated[
        list[Path], typer.Argument(help="Dataset folders, such as datasets/23-org-units-100k-weekly-10y.")
    ],
    memory_limit: Annotated[str, typer.Option(help="DuckDB memory limit; above it, DuckDB spills to disk.")] = "1GB",
) -> None:
    """Time the checks a Phase 2 import would run, on the files themselves and without Chap.

    Uses DuckDB to measure; which engine Chap uses for this is not decided. Peak memory is for the
    whole process.
    """
    for directory in datasets:
        rows, results, peak_mb = run_checks(directory, memory_limit)
        typer.echo(f"{directory.name}: {rows:,} rows")
        for result in results:
            typer.echo(f"  {result.name:<40} {result.seconds:7.2f} s  ({result.found:,} found)")
        total = sum(r.seconds for r in results)
        typer.echo(f"  {'all checks':<40} {total:7.2f} s, peak memory {peak_mb:,.0f} MB")
