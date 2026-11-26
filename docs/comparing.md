# Comparing with JSON

Today the Modeling App sends a dataset to Chap's `make-dataset` endpoint as JSON. This page
compares that with the Parquet upload, on the same data.

## On one machine

`compare` uploads each dataset three ways to the same Chap: as Parquet, as `make-dataset` JSON
with `providedDataColumns` (what the Modeling App sends today), and as `make-dataset` JSON with
`providedData` (one object per value, the older form). The JSON bodies carry the same settings
and locations as the Parquet files.

```bash
uv run chap-test-data compare 02-district-weekly 03-facility-points --dry-run --repeat 3
uv run chap-test-data compare 03-facility-points --dhis2 --dry-run --format parquet --format json-columns
uv run chap-test-data compare 03-facility-points --wait        # real import, with the worker's time
```

Dry runs directly to Chap, median of 3, on 2026-11-26:

| Dataset | Format | Body | Request |
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

- **Size:** at facility scale Parquet is about 8x smaller than today's JSON. How much depends on
  the data: smoother test data gave 14x, so real data may land in between. With large polygons
  the geometry dominates and the gap narrows to about 4x.
- **Server time:** Parquet is 1.2x to 1.4x faster. For small datasets the two are about even.
- **Worker:** the background import takes the same time for every format, because all three
  queue the same job (54 s at 1,500 facilities).

## Over a real network

On one machine sending costs almost nothing. In production the upload crosses a real network,
from the user's browser to DHIS2 and on to Chap, and there the size of the body counts.

`slow-link.sh` measures that. It runs the curl upload in a small container on Chap's Docker
network whose network interface is shaped with Linux `tc netem`: real delay on every round trip
and a capped rate, so TCP behaves as it does on a slow, distant link.

```bash
./slow-link.sh --delay 100ms --rate 10mbit --dry-run datasets/03-facility-points
./slow-link.sh --delay 100ms --rate 10mbit --dry-run --json datasets/03-facility-points
./slow-link.sh --delay 300ms --rate 2mbit --dhis2 --dry-run datasets/03-facility-points
```

`03-facility-points` (1,500 facilities x 365 weeks), a dry run through a DHIS2 2.43 route, on
2026-11-26:

| Link | Parquet (3.8 MB) | Today's JSON (31.4 MB) | JSON takes |
| --- | --- | --- | --- |
| Same machine | 1.1 s | 1.4 s | 1.2x as long |
| 50 Mbit/s, 20 ms delay | 1.9 s | 6.7 s | 3.6x |
| 20 Mbit/s, 50 ms delay | 3.1 s | 14.7 s | 4.8x |
| 10 Mbit/s, 100 ms delay | 5.0 s | 28.1 s | 5.6x |
| 2 Mbit/s, 300 ms delay | 18.9 s | 134.1 s | 7.1x |

Straight to Chap, without DHIS2, the times are within 0.1 s of these.

- **The slower the link, the closer the gain gets to the size difference.** On a fast link
  Chap's own work dominates; on a slow one sending does, and Parquet sends 8x fewer bytes.
- **The upload is the slow direction.** Many links upload far slower than they download, and a
  dataset goes up.
- **JSON cannot be compressed on the way.** Browsers do not compress request bodies, and DHIS2
  routes strip gzip, so the 8x difference stays 8x on the wire.
- **The DHIS2 route sends Parquet files twice to Chap** until
  [DHIS2-22596](https://dhis2.atlassian.net/browse/DHIS2-22596) is fixed. That leg is usually
  between servers, so it costs little: about 0.1 s here.
- **The route's timeout starts after the upload,** so a slow upload does not time out, but the
  user waits for every byte.

`chap-test-data upload` and `compare` also take `--bandwidth` (Mbit/s), which only paces the
sending, without delay. It needs no Docker but leaves out what latency does to TCP.
