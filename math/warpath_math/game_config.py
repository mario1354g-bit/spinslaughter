from dataclasses import dataclass, field
from typing import Any

from .paytable import PAYTABLE
from .reels import ALL_REEL_SETS, ROWS_PER_REEL
from .symbols import HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, WILD


@dataclass(frozen=True)
class Distribution:
    criteria: str
    quota: float
    win_criteria: float | None = None
    conditions: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BetMode:
    name: str
    cost: float
    description: str
    rtp: float = 0.96
    max_win: float = 5000.0
    auto_close_disabled: bool = False
    is_feature: bool = False
    is_buybonus: bool = False
    is_internal_bonus: bool = False
    distributions: tuple[Distribution, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GameConfig:
    game_id: str = "warpath_reels"
    provider_number: int = 0
    working_name: str = "Warpath Reels"
    win_type: str = "ways"
    rtp: float = 0.96
    wincap: int = 5000
    num_reels: int = 6
    num_rows: tuple[int, ...] = tuple(ROWS_PER_REEL)
    total_ways: int = 324
    low_symbols: tuple[str, ...] = tuple(LOW_SYMBOLS)
    high_symbols: tuple[str, ...] = tuple(HIGH_SYMBOLS)
    wild_symbol: str = WILD
    bonus_trigger_symbol: str = SCATTER
    special_symbols: dict[str, tuple[str, ...]] = field(default_factory=lambda: {"wild": (WILD,), "bonus": (SCATTER,), "scatter": (SCATTER,)})
    paytable: dict = field(default_factory=lambda: PAYTABLE)
    mode_pay_scale: dict[str, float] = field(
        default_factory=lambda: {
            "base": 0.93,
            "warpath_spins": 0.000055,
            "warpath_buy_8": 0.000609,
            "warpath_buy_10": 0.000348,
            "warpath_buy_12": 0.000233,
        }
    )
    free_spin_triggers: dict[int, int] = field(default_factory=lambda: {3: 8, 4: 10, 5: 12})
    buy_feature_spins: dict[str, int] = field(default_factory=lambda: {"warpath_buy_8": 8, "warpath_buy_10": 10, "warpath_buy_12": 12})
    feature_start_multipliers: dict[str, int] = field(
        default_factory=lambda: {
            "warpath_spins": 2,
            "warpath_buy_8": 3,
            "warpath_buy_10": 4,
            "warpath_buy_12": 5,
        }
    )
    max_cascades: int = 6
    escalation_levels: tuple[int, ...] = (1, 2, 3, 4, 5)
    bet_modes: tuple[BetMode, ...] = (
        BetMode(
            name="base",
            cost=1.0,
            description="Base game with Warpath Spins trigger",
            is_feature=True,
            distributions=(
                Distribution("0", 0.58, conditions={"reel_weights": {"base": {"base": 1}}}),
                Distribution("basegame", 0.395, conditions={"reel_weights": {"base": {"base": 1}}}),
                Distribution("freegame", 0.024, conditions={"reel_weights": {"base": {"base": 1}, "warpath_spins": {"warpath_spins": 1}}}),
                Distribution("wincap", 0.001, win_criteria=5000.0, conditions={"force_wincap": True}),
            ),
        ),
        BetMode(
            name="warpath_buy_8",
            cost=80.0,
            description="Buy Warpath Spins - 8 spins",
            is_buybonus=True,
            distributions=(
                Distribution("freegame", 0.999, conditions={"reel_weights": {"warpath_buy_8": {"warpath_spins": 1}}, "force_freegame": True}),
                Distribution("wincap", 0.001, win_criteria=5000.0, conditions={"force_wincap": True, "force_freegame": True}),
            ),
        ),
        BetMode(
            name="warpath_buy_10",
            cost=100.0,
            description="Buy Warpath Spins - 10 spins",
            is_buybonus=True,
            distributions=(
                Distribution("freegame", 0.999, conditions={"reel_weights": {"warpath_buy_10": {"warpath_spins": 1}}, "force_freegame": True}),
                Distribution("wincap", 0.001, win_criteria=5000.0, conditions={"force_wincap": True, "force_freegame": True}),
            ),
        ),
        BetMode(
            name="warpath_buy_12",
            cost=120.0,
            description="Buy Warpath Spins - 12 spins",
            is_buybonus=True,
            distributions=(
                Distribution("freegame", 0.999, conditions={"reel_weights": {"warpath_buy_12": {"warpath_spins": 1}}, "force_freegame": True}),
                Distribution("wincap", 0.001, win_criteria=5000.0, conditions={"force_wincap": True, "force_freegame": True}),
            ),
        ),
    )

    def betmode_cost(self, mode_name: str) -> float:
        for mode in self.bet_modes:
            if mode.name == mode_name:
                return mode.cost
        return 1.0

    def target_payout_multiplier(self, mode_name: str) -> float:
        return self.betmode_cost(mode_name) * self.rtp

    def validate(self) -> None:
        if self.num_reels != len(self.num_rows):
            raise ValueError("num_reels must match num_rows")
        if self.num_rows != (2, 3, 3, 3, 3, 2):
            raise ValueError("Warpath Reels must use the 2-3-3-3-3-2 layout")
        if self.total_ways != 2 * 3 * 3 * 3 * 3 * 2:
            raise ValueError("total_ways must match the configured reel layout")
        valid_symbols = set(self.low_symbols + self.high_symbols + (self.wild_symbol, self.bonus_trigger_symbol))
        pay_symbols = set(self.paytable)
        if not pay_symbols.issubset(valid_symbols):
            raise ValueError(f"Paytable contains invalid symbols: {sorted(pay_symbols - valid_symbols)}")
        for mode, reel_set in ALL_REEL_SETS.items():
            if len(reel_set) != self.num_reels:
                raise ValueError(f"{mode} reel set must contain {self.num_reels} reels")
            for reel_index, strip in enumerate(reel_set):
                invalid = set(strip) - valid_symbols
                if invalid:
                    raise ValueError(f"{mode} reel {reel_index + 1} contains invalid symbols: {sorted(invalid)}")
