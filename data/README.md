# Data policy

The recovered CIGEFI-UCR archive is not distributed by this repository. Its
redistribution rights could not be established, and some legacy documents also
contain personal or institutional information. Consequently, `data/raw/`, local
processed products, the recovered `CIGEFI-*` folders, and the original notebooks
are ignored by Git.

## Public sample

Files under `data/sample/` are **synthetic demonstrations**, not meteorological
observations:

- `synthetic_campbell_hourly.csv` imitates the recovered `fh,temp,hora` schema.
- `synthetic_davis_30min.csv` imitates the recovered `fh,TempOut,hora` schema.
- `synthetic_davis_5min_extrema.csv` imitates the three-column Excel export while
  retaining maximum and minimum interval values as distinct variables.

The sample intentionally contains a few malformed rows, duplicates, gaps, an
out-of-range value, and a temporal jump so that the QC behavior is visible. It
is generated deterministically by `scripts/generate_sample_data.py` and is
always labeled as synthetic in filenames, source metadata, and notebooks.

## Using authorized local data

Place authorized inputs under `data/raw/` or pass their paths directly to
`scripts/run_pipeline.py`. Do not commit them unless the data owner has provided
explicit redistribution terms. The pipeline never downloads or reconstructs
missing institutional observations.
