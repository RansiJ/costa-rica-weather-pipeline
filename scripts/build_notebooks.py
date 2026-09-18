"""Build the three small narrative notebooks from versioned cell sources."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


SETUP = """from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display

ROOT = next(
    candidate
    for candidate in [Path.cwd(), *Path.cwd().parents]
    if (candidate / "src" / "weather_pipeline").exists()
)
sys.path.insert(0, str(ROOT / "src"))
SAMPLE = ROOT / "data" / "sample"
FIGURES = ROOT / "figures"
FIGURES.mkdir(exist_ok=True)
plt.style.use("seaborn-v0_8-whitegrid")
"""


LOAD_ALL = """from weather_pipeline import (
    apply_quality_flags,
    concatenate_sources,
    load_campbell_csv,
    load_davis_30min_csv,
    load_davis_interval_extrema_csv,
)

campbell = load_campbell_csv(
    SAMPLE / "synthetic_campbell_hourly.csv",
    source="synthetic_campbell_hourly",
    instrument="Synthetic Campbell-like source",
)
davis = load_davis_30min_csv(
    SAMPLE / "synthetic_davis_30min.csv",
    source="synthetic_davis_30min",
    instrument="Synthetic Davis-like source",
)
extrema = load_davis_interval_extrema_csv(
    SAMPLE / "synthetic_davis_5min_extrema.csv",
    source="synthetic_davis_5min_interval_extrema",
    instrument="Synthetic Davis-like source",
)
observations = apply_quality_flags(
    concatenate_sources([campbell, davis, extrema])
)
"""


def notebook(cells: list[object]) -> nbf.NotebookNode:
    result = nbf.v4.new_notebook()
    result.cells = cells
    result.metadata = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3"},
    }
    return result


def build_quality_notebook() -> nbf.NotebookNode:
    return notebook(
        [
            nbf.v4.new_markdown_cell(
                """# 01 — Data quality overview

> **Synthetic demonstration.** Every record used below is generated locally and
> is not a CIGEFI-UCR observation. The schemas and injected failure modes mirror
> the recovered archive so the public QC workflow remains executable."""
            ),
            nbf.v4.new_markdown_cell(
                """The objective is to retain source identity and raw values while
making structural, temporal, value, and provenance concerns independently
auditable. Flags are created before `temperature_clean_c` is derived."""
            ),
            nbf.v4.new_code_cell(SETUP),
            nbf.v4.new_code_cell(LOAD_ALL),
            nbf.v4.new_code_cell(
                """from weather_pipeline import detect_gaps, source_summary

summary = source_summary(observations)
display(summary)"""
            ),
            nbf.v4.new_markdown_cell(
                """The five-minute source appears twice because maximum and minimum
are distinct interval statistics. They are intentionally not mixed with
`air_temperature`."""
            ),
            nbf.v4.new_code_cell(
                """flag_columns = [
    column
    for column in observations.columns
    if column.startswith("qc_") and column not in {"qc_pass", "qc_reasons"}
]
flag_summary = (
    observations[flag_columns]
    .sum()
    .rename("flagged_records")
    .to_frame()
    .assign(percent=lambda data: 100 * data["flagged_records"] / len(observations))
    .sort_values("flagged_records", ascending=False)
)
display(flag_summary)

gaps = detect_gaps(observations)
display(gaps.head())"""
            ),
            nbf.v4.new_code_cell(
                """coverage = summary.sort_values(["source", "measurement_type"]).reset_index(drop=True)
labels = coverage["source"] + " / " + coverage["measurement_type"]
nonzero_flags = flag_summary.query("flagged_records > 0").sort_values("flagged_records")

fig, (timeline, flags) = plt.subplots(2, 1, figsize=(11, 7), constrained_layout=True)
for position, row in coverage.iterrows():
    timeline.hlines(position, row["start"], row["end"], linewidth=8)
    timeline.scatter([row["start"], row["end"]], [position, position], s=28)
timeline.set_yticks(range(len(labels)), labels)
timeline.set_title("Synthetic source and variable coverage")
timeline.set_xlabel("Timestamp")

flags.barh(nonzero_flags.index.str.replace("qc_", "", regex=False), nonzero_flags["flagged_records"])
flags.set_title("Independent QC flags")
flags.set_xlabel("Flagged records")

output = FIGURES / "demo_data_quality_overview.png"
fig.savefig(output, dpi=160, bbox_inches="tight")
plt.show()
output.relative_to(ROOT)"""
            ),
            nbf.v4.new_code_cell(
                """analysis_ready = observations.loc[
    observations["qc_pass"] & observations["measurement_type"].eq("air_temperature")
].copy()
print(f"Normalized records: {len(observations):,}")
print(f"QC-passing air-temperature records: {len(analysis_ready):,}")
display(
    analysis_ready[
        [
            "timestamp",
            "temperature_raw_c",
            "temperature_clean_c",
            "source",
            "source_file",
            "native_frequency",
            "qc_pass",
        ]
    ].head()
)"""
            ),
            nbf.v4.new_markdown_cell(
                """No flagged row is deleted from `observations`. The
`analysis_ready` view is a downstream choice, and the source file and native
frequency remain attached to every selected record."""
            ),
        ]
    )


def build_comparison_notebook() -> nbf.NotebookNode:
    return notebook(
        [
            nbf.v4.new_markdown_cell(
                """# 02 — Instrument/source comparison

> **Synthetic demonstration.** The controlled offset in this notebook was
> generated by `scripts/generate_sample_data.py`; it is not a historical result."""
            ),
            nbf.v4.new_markdown_cell(
                """The comparison uses QC-passing observations at exact common
timestamps. It does not interpolate, select a preferred instrument, or apply a
calibration correction."""
            ),
            nbf.v4.new_code_cell(SETUP),
            nbf.v4.new_code_cell(
                """from weather_pipeline import (
    apply_quality_flags,
    compare_instruments,
    concatenate_sources,
    load_campbell_csv,
    load_davis_30min_csv,
)

left_source = "synthetic_campbell_hourly"
right_source = "synthetic_davis_30min"
campbell = load_campbell_csv(
    SAMPLE / "synthetic_campbell_hourly.csv",
    source=left_source,
    instrument="Synthetic Campbell-like source",
)
davis = load_davis_30min_csv(
    SAMPLE / "synthetic_davis_30min.csv",
    source=right_source,
    instrument="Synthetic Davis-like source",
)
observations = apply_quality_flags(concatenate_sources([campbell, davis]))
aligned, metrics = compare_instruments(observations, left_source, right_source)
display(pd.Series(metrics, name="value").to_frame())"""
            ),
            nbf.v4.new_code_cell(
                """difference_column = f"{right_source}_minus_{left_source}_c"
window = aligned.head(24 * 7)

fig, (series_axis, difference_axis) = plt.subplots(
    1, 2, figsize=(12, 4.5), constrained_layout=True
)
series_axis.plot(window["timestamp"], window[left_source], label="Campbell-like", linewidth=1.4)
series_axis.plot(window["timestamp"], window[right_source], label="Davis-like", linewidth=1.2)
series_axis.set_title("First seven days of exact-time pairs")
series_axis.set_ylabel("Synthetic temperature (°C)")
series_axis.tick_params(axis="x", rotation=30)
series_axis.legend()

difference_axis.hist(aligned[difference_column], bins=24, color="#4C78A8", edgecolor="white")
difference_axis.axvline(metrics["mean_difference_c"], color="#E45756", linestyle="--", label="Mean")
difference_axis.set_title("Difference distribution")
difference_axis.set_xlabel("Davis-like minus Campbell-like (°C)")
difference_axis.set_ylabel("Paired observations")
difference_axis.legend()

output = FIGURES / "demo_instrument_comparison.png"
fig.savefig(output, dpi=160, bbox_inches="tight")
plt.show()
output.relative_to(ROOT)"""
            ),
            nbf.v4.new_markdown_cell(
                """## Interpretation boundary

The synthetic series agree strongly because they were generated from the same
signal with a controlled offset. In the recovered archive, an observed offset
may combine instrument response, siting, exposure, timestamp semantics, and
processing history. Without those metadata, the defensible language is
**difference between sources during overlap**, not bias or calibration error."""
            ),
        ]
    )


def build_temperature_notebook() -> nbf.NotebookNode:
    return notebook(
        [
            nbf.v4.new_markdown_cell(
                """# 03 — Temperature analysis

> **Synthetic demonstration.** These summaries show that the processed dataset
> is usable; they make no claim about San Ramón climate."""
            ),
            nbf.v4.new_code_cell(SETUP),
            nbf.v4.new_code_cell(LOAD_ALL),
            nbf.v4.new_code_cell(
                """from weather_pipeline import monthly_temperature_summary, resample_hourly

hourly = resample_hourly(
    observations,
    statistic="mean",
    minimum_coverage=0.5,
)
monthly = monthly_temperature_summary(observations)
display(monthly)"""
            ),
            nbf.v4.new_code_cell(
                """clean_air = observations.loc[
    observations["qc_pass"] & observations["measurement_type"].eq("air_temperature")
].copy()

fig, (monthly_axis, distribution_axis) = plt.subplots(
    1, 2, figsize=(12, 4.5), constrained_layout=True
)
for source, group in monthly.groupby("source"):
    monthly_axis.plot(group["month"], group["median_c"], marker="o", label=source)
monthly_axis.set_title("Monthly median of QC-passing values")
monthly_axis.set_ylabel("Synthetic temperature (°C)")
monthly_axis.tick_params(axis="x", rotation=30)
monthly_axis.legend(fontsize=8)

for source, group in clean_air.groupby("source"):
    distribution_axis.hist(
        group["temperature_clean_c"], bins=30, alpha=0.55, density=True, label=source
    )
distribution_axis.set_title("QC-passing temperature distributions")
distribution_axis.set_xlabel("Synthetic temperature (°C)")
distribution_axis.set_ylabel("Density")
distribution_axis.legend(fontsize=8)

output = FIGURES / "demo_temperature_analysis.png"
fig.savefig(output, dpi=160, bbox_inches="tight")
plt.show()
output.relative_to(ROOT)"""
            ),
            nbf.v4.new_code_cell(
                """hourly_summary = (
    hourly.groupby("source")
    .agg(
        hourly_rows=("timestamp", "size"),
        usable_hourly_values=("temperature_clean_c", "count"),
        median_coverage=("coverage_fraction", "median"),
    )
    .reset_index()
)
display(hourly_summary)"""
            ),
            nbf.v4.new_markdown_cell(
                """The hourly table records how many native observations contributed
to each value and never combines instruments silently. Interval maximum/minimum
records are excluded because their temporal statistic is not equivalent to the
air-temperature observations."""
            ),
        ]
    )


def main() -> None:
    NOTEBOOKS.mkdir(exist_ok=True)
    outputs = {
        "01_data_quality.ipynb": build_quality_notebook(),
        "02_instrument_comparison.ipynb": build_comparison_notebook(),
        "03_temperature_analysis.ipynb": build_temperature_notebook(),
    }
    for name, content in outputs.items():
        nbf.write(content, NOTEBOOKS / name)
        print(f"Wrote {NOTEBOOKS / name}")


if __name__ == "__main__":
    main()
