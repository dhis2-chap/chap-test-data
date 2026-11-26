"""Time the checks a Phase 2 import would run, straight on the files, without Chap.

DuckDB is used here to measure; which engine Chap uses for this is not decided.
"""

import resource
import time
from pathlib import Path

import duckdb
import pyarrow.parquet as pq
from pydantic import BaseModel


class CheckResult(BaseModel):
    name: str
    seconds: float
    found: int


def run_checks(directory: Path, memory_limit: str = "1GB") -> tuple[int, list[CheckResult], float]:
    """Run each check on the folder's files; returns the row count, the results and the peak memory in MB."""
    observations = directory / "observations.parquet"
    locations = directory / "locations.parquet"
    if not locations.exists():
        raise FileNotFoundError(f"{directory} needs observations.parquet and locations.parquet")
    names = pq.read_schema(observations).names
    if "location" not in names or "time_period" not in names:
        raise ValueError(f"{observations} needs location and time_period columns")
    covariates = [c for c in names if c not in ("location", "time_period")][1:]
    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{memory_limit.replace("'", '')}'")
    # Paths go in through the relation API, never into SQL text.
    con.read_parquet(str(observations)).create_view("obs")
    con.read_parquet(str(locations)).create_view("locs")
    quoted = ['"' + c.replace('"', '""') + '"' for c in covariates]
    any_gap = " OR ".join(f"{c} IS NULL" for c in quoted) or "false"
    checks = {
        "row count (footer)": "SELECT count(*) FROM obs",
        "duplicate (location, time_period)": "SELECT location, time_period FROM obs GROUP BY ALL HAVING count(*) > 1",
        "periods per org unit, first and last": (
            "SELECT location, count(*), min(time_period), max(time_period) FROM obs GROUP BY location"
        ),
        # Column names come from the file's own schema and are quoted above.
        "org units with a covariate gap": f"SELECT location FROM obs GROUP BY location HAVING bool_or({any_gap})",  # noqa: S608
        "org units missing from locations": (
            "SELECT DISTINCT o.location FROM obs o ANTI JOIN (SELECT location FROM locs) l USING (location)"
        ),
    }
    results = []
    for name, sql in checks.items():
        started = time.perf_counter()
        rows = con.execute(sql).fetchall()
        results.append(CheckResult(name=name, seconds=time.perf_counter() - started, found=len(rows)))
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20  # bytes on macOS
    if peak_mb < 1:  # Linux reports kilobytes
        peak_mb *= 1024
    return pq.ParquetFile(observations).metadata.num_rows, results, peak_mb
