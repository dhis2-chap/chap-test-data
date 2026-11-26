# Comparing with JSON

Today the Modeling App sends a dataset to Chap as JSON, to Chap's `make-dataset` endpoint. This
page compares that with sending the same data as Parquet files: how large the upload is, and how
long it takes.

## On one machine

`compare` uploads the same dataset in three forms to the same Chap, and prints a table of their
sizes and times:

| Form | What is sent |
| --- | --- |
| `parquet` | The dataset's Parquet files, to Chap's new upload. |
| `json-columns` | A JSON body with one list per column, as the Modeling App sends today. |
| `json-rows` | A JSON body with one object per value, an older form. |

The JSON bodies hold the same data, settings and locations as the Parquet files.

```bash
uv run chap-test-data compare 02-district-weekly 03-facility-points \
  --dry-run --repeat 3
uv run chap-test-data compare 03-facility-points --dhis2 --dry-run \
  --format parquet --format json-columns
uv run chap-test-data compare 03-facility-points --wait
```

| Option | What it does |
| --- | --- |
| `DATASET ...` | The datasets to compare, by folder name. |
| `--all` | Compare every dataset Chap should import, not the ones it must refuse. This includes a dataset of a million rows, whose one-object-per-value JSON is several GB. |
| `--format FORM` | Only these forms: `parquet`, `json-columns` or `json-rows`. Repeat for several; default all three. |
| `--dry-run` | Only check; Chap stores nothing. The times are then Chap's checking only. |
| `--wait` | After each real import, wait until Chap has stored the dataset and report how long that took. |
| `--repeat N` | Upload each form N times and report the middle (median) time. Default 1. |
| `--dhis2` | Go through the DHIS2 route instead of straight to Chap. |
| `--bandwidth MBIT` | Send no faster than this many Mbit/s. |
| `--root FOLDER` | The folder holding the dataset folders. Default `datasets`. |
| `--results FILE` | A Markdown file the table is added to. Default `results/compare.md`. |

Results for dry runs straight to Chap on a laptop, the middle of 3 runs:

| Dataset | Form | Upload size | Time |
| --- | --- | --- | --- |
| 1,500 facilities x 365 weeks | Parquet | 3.8 MB | 0.98 s |
| | JSON columns | 31.4 MB (8.2x) | 1.37 s (1.4x) |
| | JSON rows | 211.5 MB (55x) | 15.18 s (15.5x) |
| 2,000 facilities x 365 weeks | Parquet | 5.1 MB | 1.30 s |
| | JSON columns | 41.9 MB (8.2x) | 1.87 s (1.4x) |
| | JSON rows | 282.0 MB (55x) | 20.66 s (15.9x) |
| 1,500 areas, 2,048 points per border | Parquet | 40.8 MB | 10.57 s |
| | JSON columns | 158.1 MB (3.9x) | 13.00 s (1.2x) |
| | JSON rows | 338.2 MB (8.3x) | 26.14 s (2.5x) |
| 150 districts x 365 weeks | Parquet | 1.2 MB | 0.43 s |
| | JSON columns | 6.3 MB (5.1x) | 0.40 s (0.9x) |
| | JSON rows | 24.3 MB (20x) | 1.92 s (4.4x) |

- **Size:** for facilities, the Parquet upload is about 8 times smaller than today's JSON. How
  much smaller depends on the data: smooth values pack tighter than noisy ones. With detailed
  areas the shapes make up most of the upload, and the gap narrows to about 4 times.
- **Time:** Chap checks Parquet 1.2 to 1.4 times faster. For small datasets the two are about the
  same.
- **Storing** takes the same time whatever form the data came in (about a minute for 1,500
  facilities), because Chap stores all three the same way.

## Over a real network

On one machine, sending costs almost nothing. In real use the upload travels from the user's
browser to DHIS2 and on to Chap, often over a slow or distant connection, and then the size of
the upload is what counts.

`slow-link.sh` measures that. It sends the upload from a small Docker container whose connection
is slowed down for real: each round trip is delayed, and the speed is capped.

```bash
./slow-link.sh --delay 100ms --rate 10mbit --dry-run datasets/03-facility-points
./slow-link.sh --delay 100ms --rate 10mbit --dry-run \
  --json datasets/03-facility-points
./slow-link.sh --delay 300ms --rate 2mbit --dhis2 \
  --dry-run datasets/03-facility-points
```

| Option | What it does |
| --- | --- |
| `--delay TIME` | The delay added to each round trip, such as `100ms` for a distant server. Default `100ms`. |
| `--rate SPEED` | The upload speed, such as `10mbit` or `2mbit`. Default `10mbit`. |
| `--dry-run`, `--dhis2`, `--json` | As for `upload.sh`: only check, go through DHIS2, or send the JSON instead of Parquet. |

It needs Chap running as in [Getting started](getting-started.md), and DHIS2 for `--dhis2`.

Results for 1,500 facilities of weekly data over 7 years, through DHIS2, only checking:

| Connection | Parquet (3.8 MB) | Today's JSON (31.4 MB) | JSON takes |
| --- | --- | --- | --- |
| Same machine | 1.1 s | 1.4 s | 1.2 times as long |
| 50 Mbit/s, 20 ms delay | 1.9 s | 6.7 s | 3.6 times |
| 20 Mbit/s, 50 ms delay | 3.1 s | 14.7 s | 4.8 times |
| 10 Mbit/s, 100 ms delay | 5.0 s | 28.1 s | 5.6 times |
| 2 Mbit/s, 300 ms delay | 18.9 s | 134.1 s | 7.1 times |

Straight to Chap, without DHIS2, the times are within a tenth of a second of these.

- **The slower the connection, the bigger the gain,** up to the 8 times smaller upload: on a fast
  connection Chap's own work takes most of the time, on a slow one the sending does.
- **Uploading is the slow direction.** Many connections send far slower than they receive, and
  a dataset is sent.
- **The JSON cannot be shrunk on the way.** Browsers do not compress what they send, and DHIS2
  routes remove compression, so the 8 times difference is what travels.
- **The route's timeout starts once the upload has arrived,** so a slow upload does not fail, but
  the user waits for all of it.
