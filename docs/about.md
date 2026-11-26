# About

chap-test-data is part of [Chap](https://chap.dhis2.org), the Climate and Health modelling
platform built around DHIS2. Chap forecasts climate-sensitive diseases such as malaria and
dengue from health data reported in DHIS2 and from climate data, and helps countries judge how
far those forecasts can be trusted.

## Why it exists

Chap is moving from datasets sent as JSON and stored one value per database row to datasets sent
and kept as Parquet files. Testing that needs data in every size, from a handful of districts to
100,000 org units over ten years, and in every shape Chap must accept, accept in part or refuse.
Real DHIS2 data cannot be shared freely and does not come in every size, so this tool makes it
up: close enough to real data to behave like it, with the answer Chap should give known in
advance.

It also measures what the change brings: how much smaller and faster Parquet uploads are than
today's JSON, straight to Chap and through DHIS2, on fast and on slow, distant connections.

## Related projects

| Project | What it is |
| --- | --- |
| [chap-core](https://github.com/dhis2-chap/chap-core) | The Chap platform: its API, database, model runs and evaluation. |
| [chapkit](https://github.com/dhis2-chap/chapkit) | The toolkit for building Chap models as services. Its test data sets the value ranges used here. |
| [Chap documentation](https://chap.dhis2.org) | The Chap project, its models and how to use the Modeling App. |

## Contributing

Issues and pull requests are welcome on
[GitHub](https://github.com/dhis2-chap/chap-test-data). Run `make lint` and `make test` before
you push; CI runs both, and builds the package and this site.

## License

[GNU Affero General Public License v3](https://github.com/dhis2-chap/chap-test-data/blob/main/LICENSE),
as chap-core. The datasets it makes are made up and free to use.
