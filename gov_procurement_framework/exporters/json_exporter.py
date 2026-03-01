"""JSON export implementation for normalized tender records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonExporter:
    """Write full normalized records to a JSON file."""

    def __init__(self, output_dir: str = "output") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, data: list[dict[str, Any]], filename: str) -> None:
        path = self.output_dir / filename
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=True, indent=2)

