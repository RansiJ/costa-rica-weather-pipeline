# Quality-control policy

## Principle: flag first, remove later

`apply_quality_flags` retains the original parsed value in
`temperature_raw_c`, writes every independent reason to a boolean flag and to
`qc_reasons`, and only then masks failing values in `temperature_clean_c`.
Informational flags do not automatically invalidate an observation. The raw
files are never edited.

## Implemented flags

| Flag | Rule | Affects `qc_pass` | Rationale and limitation |
|---|---|---:|---|
| `qc_ingest_structure` | The row has an unexpected field count or is a metadata units row. | Yes | Structural problems cannot be repaired without inventing field boundaries. |
| `qc_invalid_timestamp` | Timestamp parsing returns `NaT`. | Yes | A value without a usable time cannot enter time-series analysis. |
| `qc_missing_temperature` | Blank or an explicit missing token such as `NaN`, `----`, or `np.nan`. | Yes | Missingness remains distinguishable from nonnumeric text. |
| `qc_non_numeric_temperature` | A non-missing raw value cannot be converted to a number. | Yes | Prevents silent coercion without retaining the reason. |
| `qc_duplicate` | Same source, instrument, measurement type, and timestamp occur more than once. | Yes | All members are flagged. No arbitrary `keep="first"` selection is made. |
| `qc_physical_range` | Parsed value is outside the configurable 7–36 °C operational screen. | Yes | The bounds recur in legacy code and are broad for this archive, but no recovered station document validates them as universal physical limits. |
| `qc_temporal_jump` | Adjacent observations differ by at least 4 °C and exceed 10 °C/hour. | Yes | Modern conservative screen for gross step changes. It replaces an inconsistently applied legacy percentile rule and remains configurable. |
| `qc_unknown_source` | Source or instrument identifier is blank/unknown. | Yes | The project requires traceable provenance. An unknown model is acceptable when the source family itself is known. |
| `qc_out_of_order` | Timestamp moves backward in file order. | No | The main Campbell and Davis exports are value-sorted. Sorting is allowed for analysis, but original order is recorded as a quality fact. |
| `qc_unexpected_interval` | Consecutive unique timestamps do not match the declared native interval. | No | May identify a gap rather than a bad observation. |
| `qc_gap_after_previous` | Elapsed time exceeds the declared native interval. | No | Gap runs are reported separately; no missing values are synthesized. |
| `qc_transition_period` | Timestamp falls inside a caller-supplied transition window. | No | Context flag only. The library does not invent transition dates. |

## Temporal harmonization

Harmonization happens after QC and remains source-specific. The default hourly
product is an explicitly labeled arithmetic mean with a recorded observation
count, expected count, coverage fraction, source files, and an insufficient-
coverage flag. Interval extrema are excluded from air-temperature resampling
because their measurement type is different.

Simultaneous sources remain parallel by default. An analysis may request an
`explicit_priority` policy, but it must supply a complete ordered source list;
the selected policy is written into the result.

## Historical rules: retained, changed, and rejected

### Retained with auditability

- The recurring 7–36 °C limits are retained as a configurable **operational
  screen**, not stated as a physical truth. Values are flagged and preserved.
- Top/bottom quantiles remain valid descriptive analysis outputs, but they are
  not treated as QC or called daily maxima/minima.
- Invalid dates, missing values, duplicates, and temporal discontinuities remain
  explicit concerns, consistent with the work logs.

### Changed during reconstruction

- Legacy `drop_duplicates` behavior became all-member duplicate flags. The
  modern pipeline requires an explicit downstream resolution.
- A signed 99.9th-percentile difference test, sometimes applied only to the last
  file in a loop, became a transparent rate-and-magnitude screen.
- Filtering `minute == 0` became source-specific hourly mean/median resampling
  with coverage metadata.
- Replacing suspicious values immediately with `NaN` became raw-value
  preservation plus flags and a derived clean column.
- The five-minute maximum and minimum columns remain separately typed instead
  of being concatenated into an unlabeled temperature column.

### Rejected from the main pipeline

- The special 2016 upper bound of 34 °C.
- Deleting all December 2011 data and values below 13 °C.
- Deleting January 2012 values below 15 °C.
- Deleting 2022 values below 14.3 °C and the 2022-01-28 to 2022-02-15 period.
- Treating the legacy 2017-07-21 source switch as proof of calibration or as a
  reason to discard the earlier overlap.

These rules appear in code but have no recovered methodological justification.

## Local recovered-data QC result

The validated local run (not distributed) ingested 242,436 normalized rows:

- Campbell: 71,446 rows; 71,387 pass; 55 outside the operational range; one
  duplicated timestamp pair; two malformed source rows.
- Davis 30-minute: 5,852 rows; all pass the implemented failure rules.
- Davis five-minute extrema: 82,569 rows per variable; 81,932 pass per variable;
  the difference is the units row plus 636 missing values.
- 1,167 Campbell gap runs imply 2,182 absent hourly intervals. The largest run
  contains 451 expected hours. Davis 30-minute and five-minute timestamp grids
  are complete across their surviving coverage, although the latter has missing
  values at 636 timestamps.

The 5,887 out-of-order transitions and 1,167 unexpected intervals are
informational; they do not by themselves erase valid measurements.
