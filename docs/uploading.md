# Uploading and checking

Start Chap first (see [Getting started](getting-started.md)).

## One dataset

```bash
uv run chap-test-data upload --dry-run datasets/03-facility-points   # validate only
uv run chap-test-data upload --wait datasets/03-facility-points      # import, and wait for the job
```

## Every dataset against its expected answer

```bash
uv run chap-test-data check                    # every folder in datasets/
uv run chap-test-data check --dhis2            # the same through the DHIS2 route
```

`check` dry-runs each dataset and compares Chap's answer with the folder's `expected.json`:
how many org units it imports and rejects, or which error it gives.

## Through a DHIS2 route

`--dhis2` sends the upload to DHIS2's route API, which forwards it to Chap, as the Modeling App
does. DHIS2 2.42.3 and later forward each file twice
([DHIS2-22596](https://dhis2.atlassian.net/browse/DHIS2-22596)); Chap ignores the extra copies,
so the result is the same as without DHIS2. Tested on DHIS2 2.41.11, 2.42.7.1 and 2.43.2.1.

## With curl

The same, without Python:

```bash
./upload.sh --dry-run datasets/03-facility-points
./upload.sh --dry-run --json datasets/03-facility-points     # the make-dataset JSON body instead
./upload.sh --dhis2 --dry-run datasets/03-facility-points
./check-all.sh                                               # every dataset against expected.json

curl -X POST "http://localhost:8000/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet

curl -u admin:district -X POST \
  "http://localhost:8080/api/routes/chap/run/v1/crud/datasets/files?dryRun=true" \
  -F observations=@datasets/03-facility-points/observations.parquet \
  -F locations=@datasets/03-facility-points/locations.parquet
```

With a token, add `-H "Authorization: Bearer ..."` to curl, or set `CHAP_API_TOKEN`.

## Results

Measured on a MacBook with Docker Desktop, chap-core `feat/dataset-parquet-upload`:

- Every dataset gave the expected answer, directly and through DHIS2 routes on 2.41.11, 2.42.7.1
  and 2.43.2.1, and a real import of `03-facility-points` succeeded through each.
- Real imports took 4 to 6 s for the request at 1,500 to 2,000 facilities, and about 20 s with
  large polygons, where checking the geometry takes most of the time. The worker then stores the
  data in the background: 54 s at 1,500 facilities, 70 s at 2,000.
- The DHIS2 route's timeout (30 s in the Modeling App, 60 s at most) counts from the end of the
  upload, so a slow upload does not use it up.
