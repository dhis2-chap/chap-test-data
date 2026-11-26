"""Chap's file conventions and Phase 1 limits, and expected.json."""

from pathlib import Path

import geopandas as gpd
import pyarrow.parquet as pq
from pydantic import AliasChoices, BaseModel, Field

SPEC_VERSION = "1"
ROW_GROUP_SIZE = 20_000

# Chap's Phase 1 limits (chap_core/file_io/dataset_files.py and the upload endpoint).
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_UPLOAD_BYTES = 4 * MAX_FILE_BYTES + 1024 * 1024
MAX_ROWS = 1_000_000

LOCATION_KEYS = {b"chap.spec_version": SPEC_VERSION.encode(), b"chap.provenance": b'{"license": "CC0-1.0"}'}


def write_locations(frame: gpd.GeoDataFrame, path: Path) -> None:
    """Write GeoParquet; geopandas writes the `geo` key, Chap's keys are merged in after."""
    frame.to_parquet(path, index=False, compression="zstd")
    table = pq.read_table(path)
    pq.write_table(table.replace_schema_metadata({**table.schema.metadata, **LOCATION_KEYS}), path, compression="zstd")


class Expected(BaseModel):
    """expected.json: the dry-run answer Chap should give for a dataset folder."""

    about: str = ""
    seed: int | None = None
    http: int
    imported_count: int | None = Field(
        default=None,
        validation_alias=AliasChoices("importedCount", "imported_count"),
        serialization_alias="importedCount",
    )
    rejected: int | None = None
    detail: str | None = None
    rows: int | None = None
    values: int | None = None

    @classmethod
    def read(cls, directory: Path) -> "Expected":
        return cls.model_validate_json((directory / "expected.json").read_text())

    def write(self, directory: Path) -> None:
        text = self.model_dump_json(by_alias=True, exclude_none=True, indent=2)
        (directory / "expected.json").write_text(text + "\n")

    def summary(self) -> str:
        if self.http == 200:
            return f"200 imported={self.imported_count} rejected={self.rejected}"
        return f"{self.http} ...{self.detail or ''}..."
