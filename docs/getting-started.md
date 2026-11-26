# Getting started

## Install

You need [uv](https://docs.astral.sh/uv/), which also installs the Python version it needs (3.13).

```bash
git clone https://github.com/dhis2-chap/chap-test-data && cd chap-test-data
uv sync
uv run chap-test-data --help
```

That is all you need to generate datasets. To upload them you also need a running Chap, and to
upload through DHIS2 a running DHIS2. Both run in Docker, as below.

## Start Chap

The Parquet upload is on the chap-core branch `feat/dataset-parquet-upload`. From a chap-core
checkout next to this one:

```bash
cd ../chap-core
git switch feat/dataset-parquet-upload
docker compose -p chap-test-data up -d --build
curl localhost:8000/health
```

`-p chap-test-data` gives this Chap its own name in Docker, so it and its data stay apart from
any other Chap you run. It answers on `http://localhost:8000`, without a token unless
`CHAP_API_TOKEN` is set in chap-core's `.env`.

## Start DHIS2

The Modeling App does not talk to Chap directly: it goes through a DHIS2 route, which passes its
requests on to Chap. To test that path, `dhis2/` holds a DHIS2 that runs next to Chap, and a
script that creates a route named `chap` pointing at it. The first start takes a minute or two.

```bash
cd dhis2
docker compose up -d          # DHIS2 2.43.2.1
# waits until DHIS2 is up, then creates the route chap -> http://chap:8000/**
./setup-route.sh
cd ..
```

For another DHIS2 version, remove the old one with its data first:
`docker compose down -v`, then `DHIS2_TAG=2.42.7.1 docker compose up -d`. To use a DHIS2 that
runs elsewhere, point the connection settings below at it, and make sure it allows the route's
address in its `route.remote_servers_allowed` setting.

## Connection settings

`upload`, `check` and `compare` find Chap and DHIS2 through these settings. Each can be given as
an option before the command (`uv run chap-test-data --chap-url http://... check`) or as an
environment variable.

| Option | Environment variable | Default | What it is |
| --- | --- | --- | --- |
| `--chap-url` | `CHAP_URL` | `http://localhost:8000` | Where Chap's API answers. |
| `--chap-token` | `CHAP_API_TOKEN` | none | Chap's API token, if Chap is set up to require one. |
| `--dhis2-url` | `DHIS2_URL` | `http://localhost:8080` | Where DHIS2 answers, for uploads with `--dhis2`. |
| `--dhis2-user` | `DHIS2_USER` | `admin` | The DHIS2 user name. |
| `--dhis2-password` | `DHIS2_PASSWORD` | `district` | The DHIS2 password. |
| `--route-code` | `ROUTE_CODE` | `chap` | The code of the DHIS2 route that passes requests on to Chap. |

The curl scripts read the same environment variables.

## Stop

This removes both, with their data:

```bash
cd dhis2 && docker compose down -v && cd ..
cd ../chap-core && docker compose -p chap-test-data down -v
```

## Developing

| Command | What it does |
| --- | --- |
| `make lint` | Fixes and checks the code style, and checks the types (ruff, mypy and pyright, as chap-core). |
| `make test` | Runs the tests. They need no running Chap. |
| `make docs` | Builds this site into `site/`. `make docs-serve` shows it at http://127.0.0.1:8000 while you edit. |
| `make build` | Builds the package. |

CI runs them on every push.
