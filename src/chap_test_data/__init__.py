"""Test data and upload tools for Chap's Parquet dataset upload (POST /v1/crud/datasets/files)."""


def main() -> None:
    from chap_test_data.cli import app

    app()
