"""The chap-test-data command line."""

import sys
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from chap_test_data import compare as comparison
from chap_test_data import ui
from chap_test_data.checks import run_checks
from chap_test_data.client import Target, matches, upload_files, wait_for_job
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

# The groups generate's options are shown in, as in the docs.
SIZE = "Size and time"
COLUMNS = "Value columns"
LOCATIONS = "Locations"
FORMATS = "Other formats"
SETTINGS = "Settings in the file"
REJECTED = "Org units Chap must reject"
REFUSED = "Files Chap must refuse"
REPRODUCE = "Reproducing a dataset"


class CompareFormat(StrEnum):
    parquet = "parquet"
    json_columns = "json-columns"
    json_rows = "json-rows"


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


Dhis2 = Annotated[
    bool,
    typer.Option(
        "--dhis2",
        help="Send the upload through DHIS2's route to Chap (see --dhis2-url and --route-code), as the Modeling "
        "App does, instead of straight to Chap.",
    ),
]
DryRun = Annotated[
    bool,
    typer.Option(
        "--dry-run",
        help="Only check: Chap answers what it would import and reject, and stores nothing (dryRun=true).",
    ),
]
Bandwidth = Annotated[
    float | None,
    typer.Option(
        help="Send no faster than this many Mbit/s, to time the upload over a slow link (default: as fast as "
        "possible). The time reported includes sending. It adds no delay; scripts/upload-slow-link.sh adds both."
    ),
]


class State:
    target = Target()


@app.callback()
def connection(
    chap_url: Annotated[str, typer.Option(envvar="CHAP_URL", help="Where Chap's API answers.")] = DEFAULT.chap_url,
    chap_token: Annotated[
        str | None, typer.Option(envvar="CHAP_API_TOKEN", help="Chap's API token, if Chap is set up to require one.")
    ] = None,
    dhis2_url: Annotated[
        str, typer.Option(envvar="DHIS2_URL", help="Where DHIS2 answers, for --dhis2.")
    ] = DEFAULT.dhis2_url,
    dhis2_user: Annotated[
        str, typer.Option(envvar="DHIS2_USER", help="DHIS2 user name, for --dhis2.")
    ] = DEFAULT.dhis2_user,
    dhis2_password: Annotated[
        str, typer.Option(envvar="DHIS2_PASSWORD", help="DHIS2 password, for --dhis2.")
    ] = DEFAULT.dhis2_password,
    route_code: Annotated[
        str, typer.Option(envvar="ROUTE_CODE", help="The code of the DHIS2 route that forwards to Chap, for --dhis2.")
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


def target(dhis2: bool, bandwidth: float | None = None) -> Target:
    State.target.dhis2 = dhis2
    State.target.bandwidth = bandwidth
    return State.target


@app.command()
def generate(
    name: Annotated[str, typer.Argument(help="The dataset's name: the folder it is written to, under --out.")],
    org_units: Annotated[
        int, typer.Option(help="How many org units (districts or facilities).", rich_help_panel=SIZE)
    ] = 100,
    period: Annotated[
        Period,
        typer.Option(
            help="How often there is a value: weekly (periods like 2016W01) or monthly (201601).",
            rich_help_panel=SIZE,
        ),
    ] = Period.weekly,
    years: Annotated[int, typer.Option(help="How many years of data, from --start-year.", rich_help_panel=SIZE)] = 10,
    periods: Annotated[
        int | None,
        typer.Option(
            help="How many weeks or months exactly, instead of --years (--periods 36 --period monthly is 3 years).",
            rich_help_panel=SIZE,
        ),
    ] = None,
    start_year: Annotated[int, typer.Option(help="The year the data starts.", rich_help_panel=SIZE)] = 2016,
    columns: Annotated[
        int,
        typer.Option(
            help="How many value columns, in this order: disease_cases, population, rainfall, mean_temperature, "
            "min_temperature, max_temperature, relative_humidity, soil_moisture, ndvi, elevation. Above 10 you get "
            "covariate_11, covariate_12 and so on.",
            rich_help_panel=COLUMNS,
        ),
    ] = 10,
    column: Annotated[
        list[str] | None,
        typer.Option(
            help="Name the value columns yourself, one --column per column, in order. The first is the target (what "
            "models predict). Names from the --columns list get realistic values, others a seasonal covariate "
            "between 0 and 100. Replaces --columns.",
            rich_help_panel=COLUMNS,
        ),
    ] = None,
    missing: Annotated[
        float,
        typer.Option(
            help="Leave some case counts (the target) empty at random, as weeks with no report would be. A "
            "fraction: 0.002 is about 1 value in 500, 0 is none. Chap still imports these org units.",
            rich_help_panel=COLUMNS,
        ),
    ] = 0.002,
    geometry: Annotated[
        Geometry,
        typer.Option(
            help="point: each org unit is a point, like a health facility. polygon: each is an area, like a "
            "district, with a jagged border shared with its neighbours.",
            rich_help_panel=LOCATIONS,
        ),
    ] = Geometry.point,
    corners: Annotated[
        int,
        typer.Option(
            help="How many points each area's border has, with --geometry polygon. More points draw a more "
            "detailed border and make the file larger.",
            rich_help_panel=LOCATIONS,
        ),
    ] = 800,
    districts_per_region: Annotated[
        int,
        typer.Option(
            help="About how many districts make up a region (level 2) in hierarchy.geojson. Regions group "
            "neighbouring districts, so their sizes vary around this.",
            rich_help_panel=LOCATIONS,
        ),
    ] = 10,
    facilities_per_district: Annotated[
        int,
        typer.Option(
            help="How many facilities a district (level 3) has on average, with --geometry point. Districts differ: "
            "most have between half and twice as many.",
            rich_help_panel=LOCATIONS,
        ),
    ] = 50,
    geojson: Annotated[
        bool,
        typer.Option(
            "--geojson",
            help="Write the locations only as locations.geojson, not locations.parquet, to test a GeoJSON upload.",
            rich_help_panel=LOCATIONS,
        ),
    ] = False,
    formats: Annotated[
        list[Format] | None,
        typer.Option(
            "--format",
            help="Also write the dataset as csv, geojson, json-columns (the body the Modeling App sends today) or "
            "json-rows (one object per value); repeat for several. Parquet is always written.",
            rich_help_panel=FORMATS,
        ),
    ] = None,
    masked: Annotated[
        list[str] | None,
        typer.Option(
            help="Hide the target between two periods, START:END (for example 201801:201803), as a dataset with "
            "known bad data would. Repeat for several ranges.",
            rich_help_panel=SETTINGS,
        ),
    ] = None,
    metadata: Annotated[
        bool,
        typer.Option(
            help="--no-metadata writes no chap.* settings; Chap then names the dataset after the file.",
            rich_help_panel=SETTINGS,
        ),
    ] = True,
    spec_version: Annotated[
        str,
        typer.Option(
            help="The file format version written to the file. Chap only reads 1, so anything else is refused.",
            rich_help_panel=SETTINGS,
        ),
    ] = "1",
    about: Annotated[
        str,
        typer.Option(
            help="A description stored in expected.json (default: made from the settings).", rich_help_panel=SETTINGS
        ),
    ] = "",
    covariate_gaps: Annotated[
        int,
        typer.Option(
            help="The first N org units each miss one value in the last value column. Chap rejects those org units.",
            rich_help_panel=REJECTED,
        ),
    ] = 0,
    drop_locations: Annotated[
        int,
        typer.Option(
            help="The last N org units have data but no location in the locations file. Chap rejects them.",
            rich_help_panel=REJECTED,
        ),
    ] = 0,
    duplicate_rows: Annotated[
        int,
        typer.Option(
            help="The first N rows are written twice, so an org unit has two values for one period. Chap refuses "
            "the upload.",
            rich_help_panel=REFUSED,
        ),
    ] = 0,
    text_column: Annotated[
        str | None,
        typer.Option(
            help="Add a column with this name holding text instead of numbers. Chap refuses the upload.",
            rich_help_panel=REFUSED,
        ),
    ] = None,
    drop_time_period: Annotated[
        bool,
        typer.Option(
            "--drop-time-period",
            help="Leave out the time_period column, so Chap cannot tell when the values are from. Chap refuses the "
            "upload.",
            rich_help_panel=REFUSED,
        ),
    ] = False,
    not_parquet: Annotated[
        bool,
        typer.Option(
            "--not-parquet",
            help="Write a CSV file named observations.parquet, as a wrongly saved file would be. Chap refuses it.",
            rich_help_panel=REFUSED,
        ),
    ] = False,
    seed: Annotated[
        int | None,
        typer.Option(
            help="The same seed and options always give the same files. Without it a random seed is used and "
            "recorded in expected.json.",
            rich_help_panel=REPRODUCE,
        ),
    ] = None,
    out: Annotated[
        Path, typer.Option(help="The folder the dataset folder is written in.", rich_help_panel=REPRODUCE)
    ] = DATASETS,
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
        districts_per_region=districts_per_region,
        facilities_per_district=facilities_per_district,
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

    show_progress = sys.stderr.isatty()

    def progress(done: int, total: int) -> None:
        """A counter on the terminal while large datasets are written, erased when done."""
        if show_progress and total > 1_000:
            line = f"{done:,} of {total:,} org units" if done < total else ""
            typer.echo(f"\r\033[K{line}", nl=False, err=True)

    extra = [f.value for f in formats or [] if f is not Format.parquet]
    if extra and not_parquet:
        raise typer.BadParameter("--format needs real Parquet files to convert; leave out --not-parquet")
    try:
        expected = build(spec, directory, progress)
        for fmt in extra:
            export(directory, fmt)
    except ValueError as e:
        raise typer.BadParameter(str(e)) from e
    ui.show_generated(name, directory, expected)


@app.command()
def upload(
    directory: Annotated[
        Path, typer.Argument(help="The dataset folder to upload, such as datasets/03-facility-points.")
    ],
    dhis2: Dhis2 = False,
    dry_run: DryRun = False,
    bandwidth: Bandwidth = None,
    wait: Annotated[
        bool, typer.Option(help="After an import, wait until Chap has stored the dataset and print its id.")
    ] = False,
    raw: Annotated[bool, typer.Option("--raw", help="Also print Chap's answer as it came, in JSON.")] = False,
) -> None:
    """Upload one dataset folder, and say what Chap made of it."""
    where = "through DHIS2" if dhis2 else "to Chap"
    with ui.status_console.status(f"Uploading {directory.name} {where}{' (dry run)' if dry_run else ''}"):
        answer = upload_files(target(dhis2, bandwidth), directory, dry_run)
    ui.show_answer(directory, answer, dry_run, raw)
    job = answer.body.get("id") if isinstance(answer.body, dict) else None
    if wait and job and not dry_run and answer.http == 200:
        with ui.status_console.status("Waiting for Chap to store the dataset"):
            outcome = wait_for_job(State.target, job)
        ui.show_job(outcome)
        if outcome.status != "SUCCESS":
            raise typer.Exit(1)
    if answer.http != 200:
        raise typer.Exit(1)


@app.command()
def check(
    root: Annotated[Path, typer.Argument(help="The folder holding the dataset folders to check.")] = DATASETS,
    dhis2: Dhis2 = False,
) -> None:
    """Dry-run every dataset under ROOT and compare Chap's answer with its expected.json."""
    table = Table("Dataset", "Result", "Expected", "Chap answered")
    failed = 0
    directories = sorted(p for p in root.iterdir() if (p / "expected.json").exists())
    with ui.status_console.status("Checking") as status:
        for directory in directories:
            status.update(f"Checking {directory.name}")
            expected = Expected.read(directory)
            answer = upload_files(target(dhis2), directory, dry_run=True)
            ok = matches(expected, answer)
            failed += not ok
            table.add_row(
                directory.name,
                "[green]ok[/]" if ok else "[bold red]FAIL[/]",
                ui.describe_expected(expected),
                ui.describe_answer(answer),
            )
    ui.console.print(table)
    if failed:
        ui.console.print(f"[bold red]{failed} of {len(directories)} datasets gave another answer[/]")
        raise typer.Exit(1)
    ui.console.print(f"[bold green]All {len(directories)} datasets gave the expected answer[/]")


@app.command()
def compare(
    datasets: Annotated[
        list[str] | None, typer.Argument(help="The datasets to compare, by folder name under --root.")
    ] = None,
    all_: Annotated[
        bool, typer.Option("--all", help="Compare every dataset Chap should import, not the ones it must refuse.")
    ] = False,
    root: Annotated[Path, typer.Option(help="The folder holding the dataset folders.")] = DATASETS,
    dhis2: Dhis2 = False,
    dry_run: DryRun = False,
    bandwidth: Bandwidth = None,
    formats: Annotated[
        list[CompareFormat] | None,
        typer.Option(
            "--format",
            help="Which forms to upload: parquet, json-columns (what the Modeling App sends today) or json-rows "
            "(one object per value). Repeat for several; default all three.",
        ),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option(help="After each import, wait until Chap has stored the dataset and report how long it took."),
    ] = False,
    repeat: Annotated[int, typer.Option(help="Upload each form N times and report the middle (median) time.")] = 1,
    results: Annotated[Path, typer.Option(help="A Markdown file the results table is added to.")] = RESULTS
    / "compare.md",
) -> None:
    """Upload datasets as Parquet and as today's two JSON bodies, and compare size and time."""
    names = list(datasets or [])
    if all_:
        names = sorted(
            d.name for d in root.iterdir() if (d / "expected.json").exists() and Expected.read(d).http == 200
        )
    if not names:
        raise typer.BadParameter("name datasets or pass --all")
    chosen: list[str] = [f.value for f in formats] if formats else [str(f) for f in comparison.FORMATS]
    title = comparison.title(target(dhis2, bandwidth), dry_run)
    ui.console.print(f"[bold]{title}[/]")
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            with ui.status_console.status(f"Uploading {name} in {len(chosen)} forms"):
                found = list(
                    comparison.compare_dataset(State.target, root / name, Path(tmp), dry_run, wait, repeat, chosen)
                )
            rows += found
            ui.show_comparison(name, found)
    results.parent.mkdir(parents=True, exist_ok=True)
    with results.open("a") as f:
        f.write("\n".join([comparison.markdown_header(title), *(row.markdown() for row in rows)]) + "\n")
    ui.console.print(f"[dim]Added to {results}[/]")


@app.command("time-checks")
def time_checks(
    datasets: Annotated[
        list[Path], typer.Argument(help="The dataset folders to time, such as datasets/23-org-units-100k-weekly-10y.")
    ],
    memory_limit: Annotated[
        str, typer.Option(help="The most memory the checks may use, such as 1GB; beyond it they use the disk instead.")
    ] = "1GB",
) -> None:
    """Time the checks a Phase 2 import would run, on the files themselves and without Chap.

    Uses DuckDB to measure; which engine Chap uses for this is not decided. Peak memory is for the
    whole process.
    """
    for directory in datasets:
        with ui.status_console.status(f"Checking {directory.name}"):
            rows, results, peak_mb = run_checks(directory, memory_limit)
        table = Table(title=f"{directory.name}: {rows:,} rows", title_justify="left")
        table.add_column("Check")
        table.add_column("Time", justify="right")
        table.add_column("Found", justify="right")
        for result in results:
            table.add_row(result.name, f"{result.seconds:.2f} s", f"{result.found:,}")
        total = sum(r.seconds for r in results)
        table.add_row("[bold]all checks[/]", f"[bold]{total:.2f} s[/]", f"[dim]{peak_mb:,.0f} MB memory at most[/]")
        ui.console.print(table)
