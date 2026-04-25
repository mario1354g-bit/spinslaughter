from __future__ import annotations

import argparse
import math
import time
from collections import Counter

from warpath_math.gamestate import GameState
from warpath_math.game_config import GameConfig


def run(mode: str, spins: int, start_id: int = 1) -> dict:
    state = GameState()
    config = GameConfig()
    cost = config.betmode_cost(mode)
    payouts: list[float] = []
    criteria = Counter()
    event_counts = Counter()
    base_total = 0.0
    free_total = 0.0
    started = time.perf_counter()

    for offset in range(spins):
        book = state.build_spin(start_id + offset, mode=mode)
        payout = float(book["payoutMultiplier"])
        payouts.append(payout)
        criteria[book["criteria"]] += 1
        base_total += float(book["baseGameWins"])
        free_total += float(book["freeGameWins"])
        event_counts.update(event["type"] for event in book["events"])

    mean = sum(payouts) / spins
    variance = sum((payout - mean) ** 2 for payout in payouts) / spins
    stddev = math.sqrt(variance)
    stderr = stddev / math.sqrt(spins)
    return {
        "mode": mode,
        "cost": cost,
        "spins": spins,
        "rtp": mean,
        "rtpPercent": (mean / cost) * 100 if cost else 0,
        "payoutPerBaseBet": mean,
        "hitRate": sum(1 for payout in payouts if payout > 0) / spins,
        "zeroRate": sum(1 for payout in payouts if payout == 0) / spins,
        "bonusTriggerRate": criteria["freegame"] / spins if mode == "base" else 0,
        "maxWinRate": criteria["wincap"] / spins,
        "maxPayout": max(payouts),
        "medianPayout": sorted(payouts)[spins // 2],
        "stddev": stddev,
        "stderr": stderr,
        "confidence95": (mean - 1.96 * stderr, mean + 1.96 * stderr),
        "averageBaseWin": base_total / spins,
        "averageFreeWin": free_total / spins,
        "criteriaCounts": dict(criteria),
        "eventCounts": dict(event_counts),
        "seconds": time.perf_counter() - started,
    }


def main() -> None:
    config = GameConfig()
    valid_modes = ["base", *config.buy_feature_spins.keys()]
    parser = argparse.ArgumentParser(description="Run deterministic Warpath Reels math simulation.")
    parser.add_argument("--mode", choices=valid_modes, default="base")
    parser.add_argument("--spins", type=int, default=100_000)
    parser.add_argument("--start-id", type=int, default=1)
    args = parser.parse_args()

    config.validate()
    result = run(args.mode, args.spins, args.start_id)
    low, high = result["confidence95"]
    print(f"mode={result['mode']} spins={result['spins']} seconds={result['seconds']:.2f}")
    print(f"cost={result['cost']:.2f}x")
    print(f"RTP={result['rtpPercent']:.4f}% ({result['payoutPerBaseBet']:.6f}x paid per 1x base bet)")
    print(f"95% CI={(low / result['cost']) * 100:.4f}% to {(high / result['cost']) * 100:.4f}%")
    print(f"hitRate={result['hitRate'] * 100:.4f}% zeroRate={result['zeroRate'] * 100:.4f}%")
    if result["mode"] == "base":
        print(f"bonusTriggerRate={result['bonusTriggerRate'] * 100:.4f}%")
    print(f"maxPayout={result['maxPayout']:.2f}x median={result['medianPayout']:.2f}x stddev={result['stddev']:.6f}")
    print(f"averageBaseWin={result['averageBaseWin']:.6f}x averageFreeWin={result['averageFreeWin']:.6f}x")
    print(f"criteriaCounts={result['criteriaCounts']}")
    print(f"eventCounts={result['eventCounts']}")


if __name__ == "__main__":
    main()
