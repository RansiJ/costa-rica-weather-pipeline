"""Generate the small public dataset used by the reproducible notebooks.

Every value produced here is synthetic. The series imitate the surviving file
schemas and selected failure modes; they are not reconstructed observations.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "data" / "sample"


def temperature(timestamp: datetime) -> float:
    hour_cycle = 3.4 * math.sin(2 * math.pi * (timestamp.hour - 8) / 24)
    seasonal = 0.7 * math.sin(2 * math.pi * timestamp.timetuple().tm_yday / 45)
    return 20.5 + hour_cycle + seasonal


def write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def build_campbell() -> None:
    start = datetime(2017, 4, 17, 12)
    rows: list[list[object]] = []
    for offset in range(90 * 24):
        timestamp = start + timedelta(hours=offset)
        value = temperature(timestamp) + 1.25 + 0.06 * math.sin(offset * 0.7)
        rows.append([timestamp.date().isoformat(), f"{value:.2f}", timestamp.time().isoformat()])
    rows[48], rows[49] = rows[49], rows[48]
    rows.insert(200, rows[199].copy())
    rows[600][1] = "2.00"
    rows.append(["invalid-date", "not-a-number", "08:00:00"])
    rows.append(["2017-06-01", "21.0", "08-", "22.0", "09:00:00"])
    write_csv(OUTPUT / "synthetic_campbell_hourly.csv", ["fh", "temp", "hora"], rows)


def build_davis_30min() -> None:
    start = datetime(2017, 4, 17, 12)
    rows: list[list[object]] = []
    for offset in range(90 * 48):
        timestamp = start + timedelta(minutes=30 * offset)
        value = temperature(timestamp) + 0.05 * math.cos(offset * 0.5)
        rows.append([timestamp.date().isoformat(), f"{value:.2f}", timestamp.time().isoformat()])
    del rows[300:304]
    rows.insert(500, rows[499].copy())
    rows[900][1] = "45.00"
    write_csv(OUTPUT / "synthetic_davis_30min.csv", ["fh", "TempOut", "hora"], rows)


def build_davis_extrema() -> None:
    start = datetime(2017, 9, 13)
    rows: list[list[object]] = []
    for offset in range(14 * 24 * 12):
        timestamp = start + timedelta(minutes=5 * offset)
        center = temperature(timestamp) - 0.4
        maximum = center + 0.12
        minimum = center - 0.12
        if offset == 800:
            rows.append([timestamp.isoformat(sep=" "), "", ""])
        else:
            rows.append(
                [timestamp.isoformat(sep=" "), f"{maximum:.2f}", f"{minimum:.2f}"]
            )
    write_csv(
        OUTPUT / "synthetic_davis_5min_extrema.csv",
        ["fecha", "Temp_Max", "Temp_Min"],
        rows,
    )


def main() -> None:
    build_campbell()
    build_davis_30min()
    build_davis_extrema()
    print(f"Synthetic sample written to {OUTPUT}")


if __name__ == "__main__":
    main()
