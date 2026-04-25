from __future__ import annotations

import json
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


def saw(freq: float, t: float) -> float:
    phase = (freq * t) % 1.0
    return phase * 2.0 - 1.0


def square(freq: float, t: float) -> float:
    return 1.0 if sine(freq, t) >= 0 else -1.0


def env_decay(t: float, decay: float) -> float:
    return math.exp(-t * decay)


def soft_clip(value: float) -> float:
    return math.tanh(value * 1.35)


def write_wav(path: Path, samples: list[tuple[float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for left, right in samples:
            frames.extend(struct.pack("<hh", int(clamp(left) * 32767), int(clamp(right) * 32767)))
        handle.writeframes(bytes(frames))


def render(duration: float, fn) -> list[tuple[float, float]]:
    total = int(duration * SAMPLE_RATE)
    samples: list[tuple[float, float]] = []
    for index in range(total):
        t = index / SAMPLE_RATE
        left, right = fn(t)
        samples.append((soft_clip(left), soft_clip(right)))
    return samples


def hit(t: float, beat: float, length: float = 0.18) -> float:
    local = t - beat
    if local < 0 or local > length:
        return 0.0
    return env_decay(local, 18.0) * (sine(62, local) * 0.9 + sine(124, local) * 0.2)


def snare(t: float, beat: float, rng: random.Random, length: float = 0.12) -> float:
    local = t - beat
    if local < 0 or local > length:
        return 0.0
    return (rng.random() * 2 - 1) * env_decay(local, 24.0)


def brass_note(freq: float, t: float, start: float, length: float) -> float:
    local = t - start
    if local < 0 or local > length:
        return 0.0
    attack = min(1.0, local / 0.06)
    release = min(1.0, (length - local) / 0.18)
    env = max(0.0, min(attack, release))
    return env * (saw(freq, local) * 0.45 + square(freq / 2, local) * 0.18 + sine(freq * 2, local) * 0.12)


def string_note(freq: float, t: float, start: float, length: float) -> float:
    local = t - start
    if local < 0 or local > length:
        return 0.0
    attack = min(1.0, local / 0.35)
    release = min(1.0, (length - local) / 0.45)
    env = max(0.0, min(attack, release))
    wobble = sine(5.2, local) * 0.006
    return env * (sine(freq * (1 + wobble), local) * 0.46 + sine(freq * 2.01, local) * 0.16)


def render_loop(name: str, duration: float, bonus: bool = False) -> None:
    rng = random.Random(91 if bonus else 37)
    bpm = 126 if bonus else 108
    beat = 60 / bpm
    root = 55 if bonus else 49
    chord_roots = [root, root, root * 1.1892, root * 1.3348]

    def sample(t: float) -> tuple[float, float]:
        bar = int(t / (beat * 4))
        beat_in_loop = t % (beat * 16)
        chord = chord_roots[bar % len(chord_roots)]
        value = 0.0
        right = 0.0

        value += string_note(chord, t, bar * beat * 4, beat * 4) * 0.2
        value += string_note(chord * 1.5, t, bar * beat * 4 + beat * 0.5, beat * 3.4) * 0.12
        value += brass_note(chord * 2, t, bar * beat * 4 + beat * 2, beat * 1.4) * (0.22 if bonus else 0.16)

        for b in [0, 1.5, 2, 3.5]:
            value += hit(beat_in_loop, b * beat) * (0.42 if bonus else 0.32)
        for b in [1, 3]:
            n = snare(beat_in_loop, b * beat, rng) * (0.22 if bonus else 0.16)
            value += n
            right += n * 0.35
        if bonus:
            for b in [0.5, 2.5]:
                value += hit(beat_in_loop, b * beat, 0.11) * 0.18

        pulse = sine(chord / 2, t) * 0.1 + saw(chord / 4, t) * 0.05
        shimmer = sine(880 + 17 * sine(0.5, t), t) * 0.016
        left = value + pulse + shimmer
        right += value * 0.88 + pulse * 0.75 - shimmer
        return left, right

    write_wav(AUDIO_DIR / name, render(duration, sample))


def render_sfx(name: str, duration: float, fn) -> None:
    write_wav(AUDIO_DIR / name, render(duration, fn))


def main() -> None:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    render_loop("base_loop.wav", 16.0, bonus=False)
    render_loop("bonus_loop.wav", 16.0, bonus=True)

    render_sfx("ui_click.wav", 0.18, lambda t: (sine(320, t) * env_decay(t, 32) * 0.22, sine(420, t) * env_decay(t, 34) * 0.18))
    render_sfx("spin_start.wav", 0.72, lambda t: ((saw(84 + 360 * t, t) + sine(52, t)) * env_decay(max(0, t - 0.08), 2.6) * 0.22, saw(92 + 350 * t, t) * env_decay(max(0, t - 0.08), 2.5) * 0.19))
    for index, freq in enumerate([180, 240, 310], start=1):
        render_sfx(
            f"cascade_{index}.wav",
            0.55,
            lambda t, f=freq: (
                (sine(f, t) + saw(f * 0.5, t)) * env_decay(t, 6) * 0.24,
                (sine(f * 1.2, t) + saw(f * 0.55, t)) * env_decay(t, 6) * 0.2,
            ),
        )
    render_sfx("wild_lock.wav", 0.95, lambda t: ((saw(65, t) + sine(130, t) + sine(520, t) * 0.3) * env_decay(t, 1.8) * 0.34, (saw(65, t) + sine(196, t)) * env_decay(t, 1.7) * 0.29))
    render_sfx("multiplier_rise.wav", 0.85, lambda t: (sine(220 + t * 660, t) * env_decay(max(0, t - 0.2), 1.6) * 0.28, sine(330 + t * 880, t) * env_decay(max(0, t - 0.2), 1.8) * 0.22))
    render_sfx("feature_intro.wav", 2.4, lambda t: ((saw(55, t) + sine(110, t) + sine(220 + 80 * t, t)) * min(1, t / 0.3) * env_decay(max(0, t - 1.5), 1.0) * 0.3, (saw(82.5, t) + sine(165, t)) * min(1, t / 0.3) * env_decay(max(0, t - 1.5), 1.0) * 0.26))
    render_sfx(
        "win_small.wav",
        0.8,
        lambda t: (
            sum(sine(f, t - i * 0.08) * env_decay(max(0, t - i * 0.08), 9) * (1 if t >= i * 0.08 else 0) for i, f in enumerate([294, 370, 440])) * 0.16,
            sum(sine(f * 1.01, t - i * 0.08) * env_decay(max(0, t - i * 0.08), 9) * (1 if t >= i * 0.08 else 0) for i, f in enumerate([294, 370, 440])) * 0.15,
        ),
    )
    render_sfx("win_big.wav", 1.4, lambda t: (sum(sine(f, t - i * 0.1) * env_decay(max(0, t - i * 0.1), 5.5) * (1 if t >= i * 0.1 else 0) for i, f in enumerate([220, 277, 330, 440, 554])) * 0.16, sum(sine(f * 1.01, t - i * 0.1) * env_decay(max(0, t - i * 0.1), 5.5) * (1 if t >= i * 0.1 else 0) for i, f in enumerate([220, 277, 330, 440, 554])) * 0.14))
    render_sfx("win_mega.wav", 2.1, lambda t: ((saw(82.5, t) * 0.35 + sum(sine(f, t - i * 0.12) * env_decay(max(0, t - i * 0.12), 4) * (1 if t >= i * 0.12 else 0) for i, f in enumerate([196, 247, 294, 392, 494, 587])) * 0.14), (saw(98, t) * 0.28 + sum(sine(f * 1.005, t - i * 0.12) * env_decay(max(0, t - i * 0.12), 4) * (1 if t >= i * 0.12 else 0) for i, f in enumerate([196, 247, 294, 392, 494, 587])) * 0.13)))
    render_sfx("win_legendary.wav", 3.2, lambda t: ((saw(55, t) + sine(110, t) + sum(sine(f, t - i * 0.16) * env_decay(max(0, t - i * 0.16), 3.2) * (1 if t >= i * 0.16 else 0) for i, f in enumerate([220, 277, 330, 440, 554, 660, 880]))) * 0.16, (saw(82.5, t) + sine(165, t) + sum(sine(f * 1.003, t - i * 0.16) * env_decay(max(0, t - i * 0.16), 3.2) * (1 if t >= i * 0.16 else 0) for i, f in enumerate([220, 277, 330, 440, 554, 660, 880]))) * 0.14))

    manifest = {
        "version": 1,
        "format": "wav",
        "music": {
            "base": {"src": "/assets/audio/base_loop.wav", "loop": True, "volume": 0.42},
            "bonus": {"src": "/assets/audio/bonus_loop.wav", "loop": True, "volume": 0.5},
        },
        "sfx": {
            "uiClick": {"src": "/assets/audio/ui_click.wav", "volume": 0.42},
            "spinStart": {"src": "/assets/audio/spin_start.wav", "volume": 0.68},
            "cascade1": {"src": "/assets/audio/cascade_1.wav", "volume": 0.55},
            "cascade2": {"src": "/assets/audio/cascade_2.wav", "volume": 0.6},
            "cascade3": {"src": "/assets/audio/cascade_3.wav", "volume": 0.64},
            "wildLock": {"src": "/assets/audio/wild_lock.wav", "volume": 0.76},
            "multiplierRise": {"src": "/assets/audio/multiplier_rise.wav", "volume": 0.62},
            "featureIntro": {"src": "/assets/audio/feature_intro.wav", "volume": 0.82},
            "winSmall": {"src": "/assets/audio/win_small.wav", "volume": 0.54},
            "winBig": {"src": "/assets/audio/win_big.wav", "volume": 0.66},
            "winMega": {"src": "/assets/audio/win_mega.wav", "volume": 0.72},
            "winLegendary": {"src": "/assets/audio/win_legendary.wav", "volume": 0.82},
        },
        "provenance": {
            "currentAssets": "Deterministic local synthesized placeholders for integration.",
            "targetModel": "ACE-Step, Apache-2.0, offline generation for final mastered score.",
        },
    }
    (AUDIO_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
