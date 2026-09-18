import pandas as pd
import pytest

from weather_pipeline.analysis import compare_instruments, monthly_temperature_summary


def test_instrument_comparison_uses_exact_timestamp_pairs() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2017-01-01 00:00", "2017-01-01 01:00"] * 2
            ),
            "temperature_clean_c": [21.0, 22.0, 20.0, 21.0],
            "source": ["campbell", "campbell", "davis", "davis"],
            "measurement_type": ["air_temperature"] * 4,
            "qc_pass": [True] * 4,
        }
    )
    aligned, metrics = compare_instruments(frame, "campbell", "davis")
    assert len(aligned) == 2
    assert metrics["mean_difference_c"] == pytest.approx(-1.0)
    assert metrics["correlation"] == pytest.approx(1.0)


def test_monthly_summary_uses_only_qc_passing_values() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2017-01-01", "2017-01-02", "2017-02-01"]
            ),
            "temperature_clean_c": [20.0, 22.0, 30.0],
            "source": ["source"] * 3,
            "instrument": ["instrument"] * 3,
            "measurement_type": ["air_temperature"] * 3,
            "qc_pass": [True, False, True],
        }
    )
    summary = monthly_temperature_summary(frame)
    assert list(summary["observations"]) == [1, 1]
    assert list(summary["mean_c"]) == [20.0, 30.0]
