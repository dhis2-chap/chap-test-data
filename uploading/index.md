# Uploading and checking

Start Chap first, and DHIS2 too if you want to go through it (see [Getting started](https://dhis2-chap.github.io/chap-test-data/getting-started/index.md)).

## Upload one dataset

```
# only check
uv run chap-test-data upload --dry-run datasets/03-facility-points
# import, and wait until stored
uv run chap-test-data upload --wait datasets/03-facility-points
```

`upload` sends the dataset folder's `observations.parquet` and its locations file to Chap, and prints Chap's answer: how many locations it will import, which it rejects and why, or the error if it refuses the files.

| Option             | What it does                                                                                                                                                                                                                                        |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--dry-run`        | Only check: Chap answers what it would import and reject, and stores nothing.                                                                                                                                                                       |
| `--wait`           | After a real import, wait until Chap has stored the dataset, then print its id (`dataset id: 42`), or the error if storing failed. Storing runs after Chap has answered, and takes about a minute for 1,500 facilities of weekly data over 7 years. |
| `--dhis2`          | Send the upload through the DHIS2 route, as the Modeling App does, instead of straight to Chap.                                                                                                                                                     |
| `--bandwidth MBIT` | Send no faster than this many Mbit/s, to time the upload over a slow link. The time printed includes the sending. See [Comparing with JSON](https://dhis2-chap.github.io/chap-test-data/comparing/index.md) for a slow link with delay as well.     |

## Check every dataset

```
# every dataset folder in datasets/
uv run chap-test-data check
# the same through the DHIS2 route
uv run chap-test-data check --dhis2
# the dataset folders in another folder
uv run chap-test-data check my-datasets/
```

`check` dry-runs every dataset folder that has an `expected.json`, and compares Chap's answer with it: the number of locations imported and rejected, or the error Chap gives. It prints one line per dataset, `ok` or `FAIL`, and ends with an error if any dataset gave another answer.

| Option    | What it does                                                          |
| --------- | --------------------------------------------------------------------- |
| `FOLDER`  | The folder holding the dataset folders. Default `datasets`.           |
| `--dhis2` | Send the uploads through the DHIS2 route instead of straight to Chap. |

## Through DHIS2

With `--dhis2` the upload goes to DHIS2's route for Chap, which passes it on, as the Modeling App's uploads do. The answer is the same as without DHIS2. DHIS2 2.42.3 and later send each file on twice ([DHIS2-22596](https://dhis2.atlassian.net/browse/DHIS2-22596)); Chap uses one copy and ignores the other.

## With curl

The same, without Python: `scripts/upload-curl.sh` uploads one dataset and `scripts/check-curl.sh` checks them all.

```
scripts/upload-curl.sh --dry-run datasets/03-facility-points
scripts/upload-curl.sh --dry-run --json datasets/03-facility-points
scripts/upload-curl.sh --dhis2 --dry-run datasets/03-facility-points
scripts/upload-curl.sh --wait datasets/03-facility-points
scripts/check-curl.sh
scripts/check-curl.sh --dhis2
```

| Option           | Script                   | What it does                                                                                                                                              |
| ---------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--dry-run`      | `scripts/upload-curl.sh` | Only check; Chap stores nothing.                                                                                                                          |
| `--wait`         | `scripts/upload-curl.sh` | After a real import, wait until Chap has stored the dataset, then print its id.                                                                           |
| `--dhis2`        | both                     | Go through the DHIS2 route instead of straight to Chap.                                                                                                   |
| `--json`         | `scripts/upload-curl.sh` | Send the folder's `make-dataset.columns.json` to Chap's JSON endpoint instead, as the Modeling App does today. The dataset needs `--format json-columns`. |
| `BANDWIDTH=MBIT` | `scripts/upload-curl.sh` | An environment variable: send no faster than this many Mbit/s.                                                                                            |

Both read the [connection settings](https://dhis2-chap.github.io/chap-test-data/getting-started/#connection-settings) from the environment, and print each command they run, with the password and token hidden. Or with curl alone:

```
curl -X POST "http://localhost:8000/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet

ROUTE=http://localhost:8080/api/routes/chap/run
curl -u admin:district -X POST "$ROUTE/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet
```

If Chap needs a token, add `-H "Authorization: Bearer <token>"` to the first.

## How long it takes

Chap answers in 4 to 6 seconds for 1,500 to 2,000 facilities of weekly data over 7 years, and in about 20 seconds when the locations are detailed areas, because checking the shapes takes most of the time. It then stores the dataset in the background: about a minute for 1,500 facilities.

The DHIS2 route has a timeout (30 seconds in the Modeling App, 60 at most), but it only starts once the upload has arrived, so a slow upload does not use it up.
