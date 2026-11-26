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

The name is the folder the dataset is written to, under `datasets/` (change it with `--out`).
All options are optional.

### Size and time

| Option | Default | What it does |
| --- | --- | --- |
| `--org-units N` | 100 | How many org units (districts or facilities) the dataset has. |
| `--period weekly` or `--period monthly` | weekly | How often there is a value: once a week (periods like `2016W01`) or once a month (`201601`). |
| `--years N` | 10 | How many years of data, starting in `--start-year`. |
| `--periods N` | | How many weeks or months exactly, instead of `--years`. `--periods 36 --period monthly` is 3 years. |
| `--start-year YEAR` | 2016 | The year the data starts. |

### Value columns

| Option | Default | What it does |
| --- | --- | --- |
| `--columns N` | 10 | How many value columns, taken in this order: disease_cases, population, rainfall, mean_temperature, min_temperature, max_temperature, relative_humidity, soil_moisture, ndvi, elevation. Above 10 you get covariate_11, covariate_12 and so on. |
| `--column NAME` | | Name the value columns yourself, one `--column` per column, in order. The first is the target (what models predict). Names from the list above get realistic values; other names get a seasonal covariate between 0 and 100. Replaces `--columns`. |
| `--missing SHARE` | 0.002 | The share of target values left empty, as real reporting has gaps. 0.002 is 2 in every 1,000. |

### Locations

| Option | Default | What it does |
| --- | --- | --- |
| `--geometry point` | default | Each org unit is a point, like a health facility. |
| `--geometry polygon` | | Each org unit is an area, like a district, with a jagged border shared with its neighbours. |
| `--corners N` | 800 | How many points each area's border has, with `--geometry polygon`. More points draw a more detailed border and make the file larger. |
| `--geojson` | | Write the locations only as `locations.geojson`, not as `locations.parquet`. Use it to test a GeoJSON upload. |

### Other formats

| Option | Default | What it does |
| --- | --- | --- |
| `--format FORMAT` | | Also write the dataset in another format; repeat for several. `csv`, `geojson`, `json-columns` or `json-rows`; see [Formats](#formats). Parquet is always written. |

### Settings in the file

These go into the observations file's `chap.*` metadata, which Chap reads as the dataset's
settings.

| Option | Default | What it does |
| --- | --- | --- |
| `--masked START:END` | | Hide the target between two periods, for example `--masked 201801:201803`, as a dataset with known bad data would. Repeat for several ranges. |
| `--no-metadata` | | Write no `chap.*` settings. Chap then names the dataset after the file and uses its defaults. |
| `--spec-version VERSION` | 1 | The file format version written to the file. Chap only reads version 1, so anything else is refused. |
| `--about TEXT` | | A description stored in `expected.json`. Without it, one is made from the settings. |

### Org units Chap must reject

Chap accepts the dataset but leaves these org units out, and says which and why.
`expected.json` counts them as rejected.

| Option | Default | What it does |
| --- | --- | --- |
| `--covariate-gaps N` | 0 | The first N org units each miss one value in the last value column. Chap rejects an org unit with a gap in a covariate. |
| `--drop-locations N` | 0 | The last N org units have data but no location in the locations file. Chap rejects an org unit it cannot place on the map. |

### Files Chap must refuse

Chap refuses the whole upload with an error (HTTP 422). `expected.json` holds the error to expect.

| Option | Default | What it does |
| --- | --- | --- |
| `--duplicate-rows N` | 0 | The first N rows are written twice, so an org unit has two values for the same period. |
| `--text-column NAME` | | Adds a column with this name holding text instead of numbers. |
| `--drop-time-period` | | Leaves out the `time_period` column, so Chap cannot tell when the values are from. |
| `--not-parquet` | | Writes a CSV file named `observations.parquet`, as a wrongly saved file would be. |

### Reproducing a dataset

| Option | Default | What it does |
| --- | --- | --- |
| `--seed N` | random | The same seed and options always give the same files. Without it a random seed is used, and `expected.json` records it, so you can make the same dataset again. |
| `--out FOLDER` | `datasets` | The folder the dataset folder is written in. |

The observations are written in batches of org units, so memory stays small: 52 million rows
take about 25 s and 650 MB. The other formats are converted from the Parquet files in batches
too.

## Formats

| `--format` | Files |
| --- | --- |
| (always) | `observations.parquet`, `locations.parquet`, and `parents.geojson`: the parent areas the org units lie in |
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
- **Parents** are written to `parents.geojson`, so the org units can be checked against them: for
  facilities the districts they lie in, for districts the regions of about 50 neighbours they
  make up. Every org unit lies inside the parent its `parent` column names.
- Polygons follow the GeoJSON right-hand rule (RFC 7946): outer rings run counter-clockwise.
