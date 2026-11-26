
### 2026-11-25 21:32, direct, dry run

| Dataset | Format | Body | Body vs Parquet | HTTP | Request | Request vs Parquet | Worker | Imported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01-small-monthly | parquet | 0.03 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 10 |
| 01-small-monthly | json-columns | 0.05 MB | 1.7x | 200 | 0.01 s | 0.3x |  | 10 |
| 01-small-monthly | json-rows | 0.16 MB | 5.8x | 200 | 0.02 s | 0.5x |  | 10 |
| 02-district-weekly | parquet | 1.02 MB | 1.0x | 200 | 0.34 s | 1.0x |  | 150 |
| 02-district-weekly | json-columns | 6.03 MB | 5.9x | 200 | 0.42 s | 1.3x |  | 150 |
| 02-district-weekly | json-rows | 24.05 MB | 23.5x | 200 | 2.00 s | 5.9x |  | 150 |
| 03-facility-points | parquet | 2.02 MB | 1.0x | 200 | 0.98 s | 1.0x |  | 1500 |
| 03-facility-points | json-columns | 29.02 MB | 14.4x | 200 | 1.42 s | 1.5x |  | 1500 |
| 03-facility-points | json-rows | 209.15 MB | 103.6x | 200 | 16.16 s | 16.5x |  | 1500 |
| 04-facility-polygons | parquet | 37.35 MB | 1.0x | 200 | 10.10 s | 1.0x |  | 1500 |
| 04-facility-polygons | json-columns | 154.61 MB | 4.1x | 200 | 12.63 s | 1.3x |  | 1500 |
| 04-facility-polygons | json-rows | 334.74 MB | 9.0x | 200 | 26.03 s | 2.6x |  | 1500 |
| 05-facility-points-2000 | parquet | 2.68 MB | 1.0x | 200 | 1.30 s | 1.0x |  | 2000 |
| 05-facility-points-2000 | json-columns | 38.70 MB | 14.4x | 200 | 1.82 s | 1.4x |  | 2000 |
| 05-facility-points-2000 | json-rows | 278.87 MB | 104.0x | 200 | 21.14 s | 16.3x |  | 2000 |
| 06-geojson-locations | parquet | 0.17 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 50 |
| 06-geojson-locations | json-columns | 0.41 MB | 2.5x | 200 | 0.04 s | 1.1x |  | 50 |
| 06-geojson-locations | json-rows | 2.12 MB | 12.7x | 200 | 0.14 s | 3.6x |  | 50 |
| 07-masked-ranges | parquet | 0.04 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 20 |
| 07-masked-ranges | json-columns | 0.09 MB | 2.6x | 200 | 0.02 s | 0.4x |  | 20 |
| 07-masked-ranges | json-rows | 0.33 MB | 9.0x | 200 | 0.03 s | 0.8x |  | 20 |
| 08-no-metadata | parquet | 0.03 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 10 |
| 08-no-metadata | json-columns | 0.04 MB | 1.6x | 200 | 0.01 s | 0.3x |  | 10 |
| 08-no-metadata | json-rows | 0.12 MB | 4.5x | 200 | 0.02 s | 0.4x |  | 10 |
| 09-covariate-gaps | parquet | 0.04 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 17 |
| 09-covariate-gaps | json-columns | 0.09 MB | 2.6x | 200 | 0.02 s | 0.5x |  | 17 |
| 09-covariate-gaps | json-rows | 0.33 MB | 9.1x | 200 | 0.03 s | 0.8x |  | 17 |
| 10-missing-polygons | parquet | 0.03 MB | 1.0x | 200 | 0.04 s | 1.0x |  | 16 |
| 10-missing-polygons | json-columns | 0.08 MB | 2.4x | 200 | 0.02 s | 0.4x |  | 16 |
| 10-missing-polygons | json-rows | 0.32 MB | 9.4x | 200 | 0.04 s | 0.9x |  | 16 |

### 2026-11-25 21:38, through DHIS2, dry run

| Dataset | Format | Body | Body vs Parquet | HTTP | Request | Request vs Parquet | Worker | Imported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01-small-monthly | parquet | 0.03 MB | 1.0x | 200 | 0.14 s | 1.0x |  | 10 |
| 01-small-monthly | json-columns | 0.05 MB | 1.7x | 200 | 0.11 s | 0.8x |  | 10 |
| 01-small-monthly | json-rows | 0.16 MB | 5.8x | 200 | 0.12 s | 0.8x |  | 10 |
| 02-district-weekly | parquet | 1.02 MB | 1.0x | 200 | 0.47 s | 1.0x |  | 150 |
| 02-district-weekly | json-columns | 6.03 MB | 5.9x | 200 | 0.49 s | 1.0x |  | 150 |
| 02-district-weekly | json-rows | 24.05 MB | 23.5x | 200 | 2.08 s | 4.4x |  | 150 |
| 03-facility-points | parquet | 2.02 MB | 1.0x | 200 | 1.09 s | 1.0x |  | 1500 |
| 03-facility-points | json-columns | 29.02 MB | 14.4x | 200 | 1.45 s | 1.3x |  | 1500 |
| 03-facility-points | json-rows | 209.15 MB | 103.6x | 200 | 15.73 s | 14.5x |  | 1500 |
| 04-facility-polygons | parquet | 37.35 MB | 1.0x | 200 | 10.56 s | 1.0x |  | 1500 |
| 04-facility-polygons | json-columns | 154.61 MB | 4.1x | 200 | 12.99 s | 1.2x |  | 1500 |
| 04-facility-polygons | json-rows | 334.74 MB | 9.0x | 200 | 26.32 s | 2.5x |  | 1500 |
| 05-facility-points-2000 | parquet | 2.68 MB | 1.0x | 200 | 1.39 s | 1.0x |  | 2000 |
| 05-facility-points-2000 | json-columns | 38.70 MB | 14.4x | 200 | 1.96 s | 1.4x |  | 2000 |
| 05-facility-points-2000 | json-rows | 278.87 MB | 104.0x | 200 | 20.77 s | 14.9x |  | 2000 |
| 06-geojson-locations | parquet | 0.17 MB | 1.0x | 200 | 0.13 s | 1.0x |  | 50 |
| 06-geojson-locations | json-columns | 0.41 MB | 2.5x | 200 | 0.13 s | 1.0x |  | 50 |
| 06-geojson-locations | json-rows | 2.12 MB | 12.7x | 200 | 0.23 s | 1.8x |  | 50 |
| 07-masked-ranges | parquet | 0.04 MB | 1.0x | 200 | 0.13 s | 1.0x |  | 20 |
| 07-masked-ranges | json-columns | 0.09 MB | 2.6x | 200 | 0.11 s | 0.8x |  | 20 |
| 07-masked-ranges | json-rows | 0.33 MB | 9.0x | 200 | 0.12 s | 0.9x |  | 20 |
| 08-no-metadata | parquet | 0.03 MB | 1.0x | 200 | 0.13 s | 1.0x |  | 10 |
| 08-no-metadata | json-columns | 0.04 MB | 1.6x | 200 | 0.10 s | 0.8x |  | 10 |
| 08-no-metadata | json-rows | 0.12 MB | 4.5x | 200 | 0.11 s | 0.9x |  | 10 |
| 09-covariate-gaps | parquet | 0.04 MB | 1.0x | 200 | 0.13 s | 1.0x |  | 17 |
| 09-covariate-gaps | json-columns | 0.09 MB | 2.6x | 200 | 0.11 s | 0.8x |  | 17 |
| 09-covariate-gaps | json-rows | 0.33 MB | 9.1x | 200 | 0.12 s | 0.9x |  | 17 |
| 10-missing-polygons | parquet | 0.03 MB | 1.0x | 200 | 0.13 s | 1.0x |  | 16 |
| 10-missing-polygons | json-columns | 0.08 MB | 2.4x | 200 | 0.11 s | 0.8x |  | 16 |
| 10-missing-polygons | json-rows | 0.32 MB | 9.4x | 200 | 0.12 s | 0.9x |  | 16 |

### 2026-11-25 21:43, direct, import

| Dataset | Format | Body | Body vs Parquet | HTTP | Request | Request vs Parquet | Worker | Imported |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01-small-monthly | parquet | 0.03 MB | 1.0x | 200 | 0.09 s | 1.0x | 0.2 s | 10 |
| 01-small-monthly | json-columns | 0.05 MB | 1.7x | 200 | 0.03 s | 0.3x | 0.2 s | 10 |
| 01-small-monthly | json-rows | 0.16 MB | 5.8x | 200 | 0.06 s | 0.6x | 0.2 s | 10 |
| 02-district-weekly | parquet | 1.02 MB | 1.0x | 200 | 0.94 s | 1.0x | 6.3 s | 150 |
| 02-district-weekly | json-columns | 6.03 MB | 5.9x | 200 | 0.97 s | 1.0x | 6.4 s | 150 |
| 02-district-weekly | json-rows | 24.05 MB | 23.5x | 200 | 2.69 s | 2.9x | 6.4 s | 150 |
| 03-facility-points | parquet | 2.02 MB | 1.0x | 200 | 4.13 s | 1.0x | 54.2 s | 1500 |
| 03-facility-points | json-columns | 29.02 MB | 14.4x | 200 | 5.03 s | 1.2x | 53.9 s | 1500 |
| 03-facility-points | json-rows | 209.15 MB | 103.6x | 200 | 20.86 s | 5.1x | 52.8 s | 1500 |
| 04-facility-polygons | parquet | 37.35 MB | 1.0x | 200 | 18.88 s | 1.0x | 85.9 s | 1500 |
| 04-facility-polygons | json-columns | 154.61 MB | 4.1x | 200 | 23.90 s | 1.3x | 86.4 s | 1500 |
| 04-facility-polygons | json-rows | 334.74 MB | 9.0x | 200 | 39.26 s | 2.1x | 88.6 s | 1500 |
| 05-facility-points-2000 | parquet | 2.68 MB | 1.0x | 200 | 5.42 s | 1.0x | 70.0 s | 2000 |
| 05-facility-points-2000 | json-columns | 38.70 MB | 14.4x | 200 | 6.55 s | 1.2x | 74.0 s | 2000 |
| 05-facility-points-2000 | json-rows | 278.87 MB | 104.0x | 200 | 26.14 s | 4.8x | 72.7 s | 2000 |
| 06-geojson-locations | parquet | 0.17 MB | 1.0x | 200 | 0.10 s | 1.0x | 0.8 s | 50 |
| 06-geojson-locations | json-columns | 0.41 MB | 2.5x | 200 | 0.12 s | 1.1x | 0.7 s | 50 |
| 06-geojson-locations | json-rows | 2.12 MB | 12.7x | 200 | 0.20 s | 2.0x | 0.7 s | 50 |
| 07-masked-ranges | parquet | 0.04 MB | 1.0x | 200 | 0.06 s | 1.0x | 0.2 s | 20 |
| 07-masked-ranges | json-columns | 0.09 MB | 2.6x | 200 | 0.05 s | 1.0x | 0.2 s | 20 |
| 07-masked-ranges | json-rows | 0.33 MB | 9.0x | 200 | 0.07 s | 1.3x | 0.2 s | 20 |
| 08-no-metadata | parquet | 0.03 MB | 1.0x | 200 | 0.05 s | 1.0x | 0.2 s | 10 |
| 08-no-metadata | json-columns | 0.04 MB | 1.6x | 200 | 0.02 s | 0.4x | 0.2 s | 10 |
| 08-no-metadata | json-rows | 0.12 MB | 4.5x | 200 | 0.05 s | 1.1x | 0.2 s | 10 |
| 09-covariate-gaps | parquet | 0.04 MB | 1.0x | 200 | 0.06 s | 1.0x | 0.2 s | 17 |
| 09-covariate-gaps | json-columns | 0.09 MB | 2.6x | 200 | 0.05 s | 1.0x | 0.2 s | 17 |
| 09-covariate-gaps | json-rows | 0.33 MB | 9.1x | 200 | 0.07 s | 1.3x | 0.2 s | 17 |
| 10-missing-polygons | parquet | 0.03 MB | 1.0x | 200 | 0.08 s | 1.0x | 0.2 s | 16 |
| 10-missing-polygons | json-columns | 0.08 MB | 2.4x | 200 | 0.05 s | 0.6x | 0.2 s | 16 |
| 10-missing-polygons | json-rows | 0.32 MB | 9.4x | 200 | 0.06 s | 0.8x | 0.2 s | 16 |
