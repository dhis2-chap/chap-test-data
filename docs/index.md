# chap-test-data

Made-up datasets for [Chap](https://chap.dhis2.org), in any size, and the tools to send them to
Chap and check its answers.

- **Generate** datasets from 10 to 100,000 org units over any number of years, weekly or
  monthly, with case counts, covariates and climate data.
- **Know the answer in advance.** Each dataset comes with an `expected.json` saying what Chap
  should answer, including for the files it must refuse.
- **Upload and check** against a running Chap, straight or through DHIS2, with the
  `chap-test-data` command or with plain curl.
- **Compare** the new Parquet upload with the JSON the Modeling App sends today, on a fast link
  or a slow, distant one.

![Generated districts and facilities](assets/locations.png)

## In one minute

```bash
git clone https://github.com/dhis2-chap/chap-test-data && cd chap-test-data
uv sync
# 16 ready-made datasets in datasets/
scripts/generate-ready-made.sh --standard-only
uv run chap-test-data generate my-country --org-units 300 \
  --geometry polygon --format geojson
# needs a running Chap; see Getting started
uv run chap-test-data check
```

## Words used here

| Word | Meaning |
| --- | --- |
| org unit | A place data is reported for, as DHIS2 calls it: a district, or a health facility. |
| target | The value a model predicts: the case counts, `disease_cases` unless you name the columns yourself. |
| covariate | Any other value column a model can use, such as rainfall or temperature. |
| period | One week (`2016W01`) or one month (`201601`) of data. |
| Parquet | A compact file format for tables. GeoParquet is the same with a map shape per row. |
| route | DHIS2's way of passing requests on to another service. The Modeling App reaches Chap through one. |
| dry run | An upload Chap only checks: it answers what it would import, and stores nothing. |

## A dataset

Every dataset is a folder, named after the dataset, holding the same data in several files:

| File | What it holds |
| --- | --- |
| `observations.parquet` | One row per org unit and period: `location` (the org unit's id), `time_period`, then one number column per value. The dataset's settings, such as its name, are stored inside the file. |
| `locations.parquet` | One row per org unit: its id, `name`, `parent` (the area it lies in), `level` (3 for districts, 4 for facilities) and its point or shape on the map. |
| `locations.geojson` | The same locations as GeoJSON, which most map tools open. |
| `hierarchy.geojson` | The areas above the org units, as in DHIS2: the country (level 1), its regions (2) and, for facilities, their districts (3). Each has a `parent` one level up. |
| `make-dataset.columns.json` | The same dataset as the JSON the Modeling App sends today. |
| `expected.json` | What Chap should answer to a dry run of the Parquet files, and the seed the dataset was made with. |

`observations.parquet`, `locations.parquet`, `hierarchy.geojson` and `expected.json` are always
written; the others when you ask for them with `--format`, as the ready-made datasets do. The
file format is described in chap-core's
[dataset files documentation](https://github.com/dhis2-chap/chap-core/blob/feat/dataset-parquet-upload/docs/webapi/dataset-files.md).
