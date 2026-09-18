"""Execute every public notebook from a clean kernel with the project as cwd."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"
RUNTIME = ROOT / "tmp" / "jupyter"
for name, value in {
    "IPYTHONDIR": RUNTIME / "ipython",
    "JUPYTER_DATA_DIR": RUNTIME / "data",
    "JUPYTER_CONFIG_DIR": RUNTIME / "config",
    "JUPYTER_RUNTIME_DIR": RUNTIME / "runtime",
    "MPLCONFIGDIR": RUNTIME / "matplotlib",
}.items():
    value.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(name, str(value))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import nbformat
from nbclient import NotebookClient


PUBLIC_NOTEBOOKS = (
    "01_data_quality.ipynb",
    "02_instrument_comparison.ipynb",
    "03_temperature_analysis.ipynb",
)


def main() -> None:
    for name in PUBLIC_NOTEBOOKS:
        path = NOTEBOOKS / name
        notebook = nbformat.read(path, as_version=4)
        client = NotebookClient(
            notebook,
            timeout=300,
            kernel_name="python3",
            resources={"metadata": {"path": str(ROOT)}},
        )
        client.execute()
        nbformat.write(notebook, path)
        print(f"Executed {path}")


if __name__ == "__main__":
    main()
