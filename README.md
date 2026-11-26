# chap-test-data

[![CI](https://github.com/dhis2-chap/chap-test-data/actions/workflows/ci.yml/badge.svg)](https://github.com/dhis2-chap/chap-test-data/actions/workflows/ci.yml)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Generate synthetic Chap datasets of any size, as Parquet, CSV, GeoJSON or the `make-dataset`
JSON bodies, and upload, check and compare them against Chap. Made for Chap's Parquet dataset
upload, `POST /v1/crud/datasets/files`, from the chap-core branch `feat/dataset-parquet-upload`
(Phase 1: the files are read and stored as today, in Postgres). Uploads can go straight to Chap
or through a DHIS2 route.

A dataset is two files:

- `observations.parquet`: `location`, `time_period`, then one numeric column per value
  (cases, covariates, climate). Dataset settings sit in the file's `chap.*` metadata keys.
- `locations.parquet` (GeoParquet) or `locations.geojson`: one row per `location`, with `name`,
  `parent`, `level` and the geometry.

The format and the metadata keys are described in chap-core's `docs/webapi/dataset-files.md`.

## What is here

| Path | What it is |
| --- | --- |
| `src/chap_test_data/` | The `chap-test-data` command line: `generate`, `upload`, `check`, `compare`, `time-checks` (Python, httpx2) |
| `generate-datasets.sh` | Writes the standard test datasets into `datasets/` (`--large` adds the large examples) |
| `upload.sh`, `check-all.sh` | The same upload and check with plain curl, for machines without uv |
| `dhis2/` | A local DHIS2 that joins Chap's Docker network, and `setup-route.sh` for the route |
| `results/compare.md` | The comparison tables from the last runs |

Setup: `uv sync`, then `uv run chap-test-data --help`. `make lint` runs ruff, mypy and pyright, the
same tools as chap-core; `make test` runs the tests, which need no running Chap; `make build` (or
`uv build`) builds the package. CI runs all three on every pull request.

## Generate datasets

```bash
./generate-datasets.sh            # the 16 standard datasets, a few seconds, always the same (seed 42)
./generate-datasets.sh --large    # also the large examples, about a minute and 1.2 GB
```

Every dataset is one `chap-test-data generate NAME` with options, so variations are one command:

```bash
uv run chap-test-data generate my-test --org-units 5000 --years 5 --period monthly
uv run chap-test-data generate catchments --org-units 800 --geometry polygon --corners 256
uv run chap-test-data generate malaria --column malaria_cases --column population --column precipitation
uv run chap-test-data generate gaps --org-units 50 --covariate-gaps 5 --drop-locations 2
uv run chap-test-data generate --help
```

- Size: `--org-units`, `--years` or `--periods`, `--period weekly|monthly`, `--start-year`.
- Columns: `--columns N` takes the first N of disease_cases, population, rainfall,
  mean_temperature, min_temperature, max_temperature, relative_humidity, soil_moisture, ndvi,
  elevation (default all 10). `--column NAME` (repeatable) names them instead; the first is the
  target. `--missing` sets the share of missing target values.
- Locations: `--geometry point` (default) or `polygon`, with `--corners N` per polygon (3 is a
  triangle, the default 64 is nearly round); `--geojson` writes GeoJSON instead of GeoParquet.
- Settings: `--masked START:END`, `--no-metadata`, `--spec-version`.
- Faults Chap must catch: `--covariate-gaps N`, `--drop-locations N` (those org units are
  rejected), `--duplicate-rows N`, `--text-column NAME`, `--drop-time-period`, `--not-parquet`
  (the whole upload is refused).
- Formats: Parquet is always written; `--format` (repeatable) adds `csv` (`observations.csv`
  with time_period, location and the values, plus `locations.geojson`), `geojson`
  (`locations.geojson`), `json-columns` (`make-dataset.columns.json`, the body the Modeling App
  sends today) and `json-rows` (`make-dataset.rows.json`, one object per value). They are
  converted from the Parquet files in batches, so they work for large datasets too.

```bash
uv run chap-test-data generate laos-like --org-units 30 --period monthly --format csv --format json-columns
```

Values follow chapkit's `TestDataGenerator` (`chapkit/src/chapkit/data/generator.py`), so models
tested with either tool see the same ranges: population 50,000 to 1.5 million per org unit,
rainfall 150 +/- 130 mm per period following each org unit's own season, temperature 24 +/- 7 °C on
a regional cycle, cases from a per-org-unit level and the season plus 0.06 x rainfall, and other
covariates seasonal between 0 and 100. Locations are a grid of 0.8 degree cells near Nairobi,
shrinking for large counts. The schema is Chap's, not chapkit's: periods as Chap stores them
(`2016W01`, `201601`, real ISO weeks) and DHIS2-style org unit ids.

The seed is random by default and recorded in `expected.json`; pass `--seed N` (the recorded one,
or any fixed number such as 42) to get the same files again.

The observations are written in batches of org units, so memory stays small: 52 million rows
take about 25 s and 650 MB. Each folder gets an `expected.json` with the dry-run answer Chap's
Phase 1 endpoint should give, worked out from the options and Chap's limits (100 MB per file,
1 million rows).

### The standard datasets

| Dataset | Size | Expected answer |
| --- | --- | --- |
| `01-small-monthly` | 10 org units x 36 months, polygons | 10 imported |
| `02-district-weekly` | 150 x 365 weeks, polygons with 512 corners | 150 imported |
| `03-facility-points` | 1,500 x 365 weeks, points (3.8 MB) | 1,500 imported |
| `04-facility-polygons` | 1,500 x 365 weeks, polygons with 2,048 corners (37 MB) | 1,500 imported |
| `05-facility-points-2000` | 2,000 x 365 weeks, points (5.1 MB) | 2,000 imported |
| `06-geojson-locations` | 50 x 104 weeks, locations as GeoJSON | 50 imported |
| `07-masked-ranges` | 20 x 36 months, cases masked 201801 to 201803 by the metadata | 20 imported |
| `08-no-metadata` | 10 x 24 months, no `chap.*` keys; the name comes from the file name | 10 imported |
| `09-covariate-gaps` | 20 org units, 3 miss one covariate value | 17 imported, 3 rejected |
| `10-missing-locations` | 20 org units, 4 missing from the locations file | 16 imported, 4 rejected |
| `11-bad-duplicate-rows` | one row twice | 422 |
| `12-bad-text-column` | a text column in the observations | 422 |
| `13-bad-no-time-period` | no `time_period` column | 422 |
| `14-bad-spec-version` | `chap.spec_version` 2 | 422 |
| `15-bad-not-parquet` | a CSV file named `observations.parquet` | 422 |
| `16-named-columns` | 20 x 36 months, columns named malaria_cases, population, precipitation, temperature_2m | 20 imported |

The standard datasets use 4 value columns. The large examples use all 10, over 10 years:

| Dataset | Rows | Observations file | Phase 1 answer |
| --- | --- | --- | --- |
| `20-phase1-max-weekly-10y` | 1,900 org units x 522 weeks = 991,800 | 15 MB | 1,900 imported |
| `21-facilities-20k-weekly-10y` | 20,000 x 522 = 10.4 million | 161 MB | 413, file too large |
| `22-org-units-100k-monthly-10y` | 100,000 x 120 = 12 million | 177 MB | 413, file too large |
| `23-org-units-100k-weekly-10y` | 100,000 x 522 = 52.2 million | 753 MB | 413, file too large |

The last three are the size target for Phase 2 (stored files, CLIM-2035); Phase 1 refuses them
on purpose.

## 1. Start Chap from the branch

```bash
cd ../chap-core
git switch feat/dataset-parquet-upload
docker compose -p chap-test-data up -d --build
curl localhost:8000/health
```

The project name `chap-test-data` keeps this stack and its volumes apart from any other Chap you
run. Chap answers on `http://localhost:8000`, without a token unless `CHAP_API_TOKEN` is set in
chap-core's `.env`.

## 2. Upload without DHIS2

```bash
uv run chap-test-data upload --dry-run datasets/03-facility-points   # validate only
uv run chap-test-data upload --wait datasets/03-facility-points      # import, and wait for the job
uv run chap-test-data check                                          # dry-run all, compare with expected.json
```

The same with curl, without Python:

```bash
./upload.sh --dry-run datasets/03-facility-points
./check-all.sh

curl -X POST "http://localhost:8000/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet
```

Connection settings are options or environment variables: `CHAP_URL`, `CHAP_API_TOKEN`,
`DHIS2_URL`, `DHIS2_USER`, `DHIS2_PASSWORD`, `ROUTE_CODE`. With curl, a token goes in
`-H "Authorization: Bearer ..."`.

## 3. Upload through a DHIS2 route

Start DHIS2 on Chap's network and create the route (first start takes a minute or two):

```bash
cd dhis2
docker compose up -d                    # DHIS2 2.43.2.1; another version: DHIS2_TAG=2.42.7.1 docker compose up -d
./setup-route.sh                        # waits for DHIS2, then creates the route `chap` -> http://chap:8000/**
cd ..
```

Then upload through it, as the Modeling App would:

```bash
uv run chap-test-data upload --dhis2 --dry-run datasets/03-facility-points
uv run chap-test-data check --dhis2
./check-all.sh --dhis2

curl -u admin:district -X POST \
  "http://localhost:8080/api/routes/chap/run/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet
```

DHIS2 2.42.3 and later forward each file twice
([DHIS2-22596](https://dhis2.atlassian.net/browse/DHIS2-22596)); Chap ignores the extra copies,
so the upload is the same as without DHIS2. To switch DHIS2 version, start from a fresh
database (`docker compose down -v` first). For another DHIS2, set the connection settings above
and make sure it allows the route's target in `route.remote_servers_allowed`.

## Results

Measured on a MacBook with Docker Desktop, chap-core `feat/dataset-parquet-upload`.

- 2026-11-26: every dataset gave the expected answer through DHIS2 routes on 2.41.11, 2.42.7.1
  and 2.43.2.1, and a real import of `03-facility-points` succeeded through each.
- 2026-11-25, real imports (time for the upload request; the worker then stores the data):

| Dataset | Direct | Through DHIS2 2.43 |
| --- | --- | --- |
| `03-facility-points` (1,500 x 365) | 4.2 s | 4.4 s |
| `05-facility-points-2000` (2,000 x 365) | 5.8 s | 6.0 s |
| `04-facility-polygons` (1,500 x 365, 35 MB of polygons) | 20.3 s | 21.7 s |

With large polygons most of the time goes to checking and queueing the geometry, as in today's
JSON import. The DHIS2 route's timeout (30 s in the Modeling App, 60 s at most) counts from the
end of the upload, so a slow upload does not use it up.

## Comparing Parquet with today's JSON uploads

`chap-test-data compare` uploads each dataset three ways to the same Chap: as Parquet, as
`make-dataset` JSON with `providedDataColumns` (what the Modeling App sends today), and as
`make-dataset` JSON with `providedData` (one object per value, the older form). The JSON bodies
carry the same settings and locations as the Parquet files' metadata.

```bash
uv run chap-test-data compare 02-district-weekly 03-facility-points --dry-run --repeat 3
uv run chap-test-data compare --all --dry-run --repeat 3 --dhis2
uv run chap-test-data compare 03-facility-points --wait          # real import, with the worker's time
```

`--all` takes every dataset expected to import, including `20-phase1-max-weekly-10y`, whose
one-object-per-value JSON body is several GB; name the datasets to leave it out.

Results of 2026-11-26, dry runs directly to Chap, median of 3 (datasets from
`./generate-datasets.sh`, 4 value columns; full tables in `results/compare.md`):

| Dataset | Format | Body | Request |
| --- | --- | --- | --- |
| 03-facility-points, 1,500 x 365 | Parquet | 3.8 MB | 0.98 s |
| | JSON columns | 31.4 MB (8.2x) | 1.37 s (1.4x) |
| | JSON rows | 211.5 MB (55x) | 15.18 s (15.5x) |
| 05-facility-points-2000, 2,000 x 365 | Parquet | 5.1 MB | 1.30 s |
| | JSON columns | 41.9 MB (8.2x) | 1.87 s (1.4x) |
| | JSON rows | 282.0 MB (55x) | 20.66 s (15.9x) |
| 04-facility-polygons, 1,500 x 365, large polygons | Parquet | 40.8 MB | 10.57 s |
| | JSON columns | 158.1 MB (3.9x) | 13.00 s (1.2x) |
| | JSON rows | 338.2 MB (8.3x) | 26.14 s (2.5x) |
| 02-district-weekly, 150 x 365 | Parquet | 1.2 MB | 0.43 s |
| | JSON columns | 6.3 MB (5.1x) | 0.40 s (0.9x) |
| | JSON rows | 24.3 MB (20x) | 1.92 s (4.4x) |

What it shows:

- **Size is the big win.** At facility scale the Parquet upload is about 8x smaller than today's
  columnar JSON and about 55x smaller than one object per value. How much smaller depends on the
  data: the first test data (2026-11-25), with smoother values, gave 14x and 104x. Real DHIS2 data
  may land anywhere in between. With large polygons the geometry dominates and the gap narrows
  to 4x and 8x.
- **On the server, Parquet is 1.2x to 1.4x faster than columnar JSON** and 15x faster than one
  object per value. For small datasets the two are about even.
- **The worker takes the same time for every format** (54 s at 1,500 facilities, 70 s at 2,000,
  measured 2026-11-25), because all three queue the same job. Phase 2 (stored files) removes it.
- **The DHIS2 route adds about 0.1 s** and keeps the same ratios (measured 2026-11-25).
- These uploads ran on one machine, so transfer time is near zero. Over a real link the body
  size counts directly: at 10 Mbit/s, 31 MB of columnar JSON takes about 25 s to send and the
  3.8 MB Parquet file about 3 s.

## Timing the Phase 2 checks

In Phase 2 (CLIM-2035) the API checks uploads straight on the files, with no worker.
`chap-test-data time-checks` runs those checks on dataset folders without Chap and times them:
duplicates, periods per org unit, covariate gaps, and org units missing from the locations file.

```bash
uv run chap-test-data time-checks datasets/21-facilities-20k-weekly-10y datasets/23-org-units-100k-weekly-10y
```

It uses DuckDB to measure; which engine Chap uses is not decided. On a 12-core MacBook
(2026-11-26): 0.2 s for 10.4 million rows and 3.7 s for 52.2 million rows, nearly all of it the
duplicate check, with about 1.6 GB peak memory for the whole process.

## Stop

```bash
cd dhis2 && docker compose down -v && cd ..
cd ../chap-core && docker compose -p chap-test-data down -v
```
