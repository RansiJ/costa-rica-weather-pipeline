# Recovered archive audit

## Inventory scope

The audit covered the extracted `CIGEFI` directory before the new architecture
was created. It contains 503 files:

| Type | Count | Primary role |
|---|---:|---|
| CSV | 228 | Mixed probable exports, annual grids, extrema subsets, and monthly summaries |
| PNG/JPEG | 252 | Analysis figures and copies |
| PDF | 10 | Nine weekly work logs and one legacy plot |
| XLSX | 2 | Daily extrema export and five-minute interval-extrema export |
| ZIP | 8 | Nested backups, mostly duplicating extracted outputs |
| DOCX | 1 | A work-log template containing a completed February entry |
| Python | 1 | Colab-exported legacy script |
| INI | 1 | Desktop metadata |

Outside that directory, the project also contained 12 recovered notebooks and
one 35.7 MB outer archive. Exact SHA-256 comparison found 88 duplicate groups
covering 177 extracted files. This count excludes merely similar files whose
content differs.

## Classification of the main material

- **Probable source exports:** Campbell-shaped hourly CSV, Davis 30-minute CSV,
  and Davis five-minute interval-extrema XLSX. “Source export” does not mean an
  untouched logger file; both CSVs are value-sorted.
- **Derived datasets:** daily max/min exports, annual 30-minute grids, 10%
  extrema subsets, monthly medians, and the lossy concatenated five-minute CSV.
- **Analysis outputs:** histograms, time-series plots, report figures, and their
  ZIP copies.
- **Work logs:** November 2022 through February 2023 PDFs plus the DOCX copy.
- **Legacy code:** 12 notebooks and one exported `.py` file.
- **Uncertain provenance:** small 2014 split files and several intermediate
  variants that lack a recoverable generating path.

## What the work logs establish

- In November 2022, dates for 2014 and other years were recognized as wrongly
  transformed; untransformed 2014 data were re-imported into a small database.
- A personal “clean” database was assembled from the available San Ramón data.
- Duplicate data were noticed, removed, and the database was updated.
- “Atypical” values were replaced by `NaN`, but the logs do not state numeric
  thresholds.
- Top/bottom 10% subsets and figures for 2009–2022 were generated.
- In January 2023, yearly temperature data were backed up to MySQL on a CIGEFI
  workstation.
- In February 2023, histograms, monthly means, and the report were produced.

The logs support the historical intent but do not establish the correctness of
individual transformations.

## Decision status

### Documented and defensible

- Date parsing problems existed and must be made visible.
- Duplicates and suspicious values require QC.
- Derived extrema, histograms, and monthly summaries should be kept separate
  from source observations.
- A database-backed stage existed and is now missing.

### Documented but methodologically incomplete

- Removing duplicates without identifying their origin.
- Replacing all “atypical” values with `NaN` without preserving flags or stating
  thresholds.
- Calling top/bottom 10% observations “maximum” and “minimum” series.

### Present in code but not documented in the logs

- A 7–36 °C general screen, a 34 °C exception for 2016, and 7–40/7–35 variants.
- Deletions specific to 2011, 2012, and 2022.
- A source switch on 2017-07-21.
- Exact-hour filtering as the hourly harmonization strategy.
- A 99.9th-percentile jump test.

### Justification not recoverable

Instrument siting, model, maintenance, calibration, exposure, timezone, whether
timestamps denote interval start/end, and why the year-specific deletions were
chosen.

## Consequential legacy-code defects

1. `if archivo == "A.csv" or "B.csv":` is always truthy, so the intended
   source-specific frequency branch never works.
2. `if not temperatura < 7 or temperatura > 40:` simplifies to
   `temperatura >= 7`; values above 40 are retained rather than rejected.
3. `df.drop_duplicates(...)` is called without assignment or `inplace=True` in
   one notebook, so it has no effect.
4. Other notebooks drop duplicate timestamps with `keep="first"`, which is
   especially damaging after maximum and minimum variables were concatenated at
   identical timestamps.
5. Quantiles and jump rules are sometimes computed from only the final dataframe
   left in a loop, not from the combined dataset.
6. A combined date range is built using the last source's frequency, potentially
   imposing an hourly grid on higher-frequency sources.
7. One cell assigns a filtered dataframe to the single `fecha` column rather
   than filtering rows.
8. Several loops use inconsistent source filenames and hard-coded paths, and
   one duplicate-removal notebook reads `2018.csv` but writes `2017_nd.csv`.
9. The five-minute maximum/minimum export is treated as one unlabeled
   `TempOut` series after concatenation.

## Irrecoverable gaps and contradictions

- The original institutional SQL/MySQL database is unavailable.
- Several files named in code are absent, including the longer 2017–2022 Davis
  five-minute series reported by notebook output.
- Derived annual files extend beyond the primary exports, but their generating
  combined dataset and complete transformations are absent.
- The daily-extrema workbook, its CSV extracts, and the hourly Campbell export
  overlap in dates but represent different temporal statistics; they are not
  interchangeable.
- The source files are value-sorted even though their timestamps form regular
  grids after sorting. This is preserved as an out-of-order flag rather than
  interpreted as logger order.

The reconstruction uses the most conservative interpretation: no missing raw
records are inferred from plots, medians, histograms, or extrema subsets.
