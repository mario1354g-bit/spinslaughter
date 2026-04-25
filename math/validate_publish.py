from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent
PUBLISH_DIR = ROOT / "library" / "publish_files"
PAYOUT_MULTIPLIER_SCALE = 100


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


def validate_mode(mode: dict, check_books: bool) -> dict:
    events_path = PUBLISH_DIR / mode["events"]
    weights_path = PUBLISH_DIR / mode["weights"]
    if not events_path.exists():
        raise FileNotFoundError(events_path)
    if not weights_path.exists():
        raise FileNotFoundError(weights_path)

    lookup: dict[int, tuple[int, int]] = {}
    total_probability = 0
    weighted_payout_units = 0
    with weights_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) != 3 or not all(cell.isdigit() for cell in row):
                raise ValueError(f"{weights_path.name} contains non-integer lookup row: {row!r}")
            book_id, probability, payout_units = (int(cell) for cell in row)
            if book_id in lookup:
                raise ValueError(f"{weights_path.name} contains duplicate book id {book_id}")
            lookup[book_id] = (probability, payout_units)
            total_probability += probability
            weighted_payout_units += probability * payout_units

    book_count = None
    if check_books:
        seen_ids: set[int] = set()
        for line_number, line in enumerate(iter_book_lines(events_path), start=1):
            book = json.loads(line)
            book_id = int(book["id"])
            payout_units = int(book["payoutMultiplier"])
            if book_id not in lookup:
                raise ValueError(f"{events_path.name}:{line_number} book id {book_id} is missing from lookup")
            if lookup[book_id][1] != payout_units:
                raise ValueError(f"{events_path.name}:{line_number} payout mismatch for book id {book_id}")
            seen_ids.add(book_id)
        missing = set(lookup) - seen_ids
        if missing:
            sample = ", ".join(str(book_id) for book_id in sorted(missing)[:10])
            raise ValueError(f"{events_path.name} is missing {len(missing)} lookup ids, sample: {sample}")
        book_count = len(seen_ids)

    average_payout = (weighted_payout_units / total_probability) / PAYOUT_MULTIPLIER_SCALE
    cost = float(mode["cost"])
    return {
        "mode": mode["name"],
        "cost": cost,
        "lookupRows": len(lookup),
        "bookRows": book_count,
        "totalProbability": total_probability,
        "weightedPayoutMultiplier": round(average_payout, 6),
        "rtpPercentOfCost": round((average_payout / cost) * 100, 6),
        "events": mode["events"],
        "weights": mode["weights"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the Warpath Reels StakeEngine math publish folder.")
    parser.add_argument("--skip-books", action="store_true", help="Only validate lookup math and referenced file existence.")
    parser.add_argument("--write", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()

    index = json.loads((PUBLISH_DIR / "index.json").read_text(encoding="utf-8"))
    report = [validate_mode(mode, check_books=not args.skip_books) for mode in index["modes"]]

    for item in report:
        print(
            f"{item['mode']}: rows={item['lookupRows']} rtp={item['rtpPercentOfCost']:.6f}% "
            f"weightedPayout={item['weightedPayoutMultiplier']:.6f}x cost={item['cost']:.2f}x"
        )

    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
