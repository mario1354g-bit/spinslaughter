from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import statistics
from pathlib import Path

from warpath_math.gamestate import GameState
from warpath_math.game_config import GameConfig
from warpath_math.reels import ALL_REEL_SETS
from warpath_math.symbols import ASSET_BY_SYMBOL, HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, SYMBOL_NAMES, WILD


ROOT = Path(__file__).resolve().parent
BOOK_DIR = ROOT / "library" / "books"
LOOKUP_DIR = ROOT / "library" / "lookup_tables"
PUBLISH_DIR = ROOT / "library" / "publish_files"
FRONTEND_BOOK_DIR = ROOT.parent / "frontend" / "static" / "books"


MODES = {
    "base": (4000, None),
    "warpath_buy_8": (1600, None),
    "warpath_buy_10": (1600, None),
    "warpath_buy_12": (1600, None),
}

PROBABILITY_SCALE = 1_000_000
PAYOUT_MULTIPLIER_SCALE = 100


def payout_to_publish_units(payout: float) -> int:
    return max(0, round(float(payout) * PAYOUT_MULTIPLIER_SCALE))


def publish_book(book: dict) -> dict:
    output = dict(book)
    output["payoutMultiplier"] = payout_to_publish_units(float(book["payoutMultiplier"]))
    return output


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_force(force_data: dict[str, dict[str, list[int]]], book: dict) -> None:
    criteria = book["criteria"]
    force_data.setdefault("criteria", {}).setdefault(criteria, []).append(book["id"])
    if any(event.get("type") == "warpathSpinsIntro" for event in book["events"]):
        force_data.setdefault("events", {}).setdefault("warpathSpinsIntro", []).append(book["id"])
    if book["payoutMultiplier"] >= GameConfig().wincap:
        force_data.setdefault("events", {}).setdefault("wincap", []).append(book["id"])
    level = "zero" if book["payoutMultiplier"] == 0 else f"winLevel{GameState().win_level(book['payoutMultiplier'])}"
    force_data.setdefault("winLevels", {}).setdefault(level, []).append(book["id"])


def build_lookup_weights(mode: str, books: list[dict], target_payout: float) -> dict[int, float]:
    weights = {int(book["id"]): 1.0 for book in books}
    if not books:
        return weights

    total_weight = sum(weights.values())
    total_payout = sum(float(book["payoutMultiplier"]) * weights[int(book["id"])] for book in books)
    current_rtp = total_payout / total_weight
    if abs(current_rtp - target_payout) < 0.000001:
        return weights

    if current_rtp > target_payout:
        zero_books = [book for book in books if float(book["payoutMultiplier"]) == 0]
        if not zero_books:
            return weights
        added_weight = total_payout / target_payout - total_weight
        weights[int(zero_books[0]["id"])] += max(0.0, added_weight)
        return weights

    high_book = max(books, key=lambda book: float(book["payoutMultiplier"]))
    high_payout = float(high_book["payoutMultiplier"])
    if high_payout <= target_payout:
        return weights
    added_weight = (target_payout * total_weight - total_payout) / (high_payout - target_payout)
    weights[int(high_book["id"])] += max(0.0, added_weight)
    return weights


def summarize_books(mode: str, books: list[dict], weights: dict[int, float], cost: float) -> dict:
    payouts = [float(book["payoutMultiplier"]) for book in books]
    base_wins = [float(book["baseGameWins"]) for book in books]
    free_wins = [float(book["freeGameWins"]) for book in books]
    total_weight = sum(weights.values())
    weighted_payout = sum(float(book["payoutMultiplier"]) * weights[int(book["id"])] for book in books)
    weighted_hits = sum(weights[int(book["id"])] for book in books if float(book["payoutMultiplier"]) > 0)
    weighted_zeroes = sum(weights[int(book["id"])] for book in books if float(book["payoutMultiplier"]) == 0)
    criteria_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    for book in books:
        criteria_counts[book["criteria"]] = criteria_counts.get(book["criteria"], 0) + 1
        for event in book["events"]:
            event_counts[event["type"]] = event_counts.get(event["type"], 0) + 1
    return {
        "mode": mode,
        "cost": cost,
        "count": len(books),
        "totalWeight": round(total_weight, 6),
        "uniformRtpEstimate": round(sum(payouts) / len(books), 6) if books else 0,
        "weightedRtpEstimate": round(weighted_payout / total_weight, 6) if total_weight else 0,
        "weightedRtpPercentOfCost": round((weighted_payout / total_weight) / cost * 100, 6) if total_weight and cost else 0,
        "hitRate": round(sum(1 for payout in payouts if payout > 0) / len(books), 6) if books else 0,
        "weightedHitRate": round(weighted_hits / total_weight, 6) if total_weight else 0,
        "zeroRate": round(sum(1 for payout in payouts if payout == 0) / len(books), 6) if books else 0,
        "weightedZeroRate": round(weighted_zeroes / total_weight, 6) if total_weight else 0,
        "bonusTriggerRate": round(criteria_counts.get("freegame", 0) / len(books), 6) if books and mode == "base" else 0,
        "maxWinRate": round(criteria_counts.get("wincap", 0) / len(books), 6) if books else 0,
        "averagePayout": round(statistics.fmean(payouts), 6) if payouts else 0,
        "medianPayout": round(statistics.median(payouts), 6) if payouts else 0,
        "standardDeviation": round(statistics.pstdev(payouts), 6) if len(payouts) > 1 else 0,
        "maxPayout": round(max(payouts), 2) if payouts else 0,
        "averageBaseWin": round(statistics.fmean(base_wins), 6) if base_wins else 0,
        "averageFreeWin": round(statistics.fmean(free_wins), 6) if free_wins else 0,
        "criteriaCounts": criteria_counts,
        "eventCounts": event_counts,
    }


def write_mode(mode: str, count: int, force: str | None) -> tuple[list[dict], dict]:
    state = GameState()
    books_path = BOOK_DIR / f"books_{mode}.jsonl"
    lookup_path = LOOKUP_DIR / f"lookUpTable_{mode}.csv"
    criteria_path = LOOKUP_DIR / f"lookUpTableIdToCriteria_{mode}.csv"
    segmented_path = LOOKUP_DIR / f"lookUpTableSegmented_{mode}.csv"
    books_path.parent.mkdir(parents=True, exist_ok=True)
    lookup_path.parent.mkdir(parents=True, exist_ok=True)
    books: list[dict] = []
    force_data: dict[str, dict[str, list[int]]] = {}
    for sim_id in range(1, count + 1):
        book = state.build_spin(sim_id, mode=mode, force=force)
        books.append(book)
        record_force(force_data, book)
    config = GameConfig()
    weights = build_lookup_weights(mode, books, config.target_payout_multiplier(mode))

    with (
        books_path.open("w", encoding="utf-8") as books_file,
        lookup_path.open("w", newline="", encoding="utf-8") as lookup_file,
        criteria_path.open("w", newline="", encoding="utf-8") as criteria_file,
        segmented_path.open("w", newline="", encoding="utf-8") as segmented_file,
    ):
        lookup_writer = csv.writer(lookup_file)
        criteria_writer = csv.writer(criteria_file)
        segmented_writer = csv.writer(segmented_file)
        criteria_writer.writerow(["id", "criteria"])
        segmented_writer.writerow(["id", "criteria", "baseGameWins", "freeGameWins", "payoutMultiplier"])
        for book in books:
            books_file.write(json.dumps(publish_book(book), separators=(",", ":")) + "\n")
            probability = max(1, round(weights[int(book["id"])] * PROBABILITY_SCALE))
            lookup_writer.writerow([book["id"], probability, payout_to_publish_units(float(book["payoutMultiplier"]))])
            criteria_writer.writerow([book["id"], book["criteria"]])
            segmented_writer.writerow([book["id"], book["criteria"], book["baseGameWins"], book["freeGameWins"], book["payoutMultiplier"]])
    (PUBLISH_DIR / f"force_{mode}.json").write_text(json.dumps(force_data, indent=2), encoding="utf-8")
    return books, force_data


def compress_book_files() -> set[str]:
    if not shutil.which("zstd"):
        return set()
    compressed: set[str] = set()
    for path in BOOK_DIR.glob("books_*.jsonl"):
        output = path.with_suffix(path.suffix + ".zst")
        subprocess.run(["zstd", "-q", "-f", str(path), "-o", str(output)], check=True)
        compressed.add(output.name)
    return compressed


def write_reels() -> None:
    reel_dir = ROOT / "static-reels"
    reel_dir.mkdir(parents=True, exist_ok=True)
    for path in reel_dir.glob("reels_*.csv"):
        path.unlink()
    for mode, reel_set in ALL_REEL_SETS.items():
        max_len = max(len(reel) for reel in reel_set)
        path = reel_dir / f"reels_{mode.replace('_spins', '')}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([f"reel_{index + 1}" for index in range(len(reel_set))])
            for row in range(max_len):
                writer.writerow([reel[row] if row < len(reel) else "" for reel in reel_set])


def write_config_files(index: dict, summaries: dict[str, dict]) -> None:
    config = GameConfig()
    config_math = {
        "gameId": config.game_id,
        "workingName": config.working_name,
        "rtp": config.rtp,
        "wincap": config.wincap,
        "winType": config.win_type,
        "numReels": config.num_reels,
        "numRows": list(config.num_rows),
        "wildSymbol": config.wild_symbol,
        "bonusTriggerSymbol": config.bonus_trigger_symbol,
        "specialSymbols": config.special_symbols,
        "paytable": config.paytable,
        "modePayScale": config.mode_pay_scale,
        "freeSpinTriggers": config.free_spin_triggers,
        "betModes": [
            {
                "name": mode.name,
                "cost": mode.cost,
                "rtp": mode.rtp,
                "maxWin": mode.max_win,
                "isFeature": mode.is_feature,
                "isBuyBonus": mode.is_buybonus,
                "isInternalBonus": mode.is_internal_bonus,
                "distributions": [
                    {
                        "criteria": distribution.criteria,
                        "quota": distribution.quota,
                        "winCriteria": distribution.win_criteria,
                        "conditions": distribution.conditions,
                    }
                    for distribution in mode.distributions
                ],
            }
            for mode in config.bet_modes
        ],
        "summaries": summaries,
    }
    config_fe = {
        "gameId": config.game_id,
        "workingName": config.working_name,
        "numRows": list(config.num_rows),
        "totalWays": config.total_ways,
        "wildSymbol": config.wild_symbol,
        "bonusTriggerSymbol": config.bonus_trigger_symbol,
        "specialSymbols": config.special_symbols,
        "symbols": [
            {
                "id": symbol,
                "name": SYMBOL_NAMES[symbol],
                "asset": ASSET_BY_SYMBOL[symbol],
                "tier": "low" if symbol in LOW_SYMBOLS else "wild" if symbol == WILD else "scatter" if symbol == SCATTER else "premium" if symbol == "LS" else "high",
            }
            for symbol in [*LOW_SYMBOLS, *HIGH_SYMBOLS, WILD, SCATTER]
        ],
        "betModes": [{"name": mode.name, "cost": mode.cost, "isFeature": mode.is_feature, "isBuyBonus": mode.is_buybonus} for mode in config.bet_modes],
    }
    (PUBLISH_DIR / "config_math.json").write_text(json.dumps(config_math, indent=2), encoding="utf-8")
    (PUBLISH_DIR / "config_fe.json").write_text(json.dumps(config_fe, indent=2), encoding="utf-8")
    file_hashes = {path.name: file_sha256(path) for path in sorted(PUBLISH_DIR.glob("*")) if path.is_file() and path.name != "config.json"}
    (PUBLISH_DIR / "config.json").write_text(json.dumps({**index, "fileHashes": file_hashes}, indent=2), encoding="utf-8")


def copy_publish_artifacts(index: dict) -> None:
    for mode in MODES:
        event_file = next(item["events"] for item in index["modes"] if item["name"] == mode)
        shutil.copy2(BOOK_DIR / event_file, PUBLISH_DIR / event_file)
        shutil.copy2(LOOKUP_DIR / f"lookUpTable_{mode}.csv", PUBLISH_DIR / f"lookUpTable_{mode}.csv")


def main() -> None:
    config = GameConfig()
    config.validate()
    for directory in [BOOK_DIR, LOOKUP_DIR, PUBLISH_DIR, FRONTEND_BOOK_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    for path in [
        *BOOK_DIR.glob("books_*.jsonl"),
        *BOOK_DIR.glob("books_*.jsonl.zst"),
        *FRONTEND_BOOK_DIR.glob("books_*.jsonl"),
        *FRONTEND_BOOK_DIR.glob("lookUpTable_*.csv"),
    ]:
        path.unlink()
    for path in [*LOOKUP_DIR.glob("lookUpTable_*.csv"), *LOOKUP_DIR.glob("lookUpTableIdToCriteria_*.csv"), *LOOKUP_DIR.glob("lookUpTableSegmented_*.csv")]:
        path.unlink()
    for path in [
        *PUBLISH_DIR.glob("books_*.jsonl"),
        *PUBLISH_DIR.glob("books_*.jsonl.zst"),
        *PUBLISH_DIR.glob("lookUpTable_*.csv"),
        *PUBLISH_DIR.glob("force*.json"),
        *PUBLISH_DIR.glob("config*.json"),
        PUBLISH_DIR / "math_summary.json",
        PUBLISH_DIR / "index.json",
    ]:
        if path.exists():
            path.unlink()
    write_reels()
    summaries: dict[str, dict] = {}
    combined_force: dict[str, dict[str, list[int]]] = {}
    for mode, (count, force) in MODES.items():
        books, force_data = write_mode(mode, count, force)
        weights = build_lookup_weights(mode, books, config.target_payout_multiplier(mode))
        summaries[mode] = summarize_books(mode, books, weights, config.betmode_cost(mode))
        for category, keys in force_data.items():
            combined_force.setdefault(category, {})
            for key, ids in keys.items():
                combined_force[category].setdefault(f"{mode}:{key}", []).extend(ids)
    compressed_books = compress_book_files()
    publish_book_format = "jsonl.zst" if compressed_books else "jsonl"
    index = {
        "modes": [
            {
                "name": mode,
                "cost": config.betmode_cost(mode),
                "events": f"books_{mode}.jsonl.zst" if f"books_{mode}.jsonl.zst" in compressed_books else f"books_{mode}.jsonl",
                "weights": f"lookUpTable_{mode}.csv",
            }
            for mode in MODES
        ],
    }
    copy_publish_artifacts(index)
    (PUBLISH_DIR / "force.json").write_text(json.dumps(combined_force, indent=2), encoding="utf-8")
    (PUBLISH_DIR / "math_summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    (PUBLISH_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    write_config_files(index, summaries)
    frontend_index = {
        "gameId": config.game_id,
        "workingName": config.working_name,
        "modes": list(MODES.keys()),
        "modeCosts": {mode: config.betmode_cost(mode) for mode in MODES},
        "bookFormat": "jsonl",
    }
    (BOOK_DIR / "index.json").write_text(json.dumps(frontend_index, indent=2), encoding="utf-8")
    for path in BOOK_DIR.glob("books_*.jsonl"):
        shutil.copy2(path, FRONTEND_BOOK_DIR / path.name)
    for path in LOOKUP_DIR.glob("lookUpTable_*.csv"):
        shutil.copy2(path, FRONTEND_BOOK_DIR / path.name)
    shutil.copy2(BOOK_DIR / "index.json", FRONTEND_BOOK_DIR / "index.json")
    print(f"Generated {len(MODES)} book sets in {BOOK_DIR}")
    for mode, summary in summaries.items():
        print(
            f"{mode}: count={summary['count']} uniformRTP={summary['uniformRtpEstimate']} "
            f"weightedRTP={summary['weightedRtpEstimate']} costRTP={summary['weightedRtpPercentOfCost']}% hit={summary['hitRate']} "
            f"max={summary['maxPayout']} criteria={summary['criteriaCounts']}"
        )


if __name__ == "__main__":
    main()
