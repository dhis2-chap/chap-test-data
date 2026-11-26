# chap-test-data

[![CI](https://github.com/dhis2-chap/chap-test-data/actions/workflows/ci.yml/badge.svg)](https://github.com/dhis2-chap/chap-test-data/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://dhis2-chap.github.io/chap-test-data/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Synthetic datasets for [Chap](https://chap.dhis2.org), at any size, and the tools to send them to
Chap and check its answers.

- **Generate** datasets from 10 to 100,000 org units over any number of years, weekly or monthly,
  as Parquet and GeoParquet, and as CSV, GeoJSON and the `make-dataset` JSON bodies.
- **Know the answer in advance:** each dataset has an `expected.json` with what Chap should answer.
- **Upload and check** against a running Chap, directly or through a DHIS2 route, with Python or
  plain curl.
- **Compare** Parquet uploads with today's JSON uploads, on fast and on slow, distant links.

**Documentation: https://dhis2-chap.github.io/chap-test-data/**

## Quick start

```bash
uv sync
scripts/generate-ready-made.sh --standard-only        # 16 datasets in datasets/, the same every time
uv run chap-test-data generate my-country --org-units 300 --geometry polygon --format geojson
uv run chap-test-data --help
```

Uploading needs a running Chap from the chap-core branch `feat/dataset-parquet-upload`:

```bash
(cd ../chap-core && docker compose -p chap-test-data up -d --build)
uv run chap-test-data check                   # every dataset against its expected.json
scripts/check-curl.sh                                # the same with curl
```

## Developing

`make lint` (ruff, mypy, pyright), `make test`, `make docs`, `make build`. CI runs them on every
push. Licensed under the [AGPL v3](LICENSE), as chap-core.
