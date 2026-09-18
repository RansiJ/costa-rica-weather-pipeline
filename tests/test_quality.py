import pandas as pd

from weather_pipeline.quality import apply_quality_flags, detect_gaps


def observations(rows: list[tuple[object, object, str]]) -> pd.DataFrame:
    records = []
    for index, (timestamp, temperature, raw_temperature) in enumerate(rows, start=2):
        records.append(
            {
                "timestamp": timestamp,
                "temperature_raw_c": temperature,
                "temperature_clean_c": temperature,
                "source": "source_a",
                "instrument": "instrument_a",
                "source_file": "sample.csv",
                "source_row": index,
                "native_frequency": "30min",
                "measurement_type": "air_temperature",
                "raw_timestamp": str(timestamp),
                "raw_temperature": raw_temperature,
                "ingest_issue": pd.NA,
            }
        )
    return pd.DataFrame(records)


def test_independent_flags_preserve_raw_values() -> None:
    frame = observations(
        [
            ("2017-01-01 00:00:00", 20.0, "20.0"),
            ("2017-01-01 00:00:00", 21.0, "21.0"),
            (pd.NaT, pd.NA, "bad"),
            ("2017-01-01 00:30:00", 50.0, "50.0"),
            ("2017-01-01 01:00:00", pd.NA, ""),
        ]
    )

    result = apply_quality_flags(frame)

    assert result.loc[0:1, "qc_duplicate"].all()
    assert result.loc[2, "qc_invalid_timestamp"]
    assert result.loc[2, "qc_non_numeric_temperature"]
    assert result.loc[3, "qc_physical_range"]
    assert result.loc[4, "qc_missing_temperature"]
    assert result.loc[3, "temperature_raw_c"] == 50.0
    assert pd.isna(result.loc[3, "temperature_clean_c"])


def test_frequency_aware_temporal_jump() -> None:
    frame = observations(
        [
            ("2017-01-01 00:00:00", 20.0, "20.0"),
            ("2017-01-01 00:30:00", 29.0, "29.0"),
        ]
    )
    result = apply_quality_flags(frame)
    assert not result.loc[0, "qc_temporal_jump"]
    assert result.loc[1, "qc_temporal_jump"]


def test_gap_detection_reports_missing_intervals() -> None:
    frame = observations(
        [
            ("2017-01-01 00:00:00", 20.0, "20.0"),
            ("2017-01-01 00:30:00", 20.2, "20.2"),
            ("2017-01-01 02:00:00", 20.4, "20.4"),
        ]
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    gaps = detect_gaps(frame)
    assert len(gaps) == 1
    assert gaps.loc[0, "missing_intervals"] == 2
    assert gaps.loc[0, "gap_start"] == pd.Timestamp("2017-01-01 01:00:00")
    assert gaps.loc[0, "gap_end"] == pd.Timestamp("2017-01-01 01:30:00")


def test_transition_flag_is_informational() -> None:
    frame = observations([("2017-01-01 00:00:00", 20.0, "20.0")])
    result = apply_quality_flags(
        frame, transition_periods=[("2016-12-31", "2017-01-02")]
    )
    assert result.loc[0, "qc_transition_period"]
    assert result.loc[0, "qc_pass"]
