"""Upload datasets to Chap with httpx2, directly or through a DHIS2 route."""

import json
import secrets
import time
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx2
from pydantic import BaseModel

from chap_test_data.files import Expected

PARQUET = "application/vnd.apache.parquet"


class Target(BaseModel):
    """Where uploads go. Through DHIS2 they run on the route, as the Modeling App would send them."""

    chap_url: str = "http://localhost:8000"
    chap_token: str | None = None
    dhis2_url: str = "http://localhost:8080"
    dhis2_user: str = "admin"
    dhis2_password: str = "district"  # noqa: S105 - the DHIS2 demo database login, for a local DHIS2
    route_code: str = "chap"
    dhis2: bool = False
    # Upload speed of a simulated slow link, in Mbit/s; None sends as fast as the machine can.
    bandwidth: float | None = None

    @property
    def base_url(self) -> str:
        return f"{self.dhis2_url}/api/routes/{self.route_code}/run" if self.dhis2 else self.chap_url

    def client(self) -> httpx2.Client:
        if self.dhis2:
            return httpx2.Client(timeout=None, auth=(self.dhis2_user, self.dhis2_password))
        headers = {"Authorization": f"Bearer {self.chap_token}"} if self.chap_token else {}
        return httpx2.Client(timeout=None, headers=headers)


class Answer(BaseModel):
    http: int
    seconds: float
    bytes: int
    body: Any

    @property
    def detail(self) -> str:
        if isinstance(self.body, dict) and "detail" in self.body:
            return json.dumps(self.body["detail"])
        return json.dumps(self.body) if not isinstance(self.body, str) else self.body


def _answer(response: httpx2.Response, started: float, sent: int) -> Answer:
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    return Answer(http=response.status_code, seconds=time.perf_counter() - started, bytes=sent, body=body)


def dataset_files(directory: Path) -> tuple[Path, Path]:
    observations = directory / "observations.parquet"
    locations = directory / "locations.parquet"
    if not locations.exists():
        locations = directory / "locations.geojson"
    if not observations.exists() or not locations.exists():
        raise FileNotFoundError(f"{directory} needs observations.parquet and locations.parquet or .geojson")
    return observations, locations


def throttled(data: bytes, mbit: float, chunk: int = 64 * 1024) -> Iterator[bytes]:
    """Yield data no faster than mbit Mbit/s, as a slow link would carry it."""
    rate = mbit * 1_000_000 / 8
    started = time.perf_counter()
    for offset in range(0, len(data), chunk):
        yield data[offset : offset + chunk]
        ahead = (offset + chunk) / rate - (time.perf_counter() - started)
        if ahead > 0:
            time.sleep(ahead)


def multipart(parts: list[tuple[str, Path, str]]) -> tuple[bytes, str]:
    """A multipart/form-data body with one file per part, and its Content-Type."""
    boundary = secrets.token_hex(16)
    body = b""
    for name, path, content_type in parts:
        head = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        )
        body += head.encode() + path.read_bytes() + b"\r\n"
    return body + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def _post_slowly(target: Target, url: str, dry_run: bool, body: bytes, content_type: str) -> Answer:
    """POST a body at the target's bandwidth; the time includes sending it."""
    assert target.bandwidth is not None
    headers = {"Content-Type": content_type, "Content-Length": str(len(body))}
    with target.client() as client:
        started = time.perf_counter()
        response = client.post(
            url,
            params={"dryRun": "true"} if dry_run else None,
            content=throttled(body, target.bandwidth),
            headers=headers,
        )
        return _answer(response, started, len(body))


def upload_files(target: Target, directory: Path, dry_run: bool) -> Answer:
    """POST the two files as a multipart form to /v1/crud/datasets/files."""
    observations, locations = dataset_files(directory)
    location_type = PARQUET if locations.suffix == ".parquet" else "application/geo+json"
    url = f"{target.base_url}/v1/crud/datasets/files"
    if target.bandwidth:
        body, content_type = multipart(
            [("observations", observations, PARQUET), ("locations", locations, location_type)]
        )
        return _post_slowly(target, url, dry_run, body, content_type)
    sent = observations.stat().st_size + locations.stat().st_size
    with target.client() as client, observations.open("rb") as obs, locations.open("rb") as locs:
        started = time.perf_counter()
        response = client.post(
            url,
            params={"dryRun": "true"} if dry_run else None,
            files={
                "observations": (observations.name, obs, PARQUET),
                "locations": (locations.name, locs, location_type),
            },
        )
        return _answer(response, started, sent)


def post_make_dataset(target: Target, body: Path, dry_run: bool) -> Answer:
    """POST a JSON body to /v1/analytics/make-dataset, as the Modeling App does today."""
    content = body.read_bytes()
    url = f"{target.base_url}/v1/analytics/make-dataset"
    if target.bandwidth:
        return _post_slowly(target, url, dry_run, content, "application/json")
    with target.client() as client:
        started = time.perf_counter()
        response = client.post(
            url,
            params={"dryRun": "true"} if dry_run else None,
            content=content,
            headers={"Content-Type": "application/json"},
        )
        return _answer(response, started, len(content))


def wait_for_job(target: Target, job: str, timeout: float = 1800) -> tuple[str, float | None]:
    """Poll Chap (directly, not through DHIS2) until the job ends; returns its status and run time."""
    deadline = time.time() + timeout
    with httpx2.Client(timeout=30) as client:
        while time.time() < deadline:
            info = client.get(f"{target.chap_url}/v1/jobs/{job}").json()
            if info.get("status") in ("SUCCESS", "FAILURE"):
                start, end = (datetime.fromisoformat(info[k]) for k in ("start_time", "end_time"))
                return info["status"], (end - start).total_seconds()
            time.sleep(3)
    return "TIMEOUT", None


def matches(expected: Expected, answer: Answer) -> bool:
    """Whether Chap's answer is the one expected.json describes."""
    if answer.http != expected.http:
        return False
    if answer.http == 200:
        body = answer.body if isinstance(answer.body, dict) else {}
        rejected = body.get("rejected", [])
        return bool(body.get("importedCount") == expected.imported_count and len(rejected) == expected.rejected)
    return (expected.detail or "") in answer.detail


def summary(answer: Answer) -> str:
    if answer.http == 200 and isinstance(answer.body, dict):
        return f"200 imported={answer.body.get('importedCount')} rejected={len(answer.body.get('rejected', []))}"
    return f"{answer.http} {answer.detail[:70]}"
