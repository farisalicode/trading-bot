import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def ensure_parent_dir(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def append_trade_to_csv(csv_path: str, row: Dict[str, Any]) -> None:
    """
    Append a single trade record to a CSV file.
    If the file does not exist, create it and write a header first.
    
    Automatically adds timestamp if not present.
    """
    path = Path(csv_path)
    ensure_parent_dir(path)

    # Add timestamp if not present
    if "timestamp" not in row:
        row["timestamp"] = datetime.now().isoformat()

    file_exists = path.exists()

    with path.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


