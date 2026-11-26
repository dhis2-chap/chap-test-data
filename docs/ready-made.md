# Ready-made datasets

A set of datasets for testing Chap, made with one script: the usual sizes, the cases Chap must
reject or refuse, and a few very large ones.

```bash
scripts/generate-ready-made.sh                  # all, with the large ones: minutes
scripts/generate-ready-made.sh --standard-only  # the 16 standard ones: seconds
```

All of them, with the large ones, take a few GB. They are written to `datasets/` with a fixed seed (42), so they are the same on every machine.
Each is written as Parquet, as GeoJSON locations (`locations.geojson`) and as the JSON body the
Modeling App sends today (`make-dataset.columns.json`). The datasets Chap must refuse are written
as Parquet only.

## Standard

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

## Large

10 years with all 10 value columns. Only the first fits what Chap's Parquet upload accepts today;
the others are the sizes Chap's stored datasets are designed for.

| Dataset | Rows | Observations file | Expected answer |
| --- | --- | --- | --- |
| `20-phase1-max-weekly-10y` | 1,900 x 522 weeks = 991,800 | 15 MB | 1,900 imported |
| `21-facilities-20k-weekly-10y` | 20,000 x 522 = 10.4 million | 161 MB | 413: over Chap's 100 MB per-file limit |
| `22-org-units-100k-monthly-10y` | 100,000 x 120 = 12 million | 177 MB | 413: over Chap's 100 MB per-file limit |
| `23-org-units-100k-weekly-10y` | 100,000 x 522 = 52.2 million | 753 MB | 413: over Chap's 100 MB per-file limit |

The limits are Chap's own, not DHIS2's: its Parquet upload accepts up to 100 MB per file and
1 million rows. They keep one upload from taking too much of the API's memory, because Chap
reads the whole dataset into memory as it imports it. The file size is checked first, while the
upload arrives, so these three get 413 (too large); under 100 MB, 10 million rows would get 422
(too many rows) instead. A DHIS2 server may have its own size limit in front of it, such as
nginx's `client_max_body_size`, which also answers 413.

`23` gets no JSON body: it would be about 5 GB.

Each one is a single [`generate`](generating.md) command in `scripts/generate-ready-made.sh`, so a variation
of any of them is a matter of changing its options.
