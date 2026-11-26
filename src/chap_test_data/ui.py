"""How the command line shows results: rich text and tables, plain when the output is not a terminal."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from chap_test_data.client import Answer, JobOutcome
from chap_test_data.compare import CompareRow
from chap_test_data.files import Expected

console = Console(highlight=False)
status_console = Console(stderr=True, highlight=False)  # spinners, kept off stdout


def megabytes(path: Path) -> str:
    return f"{path.stat().st_size / 1e6:,.2f} MB"


def show_generated(name: str, directory: Path, expected: Expected) -> None:
    files = ", ".join(f"{p.name} [dim]{megabytes(p)}[/]" for p in sorted(directory.iterdir()) if p.suffix != ".json")
    console.print(f"[bold]{name}[/]  {expected.rows or 0:,} rows  {files}")
    console.print(f"  [dim]Chap should answer[/] {describe_expected(expected)}  [dim](seed {expected.seed})[/]")


def describe_expected(expected: Expected) -> str:
    if expected.http == 200:
        rejected = f", {expected.rejected} rejected" if expected.rejected else ""
        return f"[green]{expected.imported_count:,} imported{rejected}[/]"
    return f"[yellow]{expected.http}: {'too large' if expected.http == 413 else expected.detail}[/]"


def describe_answer(answer: Answer) -> str:
    """Chap's answer in a few words, coloured as describe_expected."""
    if answer.http == 200 and isinstance(answer.body, dict):
        rejected = len(answer.body.get("rejected", []))
        return (
            f"[green]{answer.body.get('importedCount', 0):,} imported{f', {rejected} rejected' if rejected else ''}[/]"
        )
    return f"[yellow]{answer.http}: {'too large' if answer.http == 413 else detail_text(answer)}[/]"


def detail_text(answer: Answer) -> str:
    """Chap's error message, without JSON quotes; a list of problems is joined into one line."""
    body = answer.body
    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, list):
        return "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
    return str(detail)


def show_answer(directory: Path, answer: Answer, dry_run: bool, raw: bool) -> None:
    """Chap's answer to an upload, in words, with a table of any rejected locations."""
    if raw:
        console.print_json(data=answer.body) if not isinstance(answer.body, str) else console.print(answer.body)
    sent = f"  [dim]HTTP {answer.http} in {answer.seconds:.2f} s, {answer.bytes / 1e6:,.2f} MB sent[/]"
    body = answer.body if isinstance(answer.body, dict) else {}
    if answer.http != 200:
        console.print(f"[bold red]Chap refused {directory.name}:[/] {detail_text(answer)}")
        console.print(sent)
        return
    rejected = body.get("rejected", [])
    verb = "would import" if dry_run else "is importing"
    console.print(
        f"[bold green]Chap {verb} {body.get('importedCount', 0):,} locations[/] from {directory.name}"
        f"{f', and rejects {len(rejected)}' if rejected else ''}"
    )
    console.print(sent)
    if rejected:
        table = Table("Location", "Value", "Periods", "Why it was rejected", show_lines=False)
        for row in rejected[:25]:
            periods = row.get("timePeriods") or []
            table.add_row(
                row.get("orgUnit", ""),
                row.get("featureName", ""),
                ", ".join(periods[:3]) + (" ..." if len(periods) > 3 else ""),
                row.get("reason", ""),
            )
        console.print(table)
        if len(rejected) > 25:
            console.print(f"  [dim]and {len(rejected) - 25} more; --raw shows them all[/]")


def show_job(outcome: JobOutcome) -> None:
    took = f" in {outcome.seconds:.1f} s" if outcome.seconds is not None else ""
    if outcome.dataset_id:
        console.print(f"[bold green]Stored as dataset {outcome.dataset_id}[/]{took}")
    elif outcome.status == "TIMEOUT":
        console.print("[bold red]Chap had not finished storing it after 30 minutes[/]")
    else:
        console.print(f"[bold red]Storing failed[/]{took}: {outcome.error or outcome.status}")


def show_comparison(dataset: str, rows: list[CompareRow]) -> None:
    """One table per dataset: each form's size and time, and how they compare with Parquet."""
    stored = any(row.worker for row in rows)
    table = Table(title=dataset, title_justify="left")
    table.add_column("Form")
    for name in ("Size", "vs Parquet", "Time", "vs Parquet", *(["Stored in"] if stored else [])):
        table.add_column(name, justify="right")
    table.add_column("Answer")
    for row in rows:
        if row.http == 200:
            count = f"{int(row.outcome):,}" if row.outcome.isdigit() else row.outcome
            answer = f"[green]{count} imported[/]"
        else:
            answer = f"[yellow]{row.http}: {row.outcome}[/]"
        cells = [row.form, f"{row.megabytes:,.2f} MB", row.size_x, f"{row.seconds:.2f} s", row.time_x]
        table.add_row(*cells, *([row.worker] if stored else []), answer)
    console.print(table)
