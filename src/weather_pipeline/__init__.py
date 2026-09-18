"""Instrument-aware processing for recovered San Ramón weather observations."""

from .analysis import compare_instruments, monthly_temperature_summary, source_summary
from .harmonize import combine_sources, resample_hourly
from .ingest import (
    COMMON_COLUMNS,
    SchemaError,
    concatenate_sources,
    load_campbell_csv,
    load_davis_30min_csv,
    load_davis_interval_extrema_csv,
    load_davis_interval_extrema_xlsx,
)
from .quality import apply_quality_flags, detect_gaps

__all__ = [
    "COMMON_COLUMNS",
    "SchemaError",
    "apply_quality_flags",
    "combine_sources",
    "compare_instruments",
    "concatenate_sources",
    "detect_gaps",
    "load_campbell_csv",
    "load_davis_30min_csv",
    "load_davis_interval_extrema_csv",
    "load_davis_interval_extrema_xlsx",
    "monthly_temperature_summary",
    "resample_hourly",
    "source_summary",
]
