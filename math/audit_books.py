from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent
PUBLISH_DIR = ROOT / "library" / "publish_files"
PAYOUT_MULTIPLIER_SCALE = 100
TOLERANCE = 0.011


def iter_book_lines(path: Path) -> Iterator[str]:
    if path.suffix == ".zst":
        process = subprocess.Popen(["zstd", "-dc", str(path)], stdout=subprocess.PIPE, text=True)
        assert process.stdout is not None
        try:
            yield from process.stdout
        finally:
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"zstd failed while reading {path}")
        return
    with path.open(encoding="utf-8") as handle:
        yield from handle


def final_win_amount(book: dict) -> float | None:
    for event in reversed(book.get("events", [])):
        if event.get("type") == "finalWin":
            return float(event.get("amount", 0))
    return None


def last_total_win_amount(book: dict) -> float | None:
    for event in reversed(book.get("events", [])):
        if event.get("type") == "setTotalWin":
            return float(event.get("amount", 0))
    return None


def audit_book(book: dict, source: str) -> None:
    events = book.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError(f"{source}: book {book.get('id')} has no events")

    indexes = [event.get("index") for event in events]
    expected = list(range(len(events)))
    if indexes != expected:
        raise ValueError(f"{source}: book {book.get('id')} event indexes are not sequential")

    final_amount = final_win_amount(book)
    if final_amount is None:
        raise ValueError(f"{source}: book {book.get('id')} has no finalWin event")

    total_amount = last_total_win_amount(book)
    if total_amount is not None and abs(total_amount - final_amount) > TOLERANCE:
        raise ValueError(f"{source}: book {book.get('id')} setTotalWin {total_amount} != finalWin {final_amount}")

    payout_amount = float(book.get("payoutMultiplier", 0)) / PAYOUT_MULTIPLIER_SCALE
    if abs(payout_amount - final_amount) > TOLERANCE:
        raise ValueError(f"{source}: book {book.get('id')} payoutMultiplier {payout_amount} != finalWin {final_amount}")


def audit_mode(mode: dict) -> dict:
    path = PUBLISH_DIR / mode["events"]
    count = 0
    for line_number, line in enumerate(iter_book_lines(path), start=1):
        audit_book(json.loads(line), f"{path.name}:{line_number}")
        count += 1
    return {"mode": mode["name"], "books": count, "events": mode["events"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Warpath Reels book event payout consistency.")
    parser.add_argument("--write", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()

    index = json.loads((PUBLISH_DIR / "index.json").read_text(encoding="utf-8"))
    report = [audit_mode(mode) for mode in index["modes"]]
    for item in report:
        print(f"{item['mode']}: audited {item['books']} books from {item['events']}")

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

