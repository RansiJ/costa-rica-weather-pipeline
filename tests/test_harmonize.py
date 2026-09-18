import pandas as pd
import pytest

from weather_pipeline.harmonize import combine_sources, resample_hourly


def qc_observations() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2017-01-01 00:00:00",
                    "2017-01-01 00:30:00",
                    "2017-01-01 01:00:00",
                ]
            ),
            "temperature_clean_c": [20.0, 22.0, 24.0],
            "source": ["davis"] * 3,
            "instrument": ["Davis"] * 3,
            "source_file": ["davis.csv"] * 3,
            "native_frequency": ["30min"] * 3,
            "measurement_type": ["air_temperature"] * 3,
            "qc_pass": [True] * 3,
        }
    )


def test_hourly_mean_and_coverage_preserve_provenance() -> None:
    result = resample_hourly(qc_observations(), minimum_coverage=0.5)
    assert result.loc[0, "temperature_clean_c"] == pytest.approx(21.0)
    assert result.loc[0, "coverage_fraction"] == pytest.approx(1.0)
    assert result.loc[1, "temperature_clean_c"] == pytest.approx(24.0)
    assert result.loc[1, "coverage_fraction"] == pytest.approx(0.5)
    assert set(result["source_file"]) == {"davis.csv"}
    assert set(result["aggregation"]) == {"hourly_mean"}


def test_insufficient_hourly_coverage_is_flagged() -> None:
    result = resample_hourly(qc_observations(), minimum_coverage=0.75)
    assert result.loc[1, "qc_insufficient_coverage"]
    assert pd.isna(result.loc[1, "temperature_clean_c"])


def test_sources_stay_parallel_by_default() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2017-01-01", "2017-01-01"]),
            "source": ["campbell", "davis"],
            "measurement_type": ["air_temperature", "air_temperature"],
        }
    )
    result = combine_sources(frame)
    assert len(result) == 2
    assert set(result["selection_policy"]) == {"keep_parallel"}


def test_source_priority_must_be_explicit_and_complete() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2017-01-01", "2017-01-01"]),
            "source": ["campbell", "davis"],
            "measurement_type": ["air_temperature", "air_temperature"],
        }
    )
    selected = combine_sources(
        frame, policy="explicit_priority", priority=["davis", "campbell"]
    )
    assert len(selected) == 1
    assert selected.iloc[0]["source"] == "davis"
    with pytest.raises(ValueError, match="does not cover"):
        combine_sources(frame, policy="explicit_priority", priority=["davis"])
