# Timing the checks

Today Chap stores a dataset one value per database row, in the background after the upload.
Chap is moving to keeping each dataset as its Parquet files instead. Then an upload could be
checked and stored while the user waits, if checking the files is fast enough.

`time-checks` answers that. It runs the checks Chap would make on each dataset folder you give
it, straight on the files and without Chap, and says how long each took and what it found:

| Check | What it looks for |
| --- | --- |
| duplicate (location, time_period) | A location with more than one row for the same period |
| periods per location, first and last | How many periods each location has, and its first and last |
| locations with a covariate gap | Locations missing a value in a covariate |
| locations missing from locations | Locations with data but no location |

```bash
uv run chap-test-data time-checks \
  datasets/21-facilities-20k-weekly-10y datasets/23-locations-100k-weekly-10y
```

| Option | What it does |
| --- | --- |
| `FOLDER ...` | The dataset folders to check. |
| `--memory-limit SIZE` | The most memory the checks may use, such as `1GB` (the default). Beyond it they use the disk instead, so a large dataset is slower but does not run out of memory. |

The checks run on DuckDB, a database that reads Parquet files directly; it stands in for
whatever Chap ends up using.

Results on a laptop with 12 cores:

| Dataset | All checks | Memory used at most |
| --- | --- | --- |
| 20,000 facilities, 10 years weekly: 10.4 million rows | 0.2 s | about 0.9 GB |
| 100,000 locations, 10 years weekly: 52.2 million rows | 3.7 s | about 1.6 GB |

Nearly all of the time goes to looking for duplicates. Even the largest dataset is checked in a
few seconds, well within the time a DHIS2 route waits for an answer.
