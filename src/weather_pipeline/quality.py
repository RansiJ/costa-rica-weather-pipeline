"""Small, auditable quality-control rules for normalized observations."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


INFORMATIONAL_FLAGS = (
    "qc_out_of_order",
    "qc_unexpected_interval",
    "qc_gap_after_previous",
    "qc_transition_period",
)
FAIL_FLAGS = (
    "qc_ingest_structure",
    "qc_invalid_timestamp",
    "qc_missing_temperature",
    "qc_non_numeric_temperature",
    "qc_duplicate",
    "qc_physical_range",
    "qc_temporal_jump",
    "qc_unknown_source",
)
ALL_FLAGS = FAIL_FLAGS + INFORMATIONAL_FLAGS


def _expected_delta(value: object) -> pd.Timedelta | None:
    supported = {
        "5min": pd.to_timedelta(300, unit="s"),
        "30min": pd.to_timedelta(1_800, unit="s"),
        "1h": pd.to_timedelta(3_600, unit="s"),
    }
    return supported.get(str(value))


def _missing_temperature(raw: pd.Series) -> pd.Series:
    normalized = raw.astype("string").str.strip().str.lower()
    return raw.isna() | normalized.isin(
        {"", "nan", "na", "n/a", "null", "none", "----", "np.nan"}
    )


def apply_quality_flags(
    observations: pd.DataFrame,
    *,
    operational_min_c: float = 7.0,
    operational_max_c: float = 36.0,
    max_rate_c_per_hour: float = 10.0,
    minimum_jump_c: float = 4.0,
    transition_periods: Iterable[tuple[str | pd.Timestamp, str | pd.Timestamp]] = (),
) -> pd.DataFrame:
    """Add independent QC flags and derive a non-destructive clean column.

    The 7--36 °C range is a configurable operational screen inherited from
    repeated legacy code, not a universal physical bound. A value is retained
    in ``temperature_raw_c`` even when ``temperature_clean_c`` is masked.
    """

    frame = observations.copy()
    required = {
        "timestamp",
        "temperature_raw_c",
        "source",
        "instrument",
        "native_frequency",
        "measurement_type",
        "raw_temperature",
        "ingest_issue",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Cannot apply QC; missing columns: {sorted(missing)}")

    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["temperature_raw_c"] = pd.to_numeric(
        frame["temperature_raw_c"], errors="coerce"
    )
    frame["qc_ingest_structure"] = frame["ingest_issue"].notna()
    frame["qc_invalid_timestamp"] = frame["timestamp"].isna()
    frame["qc_missing_temperature"] = _missing_temperature(frame["raw_temperature"])
    frame["qc_non_numeric_temperature"] = (
        frame["temperature_raw_c"].isna() & ~frame["qc_missing_temperature"]
    )

    duplicate_keys = ["source", "instrument", "measurement_type", "timestamp"]
    frame["qc_duplicate"] = frame["timestamp"].notna() & frame.duplicated(
        duplicate_keys, keep=False
    )
    frame["qc_physical_range"] = frame["temperature_raw_c"].notna() & ~frame[
        "temperature_raw_c"
    ].between(operational_min_c, operational_max_c, inclusive="both")

    unknown_values = {"", "unknown", "nan", "none", "<na>"}
    source_unknown = frame["source"].astype("string").str.strip().str.lower().isin(
        unknown_values
    )
    instrument_unknown = (
        frame["instrument"].astype("string").str.strip().str.lower().isin(unknown_values)
    )
    frame["qc_unknown_source"] = source_unknown | instrument_unknown

    frame["qc_out_of_order"] = False
    order_keys = ["source", "instrument", "measurement_type", "source_file"]
    for _, indices in frame.groupby(order_keys, sort=False, dropna=False).groups.items():
        ordered_indices = list(indices)
        backward = frame.loc[ordered_indices, "timestamp"].diff() < pd.Timedelta(0)
        frame.loc[ordered_indices, "qc_out_of_order"] = backward.fillna(False).to_numpy()

    frame["qc_unexpected_interval"] = False
    frame["qc_gap_after_previous"] = False
    frame["qc_temporal_jump"] = False
    temporal_keys = ["source", "instrument", "measurement_type", "native_frequency"]
    valid = frame[frame["timestamp"].notna()].sort_values(
        temporal_keys + ["timestamp", "source_row"], kind="stable"
    )
    for _, group in valid.groupby(temporal_keys, sort=False, dropna=False):
        expected = _expected_delta(group["native_frequency"].iloc[0])
        if expected is None:
            continue
        delta = group["timestamp"].diff()
        positive = delta > pd.Timedelta(0)
        unexpected = positive & delta.ne(expected)
        gaps = positive & delta.gt(expected)
        frame.loc[group.index, "qc_unexpected_interval"] = unexpected.fillna(False)
        frame.loc[group.index, "qc_gap_after_previous"] = gaps.fillna(False)

        temperature_delta = group["temperature_raw_c"].diff().abs()
        hours = delta.dt.total_seconds() / 3600.0
        rate = temperature_delta / hours
        adjacent = positive & delta.le(expected * 1.5)
        jumps = (
            adjacent
            & temperature_delta.ge(minimum_jump_c)
            & rate.gt(max_rate_c_per_hour)
        )
        frame.loc[group.index, "qc_temporal_jump"] = jumps.fillna(False)

    frame["qc_transition_period"] = False
    for start, end in transition_periods:
        start_timestamp = pd.Timestamp(start)
        end_timestamp = pd.Timestamp(end)
        if end_timestamp < start_timestamp:
            raise ValueError("Transition period end precedes its start")
        frame["qc_transition_period"] |= frame["timestamp"].between(
            start_timestamp, end_timestamp, inclusive="both"
        )

    frame["qc_pass"] = ~frame.loc[:, FAIL_FLAGS].any(axis=1)
    frame["temperature_clean_c"] = frame["temperature_raw_c"].where(frame["qc_pass"])
    frame["qc_reasons"] = frame.loc[:, ALL_FLAGS].apply(
        lambda row: ";".join(flag for flag, value in row.items() if bool(value)),
        axis=1,
    )
    return frame


def detect_gaps(observations: pd.DataFrame) -> pd.DataFrame:
    """Return missing-interval runs without synthesizing observations."""

    columns = [
        "source",
        "instrument",
        "measurement_type",
        "native_frequency",
        "previous_timestamp",
        "next_timestamp",
        "gap_start",
        "gap_end",
        "missing_intervals",
        "elapsed",
    ]
    required = set(columns[:4]) | {"timestamp"}
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Cannot detect gaps; missing columns: {sorted(missing)}")

    records: list[dict[str, object]] = []
    keys = columns[:4]
    valid = observations[observations["timestamp"].notna()].copy()
    valid["timestamp"] = pd.to_datetime(valid["timestamp"])
    for key_values, group in valid.groupby(keys, sort=False, dropna=False):
        expected = _expected_delta(key_values[3])
        if expected is None:
            continue
        timestamps = pd.Series(group["timestamp"].drop_duplicates().sort_values().array)
        deltas = timestamps.diff()
        for position in deltas[deltas > expected].index:
            previous = timestamps.iloc[position - 1]
            following = timestamps.iloc[position]
            elapsed = following - previous
            missing_count = max(int(elapsed // expected) - 1, 0)
            records.append(
                {
                    **dict(zip(keys, key_values, strict=True)),
                    "previous_timestamp": previous,
                    "next_timestamp": following,
                    "gap_start": previous + expected,
                    "gap_end": following - expected,
                    "missing_intervals": missing_count,
                    "elapsed": elapsed,
                }
            )
    return pd.DataFrame.from_records(records, columns=columns)
