from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any

from .features import escalation_level
from .game_config import GameConfig
from .paytable import PAYTABLE
from .reels import ROWS_PER_REEL, reel_set_for_mode
from .symbols import SCATTER, WILD


Board = list[list[dict[str, str]]]

MODE_SEED_SALT = {
    "base": 104_729,
    "warpath_spins": 209_759,
    "warpath_buy_8": 314_159,
    "warpath_buy_10": 419_431,
    "warpath_buy_12": 524_287,
}


@dataclass
class GameState:
    config: GameConfig = field(default_factory=GameConfig)
    rng: random.Random = field(default_factory=random.Random)

    def symbol(self, name: str) -> dict[str, str]:
        return {"name": name}

    def reset_seed(self, sim_id: int, mode: str) -> None:
        salt = MODE_SEED_SALT.get(mode, 0)
        self.rng.seed(sim_id * 1_000_003 + salt)

    def draw_board(self, mode: str) -> tuple[Board, list[int]]:
        reels = reel_set_for_mode(mode)
        board: Board = []
        reel_positions: list[int] = []
        for reel_index, rows in enumerate(ROWS_PER_REEL):
            strip = reels[reel_index]
            start = self.rng.randrange(len(strip))
            reel_positions.append(start)
            board.append([self.symbol(strip[(start + row) % len(strip)]) for row in range(rows)])
        return board, reel_positions

    def count_symbol(self, board: Board, symbol: str) -> int:
        return sum(1 for reel in board for sym in reel if sym["name"] == symbol)

    def anticipation(self, board: Board) -> list[int]:
        return [int(any(cell["name"] == SCATTER for cell in reel)) for reel in board]

    def buy_trigger_count_for_spins(self, spins: int) -> int:
        by_spins = {spins_awarded: scatter_count for scatter_count, spins_awarded in self.config.free_spin_triggers.items()}
        return by_spins.get(spins, 0)

    def build_buy_trigger_board(self, scatter_count: int) -> Board:
        board: Board = [
            [self.symbol("T"), self.symbol("J")],
            [self.symbol("Q"), self.symbol("K"), self.symbol("WS")],
            [self.symbol("IS"), self.symbol("IY"), self.symbol("TO")],
            [self.symbol("LS"), self.symbol("T"), self.symbol("J")],
            [self.symbol("Q"), self.symbol("K"), self.symbol("WS")],
            [self.symbol("IS"), self.symbol("IY")],
        ]
        scatter_positions = [(1, 1), (2, 1), (3, 1), (4, 1), (5, 0)]
        for reel, row in scatter_positions[:scatter_count]:
            board[reel][row] = self.symbol(SCATTER)
        return board

    def append_buy_trigger_reveal(self, events: list[dict[str, Any]], spins: int, mode: str) -> int:
        scatter_count = self.buy_trigger_count_for_spins(spins)
        board = self.build_buy_trigger_board(scatter_count)
        events.append(
            {
                "type": "reveal",
                "board": copy.deepcopy(board),
                "paddingPositions": [0 for _ in ROWS_PER_REEL],
                "gameType": mode,
                "anticipation": self.anticipation(board),
                "presentation": "buyTrigger",
            }
        )
        return scatter_count

    def evaluate_ways(self, board: Board, multiplier: int = 1, mode: str = "base") -> tuple[float, list[dict[str, Any]]]:
        wins: list[dict[str, Any]] = []
        total = 0.0
        pay_scale = self.config.mode_pay_scale.get(mode, 1.0)
        for symbol, pays in PAYTABLE.items():
            ways = 1
            matched_reels = 0
            positions: list[list[int]] = []
            for reel_index, reel in enumerate(board):
                matches = [
                    row_index
                    for row_index, cell in enumerate(reel)
                    if cell["name"] == symbol or (reel_index > 0 and cell["name"] == WILD)
                ]
                if not matches:
                    break
                ways *= len(matches)
                matched_reels += 1
                positions.extend([[reel_index, row] for row in matches])
            if matched_reels < 3:
                continue
            pay = pays.get(matched_reels, 0)
            if not pay:
                continue
            win = round(pay * ways * multiplier * pay_scale, 2)
            if win <= 0:
                continue
            total += win
            wins.append(
                {
                    "symbol": symbol,
                    "kind": matched_reels,
                    "ways": ways,
                    "win": win,
                    "positions": positions,
                    "meta": {"multiplier": multiplier, "basePay": pay, "payScale": pay_scale},
                }
            )
        return round(total, 2), wins

    def cap_wins(self, wins: list[dict[str, Any]], win: float, remaining: float) -> tuple[float, list[dict[str, Any]], bool]:
        if win <= remaining:
            return win, wins, False
        if remaining <= 0:
            return 0.0, [], True
        scale = remaining / win
        capped_wins = copy.deepcopy(wins)
        distributed = 0.0
        for index, win_data in enumerate(capped_wins):
            if index == len(capped_wins) - 1:
                adjusted = round(remaining - distributed, 2)
            else:
                adjusted = round(win_data["win"] * scale, 2)
                distributed += adjusted
            win_data["win"] = max(0.0, adjusted)
            win_data["meta"]["capped"] = True
        return round(remaining, 2), capped_wins, True

    def tumble_wins_for_cascade(
        self,
        board: Board,
        wins: list[dict[str, Any]],
        mode: str,
        reel_positions: list[int],
        sticky_wild_reels: set[int] | None = None,
    ) -> tuple[Board, list[int], list[list[int]]]:
        sticky_wild_reels = sticky_wild_reels or set()
        removed_positions = sorted({tuple(pos) for win in wins for pos in win["positions"] if pos[0] not in sticky_wild_reels})
        reels = reel_set_for_mode(mode)
        next_board: Board = []
        next_positions = reel_positions[:]
        for reel_index, reel in enumerate(board):
            if reel_index in sticky_wild_reels:
                next_board.append([self.symbol(WILD) for _ in reel])
                continue
            removed_rows = {row for r, row in removed_positions if r == reel_index}
            survivors = [cell for row, cell in enumerate(reel) if row not in removed_rows]
            incoming_count = len(reel) - len(survivors)
            if incoming_count <= 0:
                next_board.append(reel[:])
                continue
            strip = reels[reel_index]
            new_start = (next_positions[reel_index] - incoming_count) % len(strip)
            incoming: list[dict[str, str]] = []
            cursor = new_start
            while len(incoming) < incoming_count:
                next_symbol = strip[cursor % len(strip)]
                cursor += 1
                if mode == "base" and next_symbol == SCATTER:
                    continue
                incoming.append(self.symbol(next_symbol))
            next_positions[reel_index] = new_start
            next_board.append(incoming + survivors)
        return next_board, next_positions, [list(pos) for pos in removed_positions]

    def maybe_stack_wilds(
        self,
        board: Board,
        events: list[dict[str, Any]],
        multiplier: int,
        mode: str,
        sticky_wild_reels: set[int] | None = None,
    ) -> int:
        wild_reels: list[int] = []
        locked_reels = sticky_wild_reels or set()
        threshold = 1 if mode != "base" else 2
        for reel_index in range(1, 5):
            if reel_index in locked_reels:
                board[reel_index] = [self.symbol(WILD) for _ in board[reel_index]]
                continue
            wild_count = sum(1 for cell in board[reel_index] if cell["name"] == WILD)
            if wild_count >= threshold:
                board[reel_index] = [self.symbol(WILD) for _ in board[reel_index]]
                wild_reels.append(reel_index)
        if wild_reels:
            if sticky_wild_reels is not None and mode != "base":
                sticky_wild_reels.update(wild_reels)
            multiplier += len(wild_reels)
            events.append(
                {
                    "type": "wildMultiplier",
                    "multiplier": multiplier,
                    "wildReels": wild_reels,
                    "stickyWildReels": sorted(sticky_wild_reels) if sticky_wild_reels is not None else [],
                    "label": "Sticky Red Soldier Wild locked" if mode != "base" else "Red Soldier Wild expanded full reel",
                }
            )
        return multiplier

    def win_level(self, win: float) -> int:
        if win >= 100:
            return 5
        if win >= 50:
            return 4
        if win >= 20:
            return 3
        if win >= 5:
            return 2
        return 1

    def run_reveal(
        self,
        mode: str,
        events: list[dict[str, Any]],
        running_total: float,
        free_spin_index: int | None = None,
        free_spin_total: int | None = None,
        feature_multiplier: int = 1,
        sticky_wild_reels: set[int] | None = None,
    ) -> tuple[float, int, bool, int]:
        if free_spin_index is not None and free_spin_total is not None:
            events.append(
                {
                    "type": "freeSpinUpdate",
                    "current": free_spin_index,
                    "total": free_spin_total,
                    "mode": mode,
                    "multiplier": feature_multiplier,
                }
            )

        board, reel_positions = self.draw_board(mode)
        if sticky_wild_reels:
            for reel_index in sticky_wild_reels:
                board[reel_index] = [self.symbol(WILD) for _ in board[reel_index]]
        trigger_scatter_count = self.count_symbol(board, SCATTER)
        events.append(
            {
                "type": "reveal",
                "board": copy.deepcopy(board),
                "paddingPositions": reel_positions[:],
                "gameType": mode,
                "anticipation": self.anticipation(board),
                "stickyWildReels": sorted(sticky_wild_reels) if sticky_wild_reels else [],
            }
        )

        multiplier = self.maybe_stack_wilds(board, events, feature_multiplier, mode, sticky_wild_reels)
        reveal_total = 0.0
        capped = False

        for step in range(self.config.max_cascades):
            win, wins = self.evaluate_ways(board, multiplier, mode)
            if not wins or win <= 0:
                break
            remaining = round(self.config.wincap - running_total - reveal_total, 2)
            paid_win, paid_wins, capped = self.cap_wins(wins, win, remaining)
            if paid_win <= 0:
                capped = True
                break

            reveal_total = round(reveal_total + paid_win, 2)
            events.append({"type": "winInfo", "totalWin": round(running_total + reveal_total, 2), "wins": paid_wins})
            events.append({"type": "setWin", "amount": paid_win, "winLevel": self.win_level(paid_win)})

            if capped:
                events.append({"type": "wincap", "amount": self.config.wincap})
                break

            next_board, reel_positions, removed_positions = self.tumble_wins_for_cascade(
                board,
                paid_wins,
                mode,
                reel_positions,
                sticky_wild_reels,
            )
            multiplier += 1
            if mode != "base":
                events.append(
                    {
                        "type": "globalMultiplier",
                        "multiplier": multiplier,
                        "label": f"Warpath multiplier x{multiplier}",
                    }
                )
            events.append(
                {
                    "type": "cascade",
                    "step": step + 1,
                    "multiplier": multiplier,
                    "board": copy.deepcopy(next_board),
                    "removedPositions": removed_positions,
                }
            )
            board = next_board
            events.append({"type": "escalationUpdate", "level": escalation_level(step, step + 1)})

        return reveal_total, trigger_scatter_count, capped, multiplier

    def spins_for_trigger(self, scatter_count: int) -> int:
        eligible = [count for count in self.config.free_spin_triggers if count <= scatter_count]
        if not eligible:
            return 0
        return self.config.free_spin_triggers[max(eligible)]

    def criteria_for_result(self, total: float, base_win: float, free_win: float, bonus_triggered: bool, capped: bool) -> str:
        if capped or total >= self.config.wincap:
            return "wincap"
        if bonus_triggered or free_win > 0:
            return "freegame"
        if base_win > 0:
            return "basegame"
        return "0"

    def feature_intro_event(self, spins: int, trigger_count: int, source: str, mode: str) -> dict[str, Any]:
        return {
            "type": "warpathSpinsIntro",
            "spins": spins,
            "triggerCount": trigger_count,
            "source": source,
            "mode": mode,
            "multiplierStart": self.config.feature_start_multipliers.get(mode, 2),
            "theme": "warpath_red",
            "purchaseCost": self.config.betmode_cost(mode) if source == "buy" else 0,
        }

    def run_feature(
        self,
        events: list[dict[str, Any]],
        mode: str,
        spins: int,
        running_total: float,
    ) -> tuple[float, int, bool]:
        free_win = 0.0
        multiplier = self.config.feature_start_multipliers.get(mode, 2)
        sticky_wild_reels: set[int] = set()
        capped = False
        events.append({"type": "globalMultiplier", "multiplier": multiplier, "label": f"Warpath starts x{multiplier}"})
        for spin_index in range(1, spins + 1):
            events.append(
                {
                    "type": "awaitSpinInput",
                    "current": spin_index,
                    "total": spins,
                    "mode": mode,
                    "multiplier": multiplier,
                    "label": f"Click spin for Warpath Spin {spin_index}/{spins}",
                }
            )
            spin_win, _, capped, multiplier = self.run_reveal(
                mode,
                events,
                running_total + free_win,
                free_spin_index=spin_index,
                free_spin_total=spins,
                feature_multiplier=multiplier,
                sticky_wild_reels=sticky_wild_reels,
            )
            free_win = round(free_win + spin_win, 2)
            if capped:
                break
        return free_win, multiplier, capped

    def build_spin(self, sim_id: int, mode: str = "base", force: str | None = None) -> dict[str, Any]:
        del force
        self.reset_seed(sim_id, mode)
        events: list[dict[str, Any]] = []
        base_win = 0.0
        free_win = 0.0
        total = 0.0
        bonus_triggered = False

        if mode in self.config.buy_feature_spins:
            spins = self.config.buy_feature_spins[mode]
            bonus_triggered = True
            trigger_scatters = self.append_buy_trigger_reveal(events, spins, mode)
            events.append(self.feature_intro_event(spins=spins, trigger_count=trigger_scatters, source="buy", mode=mode))
            free_win, _, capped = self.run_feature(events, mode, spins, total)
            total = round(total + free_win, 2)
        else:
            base_win, trigger_scatters, capped, _ = self.run_reveal("base", events, total)
            total = round(total + base_win, 2)
            spins = self.spins_for_trigger(trigger_scatters)
            bonus_triggered = spins > 0
            if bonus_triggered and not capped:
                events.append(self.feature_intro_event(spins=spins, trigger_count=trigger_scatters, source="trigger", mode="warpath_spins"))
                free_win, _, capped = self.run_feature(events, "warpath_spins", spins, total)
                total = round(total + free_win, 2)

        total = min(round(total, 2), float(self.config.wincap))
        capped = total >= self.config.wincap
        events.append({"type": "setTotalWin", "amount": total})
        events.append({"type": "finalWin", "amount": total})
        for index, event in enumerate(events):
            event["index"] = index

        return {
            "id": sim_id,
            "payoutMultiplier": total,
            "events": events,
            "criteria": self.criteria_for_result(total, base_win, free_win, bonus_triggered, capped),
            "baseGameWins": round(base_win, 2),
            "freeGameWins": round(free_win, 2),
        }
