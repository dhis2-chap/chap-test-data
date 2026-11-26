# Getting started

## Install

You need [uv](https://docs.astral.sh/uv/) and Python 3.13 (uv installs it for you).

```bash
git clone https://github.com/dhis2-chap/chap-test-data && cd chap-test-data
uv sync
uv run chap-test-data --help
```

Generating datasets needs nothing else. Uploading needs a running Chap, and the DHIS2 route a
running DHIS2; both run in Docker.

## Start Chap

The Parquet upload is on the chap-core branch `feat/dataset-parquet-upload`:

```bash
cd ../chap-core
git switch feat/dataset-parquet-upload
docker compose -p chap-test-data up -d --build
curl localhost:8000/health
```

The project name `chap-test-data` keeps this stack and its volumes apart from any other Chap you
run. Chap answers on `http://localhost:8000`, without a token unless `CHAP_API_TOKEN` is set in
chap-core's `.env`.

## Start DHIS2 (for the route)

`dhis2/` holds a DHIS2 that joins Chap's Docker network, and a script that creates the route
`chap` pointing at Chap. The first start takes a minute or two.

```bash
cd dhis2
docker compose up -d          # DHIS2 2.43.2.1
./setup-route.sh              # waits for DHIS2, then creates the route chap -> http://chap:8000/**
cd ..
```

Another DHIS2 version: `DHIS2_TAG=2.42.7.1 docker compose up -d`, after `docker compose down -v`
so the database starts fresh. For a DHIS2 elsewhere, set the connection settings below and make
sure it allows the route's target in `route.remote_servers_allowed`.

## Connection settings

Every command that talks to Chap takes these as options or environment variables:

| Variable | Default |
| --- | --- |
| `CHAP_URL` | `http://localhost:8000` |
| `CHAP_API_TOKEN` | none |
| `DHIS2_URL` | `http://localhost:8080` |
| `DHIS2_USER`, `DHIS2_PASSWORD` | `admin`, `district` |
| `ROUTE_CODE` | `chap` |

## Stop

```bash
cd dhis2 && docker compose down -v && cd ..
cd ../chap-core && docker compose -p chap-test-data down -v
```

## Developing

`make lint` runs ruff, mypy and pyright, the same tools as chap-core. `make test` runs the
tests, which need no running Chap. `make docs` builds this site, and `make build` the package.
CI runs them on every push.
