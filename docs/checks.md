# Timing the checks

Once Chap stores datasets as files (Phase 2), an upload can be checked straight on the files,
without a background worker. `time-checks` runs those checks on dataset folders, without Chap,
and times each one:

- duplicate rows for one org unit and period
- periods per org unit, first and last
- org units with a gap in a covariate
- org units missing from the locations file

```bash
uv run chap-test-data time-checks datasets/21-facilities-20k-weekly-10y datasets/23-org-units-100k-weekly-10y
```

It uses DuckDB to measure; which engine Chap will use is not decided. `--memory-limit` caps
DuckDB's memory (default 1 GB); above it, DuckDB spills to disk.

On a 12-core MacBook (2026-11-26):

| Rows | All checks | Peak memory |
| --- | --- | --- |
| 10.4 million (20,000 facilities, 10 years weekly) | 0.2 s | about 0.9 GB |
| 52.2 million (100,000 org units, 10 years weekly) | 3.7 s | about 1.6 GB |

Nearly all the time goes to the duplicate check. Even the largest dataset is checked well within
a DHIS2 route's timeout.
