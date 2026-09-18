from pathlib import Path

import pandas as pd
import pytest

from weather_pipeline.ingest import (
    SchemaError,
    load_campbell_csv,
    load_davis_30min_csv,
    load_davis_interval_extrema_csv,
    load_davis_interval_extrema_xlsx,
)


def test_campbell_loader_preserves_malformed_row(tmp_path: Path) -> None:
    path = tmp_path / "campbell.csv"
    path.write_text(
        "fh,temp,hora\n"
        "2017-01-01,20.1,00:00:00\n"
        "2017-01-01,21.0,08-,22.0,09:00:00\n",
        encoding="utf-8",
    )

    result = load_campbell_csv(path)

    assert len(result) == 2
    assert result.loc[0, "timestamp"] == pd.Timestamp("2017-01-01")
    assert result.loc[0, "temperature_raw_c"] == pytest.approx(20.1)
    assert result.loc[1, "ingest_issue"] == "unexpected_field_count:5"
    assert pd.isna(result.loc[1, "timestamp"])
    assert set(result["source_file"]) == {"campbell.csv"}


def test_davis_loader_accepts_both_surviving_schemas(tmp_path: Path) -> None:
    native = tmp_path / "native.csv"
    normalized = tmp_path / "normalized.csv"
    native.write_text("fh,TempOut,hora\n2017-01-01,20.5,00:00:00\n", encoding="utf-8")
    normalized.write_text(
        "fecha,temperatura\n2017-01-01 00:00:00,20.5\n", encoding="utf-8"
    )

    native_result = load_davis_30min_csv(native)
    normalized_result = load_davis_30min_csv(normalized)

    assert native_result.loc[0, "temperature_raw_c"] == pytest.approx(20.5)
    assert normalized_result.loc[0, "timestamp"] == pd.Timestamp("2017-01-01")


def test_interval_extrema_remain_distinct_variables(tmp_path: Path) -> None:
    path = tmp_path / "extrema.csv"
    path.write_text(
        "fecha,Temp_Max,Temp_Min\n2017-01-01 00:00:00,20.3,20.0\n",
        encoding="utf-8",
    )

    result = load_davis_interval_extrema_csv(path)

    assert len(result) == 2
    assert set(result["measurement_type"]) == {
        "interval_maximum",
        "interval_minimum",
    }
    assert result["timestamp"].nunique() == 1


def test_recovered_excel_schema_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "extrema.xlsx"
    pd.DataFrame(
        {
            "fecha": ["", "2017-01-01 00:00:00"],
            "Temp_Max": ["(°C)", 20.3],
            "Temp_Min": ["(°C)", 20.0],
        }
    ).to_excel(path, index=False)

    result = load_davis_interval_extrema_xlsx(path)

    assert len(result) == 4
    assert (result.loc[:1, "ingest_issue"] == "metadata_units_row").all()
    assert result.loc[2:, "timestamp"].nunique() == 1


def test_schema_validation_is_explicit(tmp_path: Path) -> None:
    path = tmp_path / "wrong.csv"
    path.write_text("date,value\n2017-01-01,20\n", encoding="utf-8")
    with pytest.raises(SchemaError, match="Expected Davis columns"):
        load_davis_30min_csv(path)
