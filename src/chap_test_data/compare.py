"""Upload the same dataset as Parquet and as today's two JSON bodies, and compare size and time.

  parquet       POST /v1/crud/datasets/files, the two files as a multipart form
  json-columns  POST /v1/analytics/make-dataset with providedDataColumns (the Modeling App today)
  json-rows     POST /v1/analytics/make-dataset with providedData, one object per value

The JSON bodies carry the same name, target column, data sources and locations as the Parquet
files' chap.* metadata.
"""

import statistics
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from chap_test_data.client import Answer, Target, post_make_dataset, upload_files, wait_for_job
from chap_test_data.export import export

FORMATS = ("parquet", "json-columns", "json-rows")


def header(target: Target, dry_run: bool) -> str:
    via = "through DHIS2" if target.dhis2 else "direct"
    mode = "dry run" if dry_run else "import"
    link = f", sent at {target.bandwidth:g} Mbit/s" if target.bandwidth else ""
    return (
        f"\n### {datetime.now():%Y-%m-%d %H:%M}, {via}, {mode}{link}\n\n"
        "| Dataset | Format | Body | Body vs Parquet | HTTP | Request | Request vs Parquet | Worker | Imported |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )


def compare_dataset(
    target: Target,
    directory: Path,
    tmp: Path,
    dry_run: bool,
    wait: bool,
    repeat: int,
    formats: list[str] | None = None,
) -> Iterator[str]:
    """Upload one dataset in each format (default all three); yields one table row per format.

    The ratios compare with Parquet, so they are filled in only when Parquet is among the formats.
    """
    formats = formats or list(FORMATS)
    bodies = {fmt: export(directory, fmt, tmp / directory.name)[0] for fmt in formats if fmt != "parquet"}
    baseline: dict[str, float] = {}
    for fmt in [f for f in FORMATS if f in formats]:
        runs: list[Answer] = [
            upload_files(target, directory, dry_run)
            if fmt == "parquet"
            else post_make_dataset(target, bodies[fmt], dry_run)
            for _ in range(repeat)
        ]
        last = runs[-1]
        seconds = statistics.median(r.seconds for r in runs)
        worker = ""
        job = last.body.get("id") if isinstance(last.body, dict) else None
        if wait and not dry_run and last.http == 200 and job:
            stored = wait_for_job(target, job)
            worker = f"{stored.seconds:.1f} s" if stored.status == "SUCCESS" and stored.seconds else stored.status
        imported = last.body.get("importedCount") if isinstance(last.body, dict) else None
        outcome = imported if last.http == 200 else last.detail[:120]
        if fmt == "parquet":
            baseline = {"bytes": last.bytes, "seconds": seconds}
        size_x = f"{last.bytes / baseline['bytes']:.1f}x" if baseline.get("bytes") else ""
        time_x = f"{seconds / baseline['seconds']:.1f}x" if baseline.get("seconds") else ""
        yield (
            f"| {directory.name} | {fmt} | {last.bytes / 1e6:.2f} MB | {size_x} | {last.http} | {seconds:.2f} s "
            f"| {time_x} | {worker} | {outcome} |"
        )
