"""Compact summaries used by the narrative notebooks."""

from __future__ import annotations

import numpy as np
import pandas as pd


def source_summary(observations: pd.DataFrame) -> pd.DataFrame:
    """Summarize coverage and QC status by source and measurement type."""

    frame = observations.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    if "qc_pass" not in frame.columns:
        frame["qc_pass"] = True
    keys = ["source", "instrument", "native_frequency", "measurement_type"]
    return (
        frame.groupby(keys, dropna=False)
        .agg(
            records=("timestamp", "size"),
            valid_timestamps=("timestamp", "count"),
            unique_timestamps=("timestamp", "nunique"),
            start=("timestamp", "min"),
            end=("timestamp", "max"),
            qc_pass_records=("qc_pass", "sum"),
        )
        .reset_index()
        .assign(flagged_records=lambda data: data["records"] - data["qc_pass_records"])
    )


def compare_instruments(
    observations: pd.DataFrame,
    left_source: str,
    right_source: str,
    *,
    measurement_type: str = "air_temperature",
) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    """Align QC-passing observations at exact timestamps and describe differences.

    Differences are defined as ``right_source - left_source``. The function
    describes agreement only; it does not estimate or apply a calibration.
    """

    required = {"timestamp", "temperature_clean_c", "source", "measurement_type"}
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Cannot compare sources; missing columns: {sorted(missing)}")
    frame = observations.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    mask = (
        frame["source"].isin([left_source, right_source])
        & frame["measurement_type"].eq(measurement_type)
        & frame["timestamp"].notna()
        & frame["temperature_clean_c"].notna()
    )
    if "qc_pass" in frame.columns:
        mask &= frame["qc_pass"]
    subset = frame.loc[mask, ["timestamp", "source", "temperature_clean_c"]]
    if subset.duplicated(["timestamp", "source"], keep=False).any():
        raise ValueError("Resolve or flag duplicate source timestamps before comparison")
    aligned = subset.pivot(
        index="timestamp", columns="source", values="temperature_clean_c"
    )
    if left_source not in aligned or right_source not in aligned:
        aligned = pd.DataFrame(columns=[left_source, right_source])
    aligned = aligned.dropna(subset=[left_source, right_source]).copy()
    difference_name = f"{right_source}_minus_{left_source}_c"
    aligned[difference_name] = aligned[right_source] - aligned[left_source]
    difference = aligned[difference_name]
    metrics: dict[str, float | int | str] = {
        "left_source": left_source,
        "right_source": right_source,
        "paired_observations": int(len(aligned)),
    }
    if not aligned.empty:
        metrics.update(
            {
                "overlap_start": aligned.index.min().isoformat(),
                "overlap_end": aligned.index.max().isoformat(),
                "mean_difference_c": float(difference.mean()),
                "median_difference_c": float(difference.median()),
                "mae_c": float(difference.abs().mean()),
                "rmse_c": float(np.sqrt(np.mean(np.square(difference)))),
                "correlation": float(aligned[left_source].corr(aligned[right_source])),
                "difference_q05_c": float(difference.quantile(0.05)),
                "difference_q95_c": float(difference.quantile(0.95)),
            }
        )
    return aligned.reset_index(), metrics


def monthly_temperature_summary(observations: pd.DataFrame) -> pd.DataFrame:
    """Calculate a small set of monthly statistics from QC-passing values."""

    frame = observations.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    mask = (
        frame["timestamp"].notna()
        & frame["temperature_clean_c"].notna()
        & frame["measurement_type"].eq("air_temperature")
    )
    if "qc_pass" in frame.columns:
        mask &= frame["qc_pass"]
    frame = frame.loc[mask].copy()
    frame["month"] = frame["timestamp"].dt.to_period("M").dt.to_timestamp()
    keys = ["source", "instrument", "month"]
    return (
        frame.groupby(keys, dropna=False)["temperature_clean_c"]
        .agg(
            observations="count",
            mean_c="mean",
            median_c="median",
            q05_c=lambda values: values.quantile(0.05),
            q95_c=lambda values: values.quantile(0.95),
        )
        .reset_index()
    )
