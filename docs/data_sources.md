# Reconstructed data sources

## Evidence standard

Source identity is reported only as far as the surviving filenames, schemas,
legacy notebooks, and work logs support it. Instrument models, station moves,
sensor heights, exposure, calibration history, timezone, and logger aggregation
semantics are unknown. Timestamps therefore remain timezone-naive.

Confidence labels mean:

- **High**: the file structure and another surviving artifact agree.
- **Medium**: filenames and code agree, but independent instrument metadata is absent.
- **Low**: only a derived artifact or filename supports the interpretation.

## Source families used by the modern loaders

| Source family | Surviving private file | Coverage | Native interval | Records and issues | Interpretation | Confidence |
|---|---|---:|---:|---|---|---|
| Campbell-shaped hourly export | `San_ramon/campbell.csv` | 2009-02-24 17:00 to 2017-07-20 09:00 | Predominantly 1 hour | 71,446 data lines: 71,444 valid timestamps, 71,443 unique timestamps, one duplicated timestamp with different values, and two structurally malformed lines. The rows are not chronological. | Air-temperature-like values associated with Campbell by filename and legacy code. Logger model and aggregation meaning are unknown. | Medium |
| Davis 30-minute export | `San_ramon/davis30.csv` | 2017-04-17 12:00 to 2017-08-17 09:30 | 30 minutes | 5,852 timestamps, complete at the stated interval after sorting, no duplicate timestamps. The rows are not chronological. | `TempOut` observations associated with Davis by filename and legacy code. Model is unknown. | Medium |
| Davis 5-minute interval extrema | `San_ramon/datos/sede_occidente_2017-2018.xlsx` | 2017-09-13 00:00 to 2018-06-26 16:35 | 5 minutes | 82,568 valid timestamps plus one units row; `Temp_Max` and `Temp_Min` are both absent at 636 timestamps. | Two interval-extrema variables. They are not silently converted into a single instantaneous temperature. | High for schema; medium for instrument identity |

The two CSV sources above each have an exact duplicate elsewhere in the archive.
The Davis 30-minute data also survive in a semantically identical two-column
representation (`fecha,temperatura`). Hash equality was used only for exact
copies; format variants were compared by timestamp and value.

## Important derived files

| Artifact | Classification | Evidence and consequence |
|---|---|---|
| `datos_sede_occidente_2017to2018.csv` | Derived, lossy long-form export | Contains 165,136 rows: the Excel maximum block followed by the minimum block. Every timestamp is duplicated, the measurement label was discarded, and the 636 missing values in each variable became 1,272 zeros. It is excluded from primary ingestion. |
| `sede_occidente_2009-2017.xlsx` | Daily derived export | Contains daily maximum/minimum values and their occurrence times. The header explicitly states that a cut timestamp refers to the previous day's extrema. Coverage is 2009-02-28 to 2017-07-19; there are 12 missing values in each extrema column, repeated cut timestamps, and implausible values down to -35.92 °C and up to 74.10 °C. |
| `datos_sede_occidente_2009to2017_{max,min}.csv` | Derived extracts | Re-exports of the daily extrema workbook, not primary observations. |
| `REBAMB/datos/años/*_data.csv` | Harmonized/cleaned derived grids | Mostly 30-minute annual grids for 2009-2021 with many inserted missing values. The generating combined file and full transformation history are absent, and legacy code applies undocumented year-specific deletions. These files are not used as primary input. |
| `*_min.csv`, `*_max.csv`, `*_ord_c.csv` | Derived subsets | Bottom/top 10% subsets or ordered extrema created by legacy notebooks. Several 2018-2022 pairs are suspiciously identical. |
| `Medianas/`, `Histogramas/`, `temperaturas_ext/`, `Gráficas Informe/` | Analysis outputs | Monthly medians, histograms, and figures. They can be regenerated only where suitable source observations survive. |

## Availability chronology

| Period | Evidence available | Conservative use |
|---|---|---|
| 2009-02-24 to 2017-04-16 | Campbell-shaped hourly export; daily extrema export begins four days later | QC and descriptive analysis of the hourly export; daily extrema remain a separate derived product. |
| 2017-04-17 to 2017-07-20 | Campbell hourly and Davis 30-minute overlap | Exact-timestamp comparison while keeping both sources. No calibration correction is inferred. |
| 2017-07-21 to 2017-08-17 | Davis 30-minute only | Source-specific analysis. The legacy code's apparent 2017-07-21 switch is not needed to erase the earlier overlap. |
| 2017-08-17 to 2017-09-13 | No supported continuous source | Explicit gap. |
| 2017-09-13 to 2018-06-26 | Davis 5-minute interval maximum/minimum export | Preserve extrema types separately. Do not present them as `TempOut` without a documented conversion. |
| After 2018-06-26 | Only lineage-incomplete derived products survive locally | Do not reconstruct or present missing raw observations. Some extrema outputs reach 2022, but their primary records are absent. |

## Campbell–Davis overlap result

After structural, numeric, duplicate, and configurable 7–36 °C operational
screens, 2,178 exact-timestamp pairs remain from 2017-04-17 12:00 through
2017-07-20 09:00. With difference defined as Davis minus Campbell:

- mean difference: -2.478 °C;
- median difference: -2.430 °C;
- mean absolute difference: 2.479 °C;
- RMSE: 2.567 °C;
- Pearson correlation: 0.966;
- 5th–95th percentile difference: -3.702 to -1.550 °C.

These statistics demonstrate a systematic difference between the surviving
series during the overlap. They are **not** an instrument bias or calibration
estimate because location, exposure, calibration, and measurement semantics are
not available.

## Missing source material

The original MySQL database mentioned in the January 2023 work log is no longer
available. Files referenced by legacy code but absent from the recovered archive
include `SedeOccidente_davis5min.csv`, `SedeOccidente.txt`,
`campbell_rebamb.csv`, `SanRamon_data.csv`, and several intermediate
`datos_finales*.csv` products. No observations are synthesized from plots or
aggregate statistics to fill those losses.
