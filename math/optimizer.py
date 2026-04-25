from __future__ import annotations

from pathlib import Path


def summarize_lookup_tables(root: Path = Path("library/lookup_tables")) -> dict[str, int]:
    summary: dict[str, int] = {}
    for path in root.glob("lookUpTable_*.csv"):
        with path.open("r", encoding="utf-8") as fh:
            summary[path.stem] = max(0, sum(1 for _ in fh) - 1)
    return summary


if __name__ == "__main__":
    print(summarize_lookup_tables())
