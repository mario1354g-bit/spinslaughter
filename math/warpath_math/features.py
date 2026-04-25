from __future__ import annotations


def escalation_level(spin_index: int, cascades: int) -> int:
    score = spin_index + cascades * 2
    if score >= 14:
        return 5
    if score >= 10:
        return 4
    if score >= 6:
        return 3
    if score >= 3:
        return 2
    return 1

