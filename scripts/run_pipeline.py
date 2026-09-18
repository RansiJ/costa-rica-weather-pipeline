"""Run the compact pipeline on public synthetic data or explicit local files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from weather_pipeline import (
    apply_quality_flags,
    concatenate_sources,
    detect_gaps,
    load_campbell_csv,
    load_davis_30min_csv,
    load_davis_interval_extrema_csv,
    load_davis_interval_extrema_xlsx,
    resample_hourly,
    source_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campbell", type=Path)
    parser.add_argument("--davis-30min", type=Path)
    parser.add_argument("--davis-extrema", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    provided = sum(
        path is not None for path in (args.campbell, args.davis_30min, args.davis_extrema)
    )
    if provided not in {0, 3}:
        parser.error(
            "provide all three local source paths or none (synthetic demo mode)"
        )
    return args


def main() -> None:
    args = parse_args()
    sample = Path("data/sample")
    using_demo = not any((args.campbell, args.davis_30min, args.davis_extrema))
    campbell_path = args.campbell or sample / "synthetic_campbell_hourly.csv"
    davis_path = args.davis_30min or sample / "synthetic_davis_30min.csv"
    extrema_path = args.davis_extrema or sample / "synthetic_davis_5min_extrema.csv"

    label_prefix = "synthetic_" if using_demo else ""
    frames = [
        load_campbell_csv(
            campbell_path,
            source=f"{label_prefix}campbell_hourly",
            instrument=(
                "Synthetic Campbell-like source"
                if using_demo
                else "Campbell (model unknown)"
            ),
        ),
        load_davis_30min_csv(
            davis_path,
            source=f"{label_prefix}davis_30min",
            instrument=("Synthetic Davis-like source" if using_demo else "Davis (model unknown)"),
        ),
    ]
    if extrema_path.suffix.lower() == ".xlsx":
        extrema = load_davis_interval_extrema_xlsx(
            extrema_path,
            source=f"{label_prefix}davis_5min_interval_extrema",
            instrument=("Synthetic Davis-like source" if using_demo else "Davis (model unknown)"),
        )
    else:
        extrema = load_davis_interval_extrema_csv(
            extrema_path,
            source=f"{label_prefix}davis_5min_interval_extrema",
            instrument=("Synthetic Davis-like source" if using_demo else "Davis (model unknown)"),
        )
    frames.append(extrema)

    observations = apply_quality_flags(concatenate_sources(frames))
    gaps = detect_gaps(observations)
    hourly = resample_hourly(observations, statistic="mean", minimum_coverage=0.5)
    summary = source_summary(observations)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    observations.to_csv(args.output_dir / "weather_observations.csv", index=False)
    gaps.to_csv(args.output_dir / "temporal_gaps.csv", index=False)
    hourly.to_csv(args.output_dir / "hourly_temperature.csv", index=False)
    summary.to_csv(args.output_dir / "source_summary.csv", index=False)
    print(
        json.dumps(
            {
                "mode": "synthetic_demo" if using_demo else "explicit_local_sources",
                "observations": len(observations),
                "qc_pass": int(observations["qc_pass"].sum()),
                "gaps": len(gaps),
                "hourly_rows": len(hourly),
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
