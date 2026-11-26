# About

chap-test-data is part of [Chap](https://chap.dhis2.org), the Climate and Health modelling
platform built around DHIS2. Chap forecasts climate-sensitive diseases such as malaria and
dengue from health data reported in DHIS2 and from climate data, and helps countries judge how
far those forecasts can be trusted.

## Why it exists

Chap is moving from datasets sent as JSON and stored one value per database row to datasets sent
and stored as Parquet files. Testing that needs data in every size, from a handful of districts
to 100,000 org units over ten years, and in every shape Chap must accept, reject in part or
refuse. Real DHIS2 data cannot be shared freely and does not come in every size, so this tool
generates it: realistic enough to behave like the real thing, with the answer Chap should give
known in advance.

It is also how the Parquet upload was measured: how much smaller and faster it is than today's
JSON, directly and through DHIS2 routes, on fast and on slow, distant links.

## Related projects

| Project | What it is |
| --- | --- |
| [chap-core](https://github.com/dhis2-chap/chap-core) | The Chap platform: the API, the database, model runs and evaluation |
| [chapkit](https://github.com/dhis2-chap/chapkit) | The toolkit for building Chap models as services; its test data generator sets the value ranges used here |
| [Chap documentation](https://chap.dhis2.org) | The Chap project, its models and how to use the Modeling App |

## Contributing

Issues and pull requests are welcome on
[GitHub](https://github.com/dhis2-chap/chap-test-data). Run `make lint` and `make test` before
you push; CI runs both, and builds the package and this site.

## License

[GNU Affero General Public License v3](https://github.com/dhis2-chap/chap-test-data/blob/main/LICENSE),
as chap-core. The generated data is synthetic and free to use.
