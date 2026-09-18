"""Temporal harmonization with explicit aggregation and source selection."""

from __future__ import annotations

import pandas as pd


def _expected_per_hour(native_frequency: object) -> int:
    expected = {"5min": 12, "30min": 2, "1h": 1}
    try:
        return expected[str(native_frequency)]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported native frequency {native_frequency!r}; "
            f"expected one of {sorted(expected)}"
        ) from exc


def resample_hourly(
    observations: pd.DataFrame,
    *,
    statistic: str = "mean",
    minimum_coverage: float = 0.5,
    measurement_type: str = "air_temperature",
    only_qc_pass: bool = True,
) -> pd.DataFrame:
    """Create source-specific hourly values after QC.

    Sources remain parallel; this function never chooses one instrument over
    another. ``statistic`` must be explicitly ``mean`` or ``median``.
    """

    if statistic not in {"mean", "median"}:
        raise ValueError("statistic must be 'mean' or 'median'")
    if not 0 <= minimum_coverage <= 1:
        raise ValueError("minimum_coverage must be between 0 and 1")
    required = {
        "timestamp",
        "temperature_clean_c",
        "source",
        "instrument",
        "source_file",
        "native_frequency",
        "measurement_type",
    }
    missing = required - set(observations.columns)
    if missing:
        raise ValueError(f"Cannot harmonize; missing columns: {sorted(missing)}")

    frame = observations.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    mask = frame["timestamp"].notna() & frame["measurement_type"].eq(measurement_type)
    if only_qc_pass:
        if "qc_pass" not in frame.columns:
            raise ValueError("only_qc_pass=True requires a qc_pass column")
        mask &= frame["qc_pass"]
    frame = frame.loc[mask].copy()

    outputs: list[pd.DataFrame] = []
    keys = ["source", "instrument", "native_frequency", "measurement_type"]
    for key_values, group in frame.groupby(keys, sort=False, dropna=False):
        expected_count = _expected_per_hour(key_values[2])
        indexed = group.sort_values("timestamp").set_index("timestamp")
        values = indexed["temperature_clean_c"].resample("1h")
        hourly_value = values.mean() if statistic == "mean" else values.median()
        count = values.count()
        files = indexed["source_file"].resample("1h").apply(
            lambda series: ";".join(sorted(set(series.dropna().astype(str))))
        )
        result = pd.DataFrame(
            {
                "timestamp": hourly_value.index,
                "temperature_clean_c": hourly_value.to_numpy(),
                "observation_count": count.to_numpy(),
                "source_file": files.to_numpy(),
            }
        )
        result["source"] = key_values[0]
        result["instrument"] = key_values[1]
        result["native_frequency"] = key_values[2]
        result["measurement_type"] = key_values[3]
        result["aggregation"] = f"hourly_{statistic}"
        result["expected_count"] = expected_count
        result["coverage_fraction"] = result["observation_count"] / expected_count
        result["qc_insufficient_coverage"] = (
            result["coverage_fraction"] < minimum_coverage
        )
        result.loc[result["qc_insufficient_coverage"], "temperature_clean_c"] = pd.NA
        outputs.append(result)

    columns = [
        "timestamp",
        "temperature_clean_c",
        "source",
        "instrument",
        "source_file",
        "native_frequency",
        "measurement_type",
        "aggregation",
        "observation_count",
        "expected_count",
        "coverage_fraction",
        "qc_insufficient_coverage",
    ]
    if not outputs:
        return pd.DataFrame(columns=columns)
    return pd.concat(outputs, ignore_index=True).loc[:, columns].sort_values(
        ["timestamp", "source"], kind="stable"
    )


def combine_sources(
    observations: pd.DataFrame,
    *,
    policy: str = "keep_parallel",
    priority: list[str] | None = None,
) -> pd.DataFrame:
    """Keep simultaneous sources or apply a caller-specified priority policy."""

    if policy == "keep_parallel":
        result = observations.copy()
        result["selection_policy"] = "keep_parallel"
        return result.sort_values(["timestamp", "source"], kind="stable")
    if policy != "explicit_priority":
        raise ValueError("policy must be 'keep_parallel' or 'explicit_priority'")
    if not priority:
        raise ValueError("explicit_priority requires an ordered priority list")
    available = set(observations["source"].dropna().astype(str))
    uncovered = available - set(priority)
    if uncovered:
        raise ValueError(f"Priority list does not cover sources: {sorted(uncovered)}")

    rank = {source: position for position, source in enumerate(priority)}
    result = observations.copy()
    result["_priority"] = result["source"].map(rank)
    result = result.sort_values(["timestamp", "_priority"], kind="stable")
    result = result.drop_duplicates(subset=["timestamp", "measurement_type"], keep="first")
    result["selection_policy"] = "explicit_priority:" + ">".join(priority)
    return result.drop(columns="_priority")
