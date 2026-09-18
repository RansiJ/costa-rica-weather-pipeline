# Costa Rica Weather Pipeline

[![CI](https://github.com/RansiJ/costa-rica-weather-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/RansiJ/costa-rica-weather-pipeline/actions/workflows/ci.yml)

An instrument-aware meteorological data-quality and harmonization pipeline for
heterogeneous observations from San Ramón, Costa Rica.

This project reconstructs a meteorological data-quality workflow originally
developed while working with observational data at CIGEFI-UCR. The original
institutional database is no longer available to the author; therefore, this
repository is based on surviving local exports, analysis artifacts, and work
logs and does not claim to reproduce the complete historical database.

## Why this reconstruction exists

The recovered material mixes hourly, 30-minute, and 5-minute records; Campbell-
and Davis-associated series; daily extrema; intermediate exports; plots;
notebooks; nested backups; and partial SQL-derived products. The challenge is
not file sorting. It is turning incomplete scientific evidence into a pipeline
whose quality decisions and provenance remain inspectable.

The modern workflow is:

```text
RAW OBSERVATIONS
  -> SOURCE IDENTIFICATION
  -> SCHEMA NORMALIZATION
  -> TEMPORAL VALIDATION
  -> INDEPENDENT QUALITY FLAGS
  -> EXPLICIT TEMPORAL HARMONIZATION
  -> ANALYSIS-READY DATA
  -> SMALL, REPRODUCIBLE ANALYSES
```

## What survived

The archive audit found 503 files inside the extracted CIGEFI directory,
including 228 CSVs, 2 Excel workbooks, 252 figures, 10 PDFs, nested ZIP backups,
and legacy code. SHA-256 hashes identified 88 exact-duplicate groups containing
177 files. The principal supported source families are:

| Source | Supported coverage | Native interval | Modern treatment |
|---|---:|---:|---|
| Campbell-associated export | 2009-02-24 to 2017-07-20 | 1 hour | Air-temperature-like observations; malformed rows retained and flagged |
| Davis `TempOut` export | 2017-04-17 to 2017-08-17 | 30 minutes | Kept parallel to Campbell during overlap |
| Davis-associated interval extrema | 2017-09-13 to 2018-06-26 | 5 minutes | Maximum and minimum variables retained separately |

A derived CSV had concatenated the two five-minute extrema variables, erased
their labels, duplicated every timestamp, and converted 1,272 missing cells to
zero. The pipeline deliberately uses the surviving Excel schema instead.

See [data sources](docs/data_sources.md), [quality control](docs/quality_control.md),
and the [archive audit](docs/archive_audit.md) for evidence and limitations.

## Quality-control design

The policy is **flag first, remove later**. Every normalized record retains:

- original and parsed timestamp/value fields;
- source, instrument family, source file, source row, and native frequency;
- measurement type (for example, air temperature versus interval maximum);
- independent structural, temporal, value, and provenance flags;
- `qc_pass`, `qc_reasons`, and a derived `temperature_clean_c`.

The recurring legacy 7–36 °C bounds are implemented only as a configurable
operational screen. They are not presented as a universal physical truth.
Duplicates are flagged, never indiscriminately dropped. Hourly data are created
with an explicit mean or median and carry coverage/provenance columns; sources
remain parallel unless a caller supplies a complete priority policy.

## Instrument-aware overlap result

The recovered Campbell and Davis 30-minute series contain 2,178 QC-passing
exact-timestamp pairs from 2017-04-17 to 2017-07-20. Davis minus Campbell has a
mean difference of -2.478 °C, median difference of -2.430 °C, RMSE of 2.567 °C,
and correlation of 0.966.

This is an observed difference between surviving sources, **not** a calibration
correction or proof of instrument bias. The archive lacks the siting, exposure,
model, maintenance, and calibration metadata needed for those claims.

## Reproducible public demo

The repository includes only a small deterministic synthetic dataset. It uses
the recovered schemas and deliberate QC edge cases, but contains no historical
observations.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/generate_sample_data.py
python scripts/run_pipeline.py
pytest
jupyter lab
```

The default pipeline writes ignored local products to `data/processed/`.
The notebooks write clearly named demo figures to `figures/`.

To process authorized local copies explicitly:

```bash
python scripts/run_pipeline.py \
  --campbell data/raw/campbell.csv \
  --davis-30min data/raw/davis30.csv \
  --davis-extrema data/raw/sede_occidente_2017-2018.xlsx
```

No SQL connection or absolute path is required.

## Notebooks

- `01_data_quality.ipynb`: source coverage, independent flags, gaps, and the
  resulting analysis-ready records.
- `02_instrument_comparison.ipynb`: exact-timestamp source alignment, difference
  distribution, descriptive agreement, and interpretation limits.
- `03_temperature_analysis.ipynb`: compact monthly summaries and distributions
  from QC-passing synthetic records.

All public notebook outputs are labeled **synthetic demonstration**. The
historical notebooks are retained locally under the ignored `notebooks/source/`
directory because their metadata, paths, and institutional context were not
reviewed for redistribution.

## Repository layout

```text
data/                 policy and synthetic sample
docs/                 audit, source lineage, and QC decisions
figures/              reproducible synthetic-demo figures
notebooks/            three narrative public notebooks
scripts/              sample generator and command-line pipeline
src/weather_pipeline/ ingestion, QC, harmonization, and analysis
tests/                synthetic behavioral tests
```

## Limitations

- The original SQL/MySQL database and some files referenced by legacy notebooks
  are missing.
- Post-June-2018 primary observations cannot be reconstructed from the surviving
  derived outputs.
- Timestamps have no recoverable timezone metadata.
- Instrument models, siting, exposure, and calibration histories are unknown.
- The public demo validates behavior, not Costa Rican climatology.
- No license or redistribution permission is asserted for CIGEFI-UCR data.

## License

Original code, documentation, tests, synthetic data, and demo figures are
released under the [MIT License](LICENSE). Recovered institutional material is
excluded from version control and is not relicensed; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
