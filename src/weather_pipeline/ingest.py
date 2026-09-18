"""Load only the recovered source formats that are evidenced in this project.

Timestamps are retained as timezone-naive local clock readings because the
surviving files do not contain a timezone or daylight-saving metadata.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import pandas as pd


COMMON_COLUMNS = [
    "timestamp",
    "temperature_raw_c",
    "temperature_clean_c",
    "source",
    "instrument",
    "source_file",
    "source_row",
    "native_frequency",
    "measurement_type",
    "raw_timestamp",
    "raw_temperature",
    "ingest_issue",
]


class SchemaError(ValueError):
    """Raised when a recovered file does not match an evidenced source schema."""


def _read_csv_rows(path: Path) -> tuple[list[str], list[tuple[int, list[str]]]]:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                reader = csv.reader(stream)
                header = next(reader, None)
                if header is None:
                    raise SchemaError(f"Empty CSV: {path}")
                return [value.strip() for value in header], [
                    (row_number, row)
                    for row_number, row in enumerate(reader, start=2)
                    if row
                ]
        except UnicodeDecodeError as exc:
            last_error = exc
    raise SchemaError(f"Could not decode {path}: {last_error}")


def _records_to_frame(records: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    if frame.empty:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    frame["timestamp"] = pd.to_datetime(frame["raw_timestamp"], errors="coerce")
    frame["temperature_raw_c"] = pd.to_numeric(
        frame["raw_temperature"], errors="coerce"
    )
    frame["temperature_clean_c"] = frame["temperature_raw_c"]
    return frame.loc[:, COMMON_COLUMNS]


def _load_three_column_csv(
    path: str | Path,
    *,
    expected_headers: tuple[str, str, str],
    date_column: str,
    time_column: str,
    temperature_column: str,
    source: str,
    instrument: str,
    native_frequency: str,
    measurement_type: str = "air_temperature",
    source_file: str | None = None,
) -> pd.DataFrame:
    file_path = Path(path)
    header, rows = _read_csv_rows(file_path)
    if tuple(header) != expected_headers:
        raise SchemaError(
            f"Expected columns {expected_headers} in {file_path.name}; found {tuple(header)}"
        )
    position = {column: header.index(column) for column in header}
    records: list[dict[str, object]] = []
    provenance_name = source_file or file_path.name
    for row_number, row in rows:
        base = {
            "source": source,
            "instrument": instrument,
            "source_file": provenance_name,
            "source_row": row_number,
            "native_frequency": native_frequency,
            "measurement_type": measurement_type,
        }
        if len(row) != len(header):
            records.append(
                {
                    **base,
                    "raw_timestamp": ",".join(row),
                    "raw_temperature": pd.NA,
                    "ingest_issue": f"unexpected_field_count:{len(row)}",
                }
            )
            continue
        raw_timestamp = (
            f"{row[position[date_column]].strip()} "
            f"{row[position[time_column]].strip()}"
        ).strip()
        records.append(
            {
                **base,
                "raw_timestamp": raw_timestamp,
                "raw_temperature": row[position[temperature_column]].strip(),
                "ingest_issue": pd.NA,
            }
        )
    return _records_to_frame(records)


def load_campbell_csv(
    path: str | Path,
    *,
    source: str = "campbell_hourly_export",
    instrument: str = "Campbell (model unknown)",
    source_file: str | None = None,
) -> pd.DataFrame:
    """Load the recovered ``fh,temp,hora`` Campbell-shaped CSV.

    Structurally malformed rows are preserved as flagged ingest records rather
    than silently skipped or repaired.
    """

    return _load_three_column_csv(
        path,
        expected_headers=("fh", "temp", "hora"),
        date_column="fh",
        time_column="hora",
        temperature_column="temp",
        source=source,
        instrument=instrument,
        native_frequency="1h",
        source_file=source_file,
    )


def load_davis_30min_csv(
    path: str | Path,
    *,
    source: str = "davis_30min_export",
    instrument: str = "Davis (model unknown)",
    source_file: str | None = None,
) -> pd.DataFrame:
    """Load either surviving representation of the Davis 30-minute export."""

    file_path = Path(path)
    header, _ = _read_csv_rows(file_path)
    if tuple(header) == ("fh", "TempOut", "hora"):
        return _load_three_column_csv(
            file_path,
            expected_headers=("fh", "TempOut", "hora"),
            date_column="fh",
            time_column="hora",
            temperature_column="TempOut",
            source=source,
            instrument=instrument,
            native_frequency="30min",
            source_file=source_file,
        )
    if tuple(header) == ("fecha", "temperatura"):
        frame = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        records = []
        provenance_name = source_file or file_path.name
        for index, row in frame.iterrows():
            records.append(
                {
                    "source": source,
                    "instrument": instrument,
                    "source_file": provenance_name,
                    "source_row": int(index) + 2,
                    "native_frequency": "30min",
                    "measurement_type": "air_temperature",
                    "raw_timestamp": str(row["fecha"]).strip(),
                    "raw_temperature": str(row["temperatura"]).strip(),
                    "ingest_issue": pd.NA,
                }
            )
        return _records_to_frame(records)
    raise SchemaError(
        f"Expected Davis columns ('fh', 'TempOut', 'hora') or "
        f"('fecha', 'temperatura') in {file_path.name}; found {tuple(header)}"
    )


def _load_interval_extrema_frame(
    frame: pd.DataFrame,
    *,
    source: str,
    instrument: str,
    source_file: str,
) -> pd.DataFrame:
    expected = ("fecha", "Temp_Max", "Temp_Min")
    if tuple(frame.columns) != expected:
        raise SchemaError(
            f"Expected interval-extrema columns {expected}; found {tuple(frame.columns)}"
        )
    records: list[dict[str, object]] = []
    variables = {
        "Temp_Max": "interval_maximum",
        "Temp_Min": "interval_minimum",
    }
    for index, row in frame.iterrows():
        raw_date = "" if pd.isna(row["fecha"]) else str(row["fecha"]).strip()
        metadata_row = not raw_date and any(
            "°c" in str(row[column]).strip().lower()
            or "�c" in str(row[column]).strip().lower()
            for column in variables
        )
        for column, measurement_type in variables.items():
            records.append(
                {
                    "source": source,
                    "instrument": instrument,
                    "source_file": source_file,
                    "source_row": int(index) + 2,
                    "native_frequency": "5min",
                    "measurement_type": measurement_type,
                    "raw_timestamp": raw_date,
                    "raw_temperature": "" if pd.isna(row[column]) else str(row[column]).strip(),
                    "ingest_issue": "metadata_units_row" if metadata_row else pd.NA,
                }
            )
    return _records_to_frame(records)


def load_davis_interval_extrema_xlsx(
    path: str | Path,
    *,
    source: str = "davis_5min_interval_extrema_export",
    instrument: str = "Davis (model unknown)",
    source_file: str | None = None,
) -> pd.DataFrame:
    """Load the recovered Excel export without conflating max/min variables."""

    file_path = Path(path)
    frame = pd.read_excel(file_path, dtype=object, keep_default_na=False)
    return _load_interval_extrema_frame(
        frame,
        source=source,
        instrument=instrument,
        source_file=source_file or file_path.name,
    )


def load_davis_interval_extrema_csv(
    path: str | Path,
    *,
    source: str = "davis_5min_interval_extrema_export",
    instrument: str = "Davis (model unknown)",
    source_file: str | None = None,
) -> pd.DataFrame:
    """Load the public synthetic equivalent of the recovered Excel schema."""

    file_path = Path(path)
    frame = pd.read_csv(file_path, dtype=str, keep_default_na=False)
    return _load_interval_extrema_frame(
        frame,
        source=source,
        instrument=instrument,
        source_file=source_file or file_path.name,
    )


def concatenate_sources(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate normalized sources while enforcing the common schema."""

    materialized = []
    for frame in frames:
        missing = set(COMMON_COLUMNS) - set(frame.columns)
        if missing:
            raise SchemaError(f"Normalized source is missing columns: {sorted(missing)}")
        materialized.append(frame.loc[:, COMMON_COLUMNS])
    if not materialized:
        return pd.DataFrame(columns=COMMON_COLUMNS)
    return pd.concat(materialized, ignore_index=True)
