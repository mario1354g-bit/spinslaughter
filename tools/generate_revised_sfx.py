from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIO_DIR = ROOT / "frontend" / "static" / "assets" / "audio"
SAMPLE_RATE = 44_100
TWO_PI = math.pi * 2


def clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def sine(freq: float, t: float) -> float:
    return math.sin(TWO_PI * freq * t)


def decay(t: float, rate: float) -> float:
    return math.exp(-max(0.0, t) * rate)


def noise(rng: random.Random) -> float:
    return rng.random() * 2 - 1


def write_wav(path: Path, duration: float, fn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(hash(path.name) & 0xFFFF)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for index in range(int(duration * SAMPLE_RATE)):
            t = index / SAMPLE_RATE
            left, right = fn(t, rng)
            left = math.tanh(left * 1.15)
            right = math.tanh(right * 1.15)
            frames.extend(struct.pack("<hh", int(clamp(left) * 32767), int(clamp(right) * 32767)))
        handle.writeframes(bytes(frames))


def metal_hit(t: float, rng: random.Random, weight = 1.0) -> tuple[float, float]:
    transient = noise(rng) * decay(t, 70) * 0.34 * weight if t < 0.08 else 0.0
    body = (sine(72, t) * 0.5 + sine(144, t) * 0.14) * decay(t, 8) * weight
    ring = (sine(620, t) * 0.08 + sine(970, t) * 0.04) * decay(t, 18) * weight
    return transient + body + ring, transient * 0.8 + body * 0.82 + ring * 1.05


def ui_click(t: float, rng: random.Random) -> tuple[float, float]:
    local_noise = noise(rng) * decay(t, 95) * 0.2 if t < 0.055 else 0.0
    body = (sine(130, t) * 0.16 + sine(260, t) * 0.05) * decay(t, 42)
    return local_noise + body, local_noise * 0.78 + body * 0.88


def spin_start(t: float, rng: random.Random) -> tuple[float, float]:
    hit_l, hit_r = metal_hit(t, rng, 0.75)
    latch_l, latch_r = metal_hit(t - 0.085, rng, 0.38) if t >= 0.085 else (0.0, 0.0)
    air = noise(rng) * decay(t - 0.1, 4.2) * 0.11 if 0.1 <= t < 0.58 else 0.0
    return hit_l + latch_l + air, hit_r + latch_r - air * 0.55


def cascade(t: float, rng: random.Random, level: int) -> tuple[float, float]:
    impact_l, impact_r = metal_hit(t, rng, 0.72 + level * 0.13)
    rubble = noise(rng) * decay(t - 0.06, 9 - level) * (0.16 + level * 0.03) if 0.06 <= t < 0.44 else 0.0
    low = sine(45 + level * 8, t) * decay(t, 5.2) * (0.18 + level * 0.05)
    return impact_l + rubble + low, impact_r - rubble * 0.5 + low * 0.9


def wild_lock(t: float, rng: random.Random) -> tuple[float, float]:
    hit_l, hit_r = metal_hit(t, rng, 1.05)
    servo = (sine(95, t) * 0.22 + sine(190, t) * 0.09) * min(1, t / 0.08) * decay(t - 0.18, 1.8)
    crackle = noise(rng) * decay(t - 0.12, 7) * 0.08 if 0.12 <= t < 0.75 else 0.0
    return hit_l + servo + crackle, hit_r + servo * 0.86 - crackle * 0.7


def multiplier_rise(t: float, rng: random.Random) -> tuple[float, float]:
    # Tonal but not arcade: bowed metal swell plus low pressure.
    sweep = (sine(180 + t * 210, t) * 0.08 + sine(360 + t * 290, t) * 0.05) * min(1, t / 0.15) * decay(t - 0.55, 2.8)
    pressure = sine(70, t) * decay(t, 2.4) * 0.12
    dust = noise(rng) * decay(t, 4.5) * 0.045
    return sweep + pressure + dust, sweep * 1.05 + pressure * 0.85 - dust * 0.6


def feature_intro(t: float, rng: random.Random) -> tuple[float, float]:
    boom_l, boom_r = metal_hit(t, rng, 1.15)
    drum = 0.0
    for start in [0.28, 0.52, 0.76, 1.0, 1.18]:
        local = t - start
        if 0 <= local < 0.18:
            drum += sine(58, local) * decay(local, 10) * 0.38
    brass = (sine(110, t) + sine(165, t) * 0.6 + sine(220, t) * 0.35) * min(1, t / 0.4) * decay(t - 1.65, 1.2) * 0.16
    air = noise(rng) * 0.055 * min(1, t / 0.2) * decay(t - 0.8, 1.5) if t < 2.2 else 0.0
    return boom_l + drum + brass + air, boom_r + drum * 0.9 + brass * 0.86 - air * 0.5


def win_chime(t: float, rng: random.Random, tier: int) -> tuple[float, float]:
    notes_by_tier = {
        1: [220, 277, 330],
        2: [196, 247, 294, 392],
        3: [165, 220, 277, 330, 440],
        4: [130, 196, 247, 330, 494, 660],
    }
    notes = notes_by_tier[tier]
    value_l = 0.0
    value_r = 0.0
    for i, freq in enumerate(notes):
        start = i * (0.075 if tier < 3 else 0.105)
        local = t - start
        if local >= 0:
            env = decay(local, 4.5 - tier * 0.35)
            tone = (sine(freq, local) * 0.13 + sine(freq * 2.01, local) * 0.045) * env
            value_l += tone
            value_r += tone * (0.82 + (i % 2) * 0.28)
    if tier >= 3:
        sub = sine(62 if tier == 3 else 49, t) * decay(t, 2.2) * 0.14
        value_l += sub
        value_r += sub * 0.88
    if tier == 4 and t < 0.6:
        burst = noise(rng) * decay(t, 7) * 0.08
        value_l += burst
        value_r -= burst * 0.45
    return value_l, value_r


def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    write_wav(AUDIO_DIR / "ui_click.wav", 0.14, ui_click)
    write_wav(AUDIO_DIR / "spin_start.wav", 0.62, spin_start)
    write_wav(AUDIO_DIR / "cascade_1.wav", 0.5, lambda t, rng: cascade(t, rng, 1))
    write_wav(AUDIO_DIR / "cascade_2.wav", 0.55, lambda t, rng: cascade(t, rng, 2))
    write_wav(AUDIO_DIR / "cascade_3.wav", 0.62, lambda t, rng: cascade(t, rng, 3))
    write_wav(AUDIO_DIR / "wild_lock.wav", 0.92, wild_lock)
    write_wav(AUDIO_DIR / "multiplier_rise.wav", 0.82, multiplier_rise)
    write_wav(AUDIO_DIR / "feature_intro.wav", 2.25, feature_intro)
    write_wav(AUDIO_DIR / "win_small.wav", 0.75, lambda t, rng: win_chime(t, rng, 1))
    write_wav(AUDIO_DIR / "win_big.wav", 1.15, lambda t, rng: win_chime(t, rng, 2))
    write_wav(AUDIO_DIR / "win_mega.wav", 1.8, lambda t, rng: win_chime(t, rng, 3))
    write_wav(AUDIO_DIR / "win_legendary.wav", 2.8, lambda t, rng: win_chime(t, rng, 4))


if __name__ == "__main__":
    main()
