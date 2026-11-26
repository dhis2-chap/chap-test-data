# Generating datasets

## The common datasets

```bash
./generate-datasets.sh                  # all, including the large ones: a few minutes and a few GB
./generate-datasets.sh --standard-only  # the 16 standard ones only: seconds
```

They are written to `datasets/` with a fixed seed (42), so they are the same on every machine.
Each is written as Parquet, as GeoJSON locations (`locations.geojson`) and as the JSON body the
Modeling App sends today (`make-dataset.columns.json`). The datasets Chap must refuse are written
as Parquet only.

### Standard

They use 4 value columns: disease_cases, population, rainfall and mean_temperature.

| Dataset | Size | Expected answer |
| --- | --- | --- |
| `01-small-monthly` | 10 districts x 36 months | 10 imported |
| `02-district-weekly` | 150 districts x 365 weeks | 150 imported |
| `03-facility-points` | 1,500 facilities x 365 weeks | 1,500 imported |
| `04-facility-polygons` | 1,500 areas x 365 weeks, 2,048 points per border | 1,500 imported |
| `05-facility-points-2000` | 2,000 facilities x 365 weeks | 2,000 imported |
| `06-geojson-locations` | 50 districts x 104 weeks, locations only as GeoJSON | 50 imported |
| `07-masked-ranges` | 20 x 36 months, cases masked 201801 to 201803 by the metadata | 20 imported |
| `08-no-metadata` | 10 x 24 months, no `chap.*` keys; the name comes from the file name | 10 imported |
| `09-covariate-gaps` | 20 org units, 3 miss one covariate value | 17 imported, 3 rejected |
| `10-missing-locations` | 20 org units, 4 missing from the locations file | 16 imported, 4 rejected |
| `11-bad-duplicate-rows` | one row twice | 422 |
| `12-bad-text-column` | a text column in the observations | 422 |
| `13-bad-no-time-period` | no `time_period` column | 422 |
| `14-bad-spec-version` | `chap.spec_version` 2 | 422 |
| `15-bad-not-parquet` | a CSV file named `observations.parquet` | 422 |
| `16-named-columns` | 20 x 36 months, columns malaria_cases, population, precipitation, temperature_2m | 20 imported |

### Large

10 years with all 10 value columns. Only the first fits Chap's Phase 1 upload (1 million rows,
100 MB per file); the others are the size stored files (Phase 2) are designed for.

| Dataset | Rows | Phase 1 answer |
| --- | --- | --- |
| `20-phase1-max-weekly-10y` | 1,900 x 522 weeks = 991,800 | 1,900 imported |
| `21-facilities-20k-weekly-10y` | 20,000 x 522 = 10.4 million | 413, file too large |
| `22-org-units-100k-monthly-10y` | 100,000 x 120 = 12 million | 413, file too large |
| `23-org-units-100k-weekly-10y` | 100,000 x 522 = 52.2 million | 413, file too large |

`23` gets no JSON body: it would be about 5 GB.

## Your own

Every dataset is one command, so a variation is one command too:

```bash
uv run chap-test-data generate my-test --org-units 5000 --years 5 --period monthly
uv run chap-test-data generate districts --org-units 300 --geometry polygon --format geojson
uv run chap-test-data generate malaria --column malaria_cases --column population --column precipitation
uv run chap-test-data generate gaps --org-units 50 --covariate-gaps 5 --drop-locations 2
uv run chap-test-data generate --help
```

| Options | What they set |
| --- | --- |
| `--org-units`, `--years` or `--periods`, `--period weekly\|monthly`, `--start-year` | The size |
| `--columns N` | The first N of disease_cases, population, rainfall, mean_temperature, min_temperature, max_temperature, relative_humidity, soil_moisture, ndvi, elevation (default 10) |
| `--column NAME` (repeatable) | Your own column names instead; the first is the target |
| `--missing` | The share of missing target values (default 0.002) |
| `--geometry point\|polygon`, `--corners N` | Facility points (default) or district areas with N points per border (default 800) |
| `--format csv\|geojson\|json-columns\|json-rows` (repeatable) | Other formats besides Parquet |
| `--masked START:END`, `--no-metadata`, `--spec-version` | The settings in the file's metadata |
| `--covariate-gaps N`, `--drop-locations N` | Org units Chap must reject |
| `--duplicate-rows N`, `--text-column NAME`, `--drop-time-period`, `--not-parquet` | Files Chap must refuse |
| `--seed N` | The same files every time; without it the seed is random and recorded in `expected.json` |

The observations are written in batches of org units, so memory stays small: 52 million rows
take about 25 s and 650 MB. The other formats are converted from the Parquet files in batches
too.

## Formats

| `--format` | Files |
| --- | --- |
| (always) | `observations.parquet`, `locations.parquet` |
| `geojson` | `locations.geojson` |
| `csv` | `observations.csv` (time_period, location, then the values) and `locations.geojson` |
| `json-columns` | `make-dataset.columns.json`: the `make-dataset` body with `providedDataColumns`, as the Modeling App sends today |
| `json-rows` | `make-dataset.rows.json`: the older body, one object per value |

## The values

Values follow chapkit's `TestDataGenerator`, so models tested with either tool see the same
ranges:

| Column | Values |
| --- | --- |
| population | 50,000 to 1.5 million, fixed per org unit |
| rainfall | 150 +/- 130 mm per period, following each org unit's own season |
| mean_temperature | 24 +/- 7 °C on a regional cycle; min and max 4 to 8 °C below and above |
| disease_cases | a per-org-unit level that follows the season, plus 0.06 x rainfall |
| other covariates | seasonal, between 0 and 100 |

The schema is Chap's, not chapkit's: periods as Chap stores them (`2016W01`, `201601`, with real
ISO weeks, so some years have a week 53) and DHIS2-style org unit ids.

## The map

![Generated districts and facilities](assets/locations.png)

- **Districts** (`--geometry polygon`) tile a country-like map near Nairobi: no gaps, no
  overlaps, and jagged borders shared by both neighbours. A border has about 800 points by
  default, the median of chap-core's example boundaries, and is about 1.7 times as long as a
  circle of the same area, as real borders are (1.4 to 1.9 in those files).
- **Facilities** (`--geometry point`) cluster around a few towns in each district, always inside
  it, and the `parent` column names that district: one per 50 facilities.
