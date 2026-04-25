from __future__ import annotations

import random

from .symbols import HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, WILD

ROWS_PER_REEL = [2, 3, 3, 3, 3, 2]

WeightedStrip = list[tuple[str, int]]


def _make_strip(weighted_symbols: WeightedStrip, salt: int) -> list[str]:
    strip: list[str] = []
    for symbol, count in weighted_symbols:
        strip.extend([symbol] * count)
    random.Random(20_260_425 + salt).shuffle(strip)
    return strip


BASE_REEL_WEIGHTS: list[WeightedStrip] = [
    [
        ("T", 10),
        ("J", 10),
        ("Q", 10),
        ("K", 10),
        ("WS", 4),
        ("IS", 4),
        ("IY", 4),
        ("TO", 4),
        ("LS", 4),
        (SCATTER, 3),
    ],
    [
        ("T", 10),
        ("J", 9),
        ("Q", 9),
        ("K", 9),
        ("WS", 4),
        ("IS", 4),
        ("IY", 4),
        ("TO", 4),
        ("LS", 4),
        (WILD, 3),
        (SCATTER, 3),
    ],
    [
        ("T", 9),
        ("J", 10),
        ("Q", 9),
        ("K", 9),
        ("WS", 4),
        ("IS", 4),
        ("IY", 4),
        ("TO", 4),
        ("LS", 4),
        (WILD, 3),
        (SCATTER, 3),
    ],
    [
        ("T", 9),
        ("J", 9),
        ("Q", 10),
        ("K", 9),
        ("WS", 4),
        ("IS", 4),
        ("IY", 4),
        ("TO", 4),
        ("LS", 4),
        (WILD, 3),
        (SCATTER, 3),
    ],
    [
        ("T", 9),
        ("J", 9),
        ("Q", 9),
        ("K", 10),
        ("WS", 4),
        ("IS", 4),
        ("IY", 4),
        ("TO", 4),
        ("LS", 4),
        (WILD, 3),
        (SCATTER, 3),
    ],
    [
        ("T", 10),
        ("J", 10),
        ("Q", 10),
        ("K", 10),
        ("WS", 5),
        ("IS", 5),
        ("IY", 5),
        ("TO", 5),
        ("LS", 4),
        (SCATTER, 3),
    ],
]

def _without_scatter(weights: WeightedStrip) -> WeightedStrip:
    return [(symbol, count) for symbol, count in weights if symbol != SCATTER]


WARPATH_REEL_WEIGHTS: list[WeightedStrip] = [
    _without_scatter(BASE_REEL_WEIGHTS[0]),
    [*_without_scatter(BASE_REEL_WEIGHTS[1]), (WILD, 1), ("LS", 1)],
    [*_without_scatter(BASE_REEL_WEIGHTS[2]), (WILD, 1), ("LS", 1)],
    [*_without_scatter(BASE_REEL_WEIGHTS[3]), (WILD, 1), ("LS", 1)],
    [*_without_scatter(BASE_REEL_WEIGHTS[4]), (WILD, 1), ("LS", 1)],
    [*_without_scatter(BASE_REEL_WEIGHTS[5]), ("LS", 1)],
]

BASE_REELS = [_make_strip(weights, index) for index, weights in enumerate(BASE_REEL_WEIGHTS)]
WARPATH_REELS = [_make_strip(weights, 100 + index) for index, weights in enumerate(WARPATH_REEL_WEIGHTS)]
ALL_REEL_SETS = {"base": BASE_REELS, "warpath_spins": WARPATH_REELS}


def reel_set_for_mode(mode: str):
    if mode.startswith("warpath_"):
        return WARPATH_REELS
    return ALL_REEL_SETS.get(mode, BASE_REELS)


def reel6_symbols_only_soldiers_or_basics() -> bool:
    valid_symbols = set(HIGH_SYMBOLS + LOW_SYMBOLS + [WILD, SCATTER])
    return all(symbol in valid_symbols for symbol in BASE_REELS[5])
