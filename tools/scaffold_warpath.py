from __future__ import annotations

import csv
import json
import math
import random
import shutil
from pathlib import Path
from textwrap import dedent

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path.cwd()
ASSET_ROOT = ROOT / "frontend" / "static" / "assets"
BOOK_ROOT = ROOT / "math" / "library" / "books"
LOOKUP_ROOT = ROOT / "math" / "library" / "lookup_tables"
FRONTEND_BOOK_ROOT = ROOT / "frontend" / "static" / "books"


def write(path: str | Path, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dedent(text).lstrip(), encoding="utf-8")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def draw_center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, size: int, fill: tuple[int, int, int, int], bold: bool = True) -> None:
    fnt = font(size, bold=bold)
    bbox = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=8, align="center")
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = box[0] + (box[2] - box[0] - width) / 2
    y = box[1] + (box[3] - box[1] - height) / 2
    draw.multiline_text((x, y), text, font=fnt, fill=fill, spacing=8, align="center", stroke_width=2, stroke_fill=(0, 0, 0, 210))


def add_texture(img: Image.Image, seed: int, blood: bool = False) -> Image.Image:
    rnd = random.Random(seed)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for _ in range(360):
        x = rnd.randrange(img.width)
        y = rnd.randrange(img.height)
        a = rnd.randrange(12, 42)
        tone = rnd.randrange(0, 255)
        d.point((x, y), fill=(tone, tone, tone, a))
    for _ in range(32):
        x = rnd.randrange(-40, img.width)
        y = rnd.randrange(-40, img.height)
        w = rnd.randrange(40, 180)
        h = rnd.randrange(2, 10)
        color = (255, 220, 170, rnd.randrange(10, 35))
        d.rectangle((x, y, x + w, y + h), fill=color)
    if blood:
        for _ in range(20):
            x = rnd.randrange(0, img.width)
            y = rnd.randrange(0, img.height)
            radius = rnd.randrange(3, 20)
            d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(120, 0, 0, rnd.randrange(70, 155)))
            if rnd.random() < 0.45:
                d.line((x, y, x + rnd.randrange(-25, 25), y + rnd.randrange(35, 120)), fill=(95, 0, 0, 105), width=rnd.randrange(2, 5))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def make_symbol(path: Path, label: str, subtitle: str, base: tuple[int, int, int], accent: tuple[int, int, int], size: tuple[int, int] = (260, 260), premium: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size
    d.rounded_rectangle((8, 8, w - 8, h - 8), radius=24, fill=(*base, 235), outline=(88, 72, 62, 230), width=5)
    d.rounded_rectangle((20, 20, w - 20, h - 20), radius=16, outline=(*accent, 180), width=3)
    for i in range(0, w, 18):
        d.line((i, 0, i - w // 3, h), fill=(255, 255, 255, 10), width=2)
    if premium:
        d.ellipse((w * 0.15, h * 0.08, w * 0.85, h * 0.78), fill=(126, 12, 34, 95), outline=(220, 44, 70, 180), width=4)
    draw_center_text(d, (18, 26, w - 18, h - 68), label, 56 if len(label) < 4 else 34, (230, 226, 214, 255), True)
    draw_center_text(d, (24, h - 76, w - 24, h - 18), subtitle, 18, (178, 166, 148, 235), True)
    img = add_texture(img, abs(hash(path.name)) % 10000, blood=premium)
    img.save(path)


def make_card(path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 252, 252), radius=22, fill=(34, 34, 32, 238), outline=(96, 82, 72, 220), width=5)
    d.rectangle((28, 28, 232, 232), outline=(120, 20, 20, 90), width=3)
    draw_center_text(d, (0, 0, 260, 260), label, 104 if len(label) == 1 else 88, (150, 145, 135, 255), True)
    for x in range(24, 236, 34):
        d.line((x, 34, x + 12, 226), fill=(255, 255, 255, 13), width=2)
    add_texture(img, abs(hash(label)) % 10000).save(path)


def make_background() -> None:
    out = ASSET_ROOT / "backgrounds"
    out.mkdir(parents=True, exist_ok=True)
    src = ROOT / "warpath reels.jpg"
    if src.exists():
        img = Image.open(src).convert("RGB").resize((1920, 1080), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(1.2))
        img = Image.blend(img, Image.new("RGB", img.size, (20, 17, 16)), 0.58)
    else:
        img = Image.new("RGB", (1920, 1080), (26, 23, 22))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(1080):
        a = int(130 * y / 1080)
        d.line((0, y, 1920, y), fill=(0, 0, 0, a))
    d.rectangle((0, 0, 1920, 1080), fill=(42, 12, 10, 34))
    for _ in range(120):
        x = random.randrange(0, 1920)
        y = random.randrange(220, 980)
        d.ellipse((x, y, x + random.randrange(1, 4), y + random.randrange(1, 4)), fill=(210, 90, 28, random.randrange(20, 75)))
    img.convert("RGBA").save(out / "background_desert_futuristic_night.png")

    far = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    fd = ImageDraw.Draw(far)
    for _ in range(420):
        y = random.randrange(80, 980)
        x = random.randrange(0, 1920)
        fd.line((x, y, x + random.randrange(80, 260), y + random.randrange(-8, 8)), fill=(178, 145, 110, random.randrange(10, 36)), width=random.randrange(1, 3))
    far.save(out / "sandstorm_far.png")

    near = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    nd = ImageDraw.Draw(near)
    for _ in range(260):
        y = random.randrange(120, 1040)
        x = random.randrange(0, 1920)
        nd.line((x, y, x + random.randrange(160, 420), y + random.randrange(-18, 18)), fill=(205, 165, 118, random.randrange(14, 48)), width=random.randrange(2, 5))
    near.save(out / "sandstorm_near.png")

    overlay = Image.new("RGBA", (1920, 1080), (116, 0, 0, 78))
    od = ImageDraw.Draw(overlay)
    for _ in range(42):
        x = random.randrange(0, 1920)
        y = random.randrange(0, 1080)
        r = random.randrange(30, 180)
        od.ellipse((x - r, y - r, x + r, y + r), fill=(170, 0, 0, random.randrange(18, 46)))
    overlay.save(out / "total_war_red_overlay.png")


def make_particles() -> None:
    pdir = ASSET_ROOT / "particles"
    pdir.mkdir(parents=True, exist_ok=True)
    specs = {
        "ember_particle.png": ((255, 104, 24, 230), (80, 15, 0, 0)),
        "smoke_puff.png": ((150, 150, 145, 92), (0, 0, 0, 0)),
        "blood_drop.png": ((132, 0, 0, 230), (60, 0, 0, 0)),
        "sand_grain.png": ((205, 160, 112, 190), (0, 0, 0, 0)),
        "spark.png": ((255, 226, 90, 245), (0, 0, 0, 0)),
        "missile_smoke.png": ((195, 195, 185, 120), (0, 0, 0, 0)),
        "debris_chunk.png": ((92, 78, 66, 230), (0, 0, 0, 0)),
        "nuke_glow_ring.png": ((120, 210, 255, 96), (0, 0, 0, 0)),
        "flare_ring.png": ((255, 84, 18, 120), (0, 0, 0, 0)),
    }
    for name, (fill, edge) in specs.items():
        img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if "ring" in name:
            d.ellipse((8, 8, 88, 88), outline=fill, width=8)
            d.ellipse((22, 22, 74, 74), outline=(*fill[:3], max(40, fill[3] // 2)), width=4)
        elif "spark" in name:
            d.polygon([(48, 2), (58, 36), (94, 48), (58, 58), (48, 94), (38, 58), (2, 48), (38, 36)], fill=fill)
        elif "debris" in name:
            d.polygon([(18, 14), (78, 26), (68, 76), (30, 86), (10, 48)], fill=fill)
        else:
            d.ellipse((12, 12, 84, 84), fill=fill, outline=edge, width=2)
            img = img.filter(ImageFilter.GaussianBlur(2 if "smoke" in name else 0.6))
        img.save(pdir / name)


def make_effect_sheets() -> None:
    adir = ASSET_ROOT / "animations"
    adir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (1024, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for i in range(4):
        x = i * 256
        d.rounded_rectangle((x + 24, 32, x + 232, 224), radius=26, outline=(190, 52, 30, 130 + i * 25), width=6)
        d.line((x + 36, 128, x + 220, 128), fill=(255, 122, 36, 160), width=8 + i * 3)
        d.ellipse((x + 104 - i * 10, 104 - i * 10, x + 152 + i * 10, 152 + i * 10), outline=(255, 214, 94, 150), width=5)
    sheet.save(adir / "cascade_animation_frames.png")
    sheet.save(ASSET_ROOT / "cascade_animation_frames.png")

    blackbird = Image.new("RGBA", (1536, 256), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blackbird)
    for i in range(6):
        x = i * 256
        bd.polygon([(x + 28, 126), (x + 162, 78), (x + 232, 128), (x + 162, 178)], fill=(18, 20, 23, 240), outline=(120, 120, 120, 180))
        bd.line((x + 70, 168, x + 20, 218), fill=(210, 210, 205, 90), width=16)
        bd.line((x + 190, 150, x + 238, 210), fill=(255, 104, 20, 190), width=7)
    blackbird.save(adir / "blackbird_missile_launch_sequence.png")
    blackbird.save(ASSET_ROOT / "blackbird_missile_launch_sequence.png")

    make_symbol(adir / "multiplier_stamp.png", "X+", "MULTIPLIER", (56, 16, 14), (220, 40, 30), (260, 260))
    make_symbol(adir / "wild_pulse_sheet.png", "NUKE", "PULSE", (15, 36, 46), (80, 210, 255), (260, 260))
    make_symbol(adir / "symbol_shatter_sheet.png", "BOOM", "SHATTER", (42, 34, 30), (255, 130, 34), (260, 260))
    make_symbol(adir / "reel_spin_blur.png", "///", "SPIN BLUR", (42, 42, 42), (165, 32, 24), (260, 260))


def make_ui() -> None:
    udir = ASSET_ROOT / "ui"
    udir.mkdir(parents=True, exist_ok=True)
    items = {
        "logo_warpath_reels.png": ("WARPATH\nREELS", (60, 18, 16), (220, 44, 40), (720, 220)),
        "warpath_title.png": ("WARPATH\nSPINS", (55, 22, 18), (210, 48, 40), (540, 180)),
        "totalwar_title.png": ("TOTAL WAR\nSPINS", (80, 0, 0), (255, 40, 32), (540, 180)),
        "spin_button_idle.png": ("SPIN", (54, 36, 20), (255, 116, 36), (260, 132)),
        "spin_button_pressed.png": ("SPIN", (34, 20, 12), (255, 74, 22), (260, 132)),
        "spin_button_disabled.png": ("LOCKED", (28, 28, 28), (88, 88, 88), (260, 132)),
        "buy_button_warpath.png": ("BUY\nWARPATH", (42, 22, 18), (210, 72, 42), (320, 120)),
        "buy_button_totalwar.png": ("BUY\nTOTAL WAR", (76, 0, 0), (255, 45, 32), (340, 120)),
        "bet_panel_bg.png": ("", (18, 17, 16), (90, 70, 56), (960, 150)),
        "paytable_bg.png": ("PAYTABLE", (20, 18, 16), (120, 96, 75), (900, 680)),
        "fs_counter_bg.png": ("SPINS", (34, 20, 16), (210, 52, 38), (260, 120)),
        "win_banner_big.png": ("BIG WIN", (55, 28, 14), (255, 120, 34), (640, 180)),
        "win_banner_mega.png": ("MEGA WIN", (66, 8, 8), (255, 58, 36), (680, 190)),
        "win_banner_epic.png": ("EPIC WIN", (72, 0, 0), (255, 30, 24), (700, 200)),
        "win_banner_legendary.png": ("LEGENDARY", (82, 0, 0), (255, 230, 190), (760, 220)),
        "settings_icon.png": ("SET", (30, 30, 30), (160, 150, 130), (96, 96)),
        "info_icon.png": ("i", (30, 30, 30), (160, 150, 130), (96, 96)),
        "autoplay_icon.png": ("AUTO", (30, 30, 30), (160, 150, 130), (112, 96)),
        "sound_on_icon.png": ("ON", (30, 30, 30), (160, 150, 130), (96, 96)),
        "sound_off_icon.png": ("OFF", (30, 30, 30), (160, 150, 130), (96, 96)),
        "coin_particle.png": ("$", (45, 34, 20), (220, 160, 60), (80, 80)),
    }
    for name, (label, base, accent, size) in items.items():
        make_symbol(udir / name, label, "", base, accent, size)


def make_symbols() -> None:
    sdir = ASSET_ROOT / "symbols"
    sdir.mkdir(parents=True, exist_ok=True)
    for label, name in [("10", "symbol_low_10.png"), ("J", "symbol_low_j.png"), ("Q", "symbol_low_q.png"), ("K", "symbol_low_k.png")]:
        make_card(sdir / name, label)

    high_specs = [
        ("symbol_high_lady_soldier.png", "LATINA\nSOLDIER", "PREMIUM", (50, 13, 22), (220, 34, 72), True),
        ("symbol_high_taliban_old.png", "OLD\nFIGHTER", "HIGH PAY", (38, 37, 34), (105, 80, 70), False),
        ("symbol_high_iraqi_young.png", "YOUNG\nFIGHTER", "HIGH PAY", (44, 42, 38), (112, 92, 76), False),
        ("symbol_high_iraqi_soldier.png", "IRAQI\nSOLDIER", "HIGH PAY", (42, 42, 40), (118, 94, 82), False),
        ("symbol_high_woman_soldier.png", "FIELD\nWOMAN", "HIGH PAY", (46, 43, 42), (128, 84, 84), False),
    ]
    for filename, label, subtitle, base, accent, premium in high_specs:
        src_lady = ROOT / "symbol_high_lady_soldier.png"
        if filename == "symbol_high_lady_soldier.png" and src_lady.exists():
            img = Image.open(src_lady).convert("RGBA").resize((260, 260), Image.Resampling.LANCZOS)
            add_texture(img, 781, blood=True).save(sdir / filename)
        else:
            make_symbol(sdir / filename, label, subtitle, base, accent, premium=premium)
        tall_name = filename.replace(".png", "_tall.png")
        if filename == "symbol_high_lady_soldier.png" and src_lady.exists():
            tall = Image.open(src_lady).convert("RGBA").resize((260, 800), Image.Resampling.LANCZOS)
            add_texture(tall, 782, blood=True).save(sdir / tall_name)
        else:
            make_symbol(sdir / tall_name, label, "3-REEL TAKEOVER", base, accent, (260, 800), premium=premium)

    make_symbol(sdir / "wild_stealth_nuke.png", "STEALTH\nNUKE", "WILD", (12, 30, 40), (82, 210, 255), premium=False)
    make_symbol(sdir / "wild_stealth_nuke_3high.png", "STEALTH\nNUKE", "STACKED WILD", (10, 28, 38), (82, 210, 255), (260, 800), premium=False)
    make_symbol(sdir / "scatter_warpath_flare.png", "WARPATH\nFLARE", "SCATTER", (52, 22, 8), (255, 95, 20), premium=False)
    make_symbol(sdir / "scatter_warpath_flare_3high.png", "WARPATH\nFLARE", "3 HIGH", (52, 22, 8), (255, 95, 20), (260, 800), premium=False)
    make_symbol(sdir / "reel6_sr71_blackbird_2high.png", "SR-71", "BLACKBIRD STRIKE", (12, 13, 14), (126, 126, 126), (260, 530), premium=False)
    make_symbol(sdir / "reel6_sr71_blackbird_3high.png", "SR-71", "3 HIGH", (12, 13, 14), (126, 126, 126), (260, 800), premium=False)
    make_symbol(sdir / "reel6_sr71_blackbird_full.png", "SR-71\nBLACKBIRD", "FULL TAKEOVER", (8, 9, 10), (150, 150, 150), (820, 800), premium=False)


def python_math_files() -> None:
    write("math/README.md", """
        # Warpath Reels Math

        Lightweight Python math package following the StakeEngine Math SDK output conventions:
        `game_config.py`, `gamestate.py`, generated `books_*.jsonl`, lookup tables, and index files.

        This build intentionally does not claim final RTP. The generator creates deterministic development
        books for frontend testing and future math iteration.

        ```bash
        cd math
        python3 generate_books.py
        ```
    """)
    write("math/requirements.txt", """
        # No third-party runtime dependencies are required for book generation.
    """)
    write("math/warpath_math/__init__.py", """
        from .game_config import GameConfig
        from .gamestate import GameState

        __all__ = ["GameConfig", "GameState"]
    """)
    write("math/warpath_math/symbols.py", """
        LOW_SYMBOLS = ["T", "J", "Q", "K"]
        HIGH_SYMBOLS = ["LS", "TO", "IY", "IS", "WS"]
        WILD = "WD"
        SCATTER = "SC"
        SR71 = "SR"

        SYMBOL_NAMES = {
            "T": "10",
            "J": "Jack",
            "Q": "Queen",
            "K": "King",
            "LS": "Latina Lady Soldier",
            "TO": "Old Desert Fighter",
            "IY": "Young Iraqi Fighter",
            "IS": "Iraqi Soldier",
            "WS": "Field Woman Soldier",
            "WD": "Stealth Nuke Wild",
            "SC": "Warpath Flare Scatter",
            "SR": "SR-71 Blackbird Strike",
        }

        ASSET_BY_SYMBOL = {
            "T": "symbols/symbol_low_10.png",
            "J": "symbols/symbol_low_j.png",
            "Q": "symbols/symbol_low_q.png",
            "K": "symbols/symbol_low_k.png",
            "LS": "symbols/symbol_high_lady_soldier.png",
            "TO": "symbols/symbol_high_taliban_old.png",
            "IY": "symbols/symbol_high_iraqi_young.png",
            "IS": "symbols/symbol_high_iraqi_soldier.png",
            "WS": "symbols/symbol_high_woman_soldier.png",
            "WD": "symbols/wild_stealth_nuke.png",
            "SC": "symbols/scatter_warpath_flare.png",
            "SR": "symbols/reel6_sr71_blackbird_2high.png",
        }
    """)
    write("math/warpath_math/paytable.py", """
        PAYTABLE = {
            "LS": {3: 5.0, 4: 20.0, 5: 75.0, 6: 500.0},
            "TO": {3: 3.0, 4: 10.0, 5: 40.0, 6: 150.0},
            "IY": {3: 2.0, 4: 7.5, 5: 25.0, 6: 75.0},
            "IS": {3: 1.5, 4: 5.0, 5: 15.0, 6: 50.0},
            "WS": {3: 1.0, 4: 3.0, 5: 10.0, 6: 30.0},
            "K": {3: 0.5, 4: 1.5, 5: 5.0, 6: 10.0},
            "Q": {3: 0.4, 4: 1.0, 5: 3.0, 6: 6.0},
            "J": {3: 0.3, 4: 0.8, 5: 2.0, 6: 4.0},
            "T": {3: 0.2, 4: 0.6, 5: 1.5, 6: 3.0},
        }
    """)
    write("math/warpath_math/reels.py", """
        from .symbols import HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, SR71, WILD

        ROWS_PER_REEL = [2, 3, 3, 3, 3, 2]

        BASE_REELS = [
            ["T", "J", "Q", "K", "WS", "T", "SC", "J", "IS", "Q", "K", "WD", "T", "IY", "J", "Q", "TO", "K", "T", "WS"],
            ["J", "Q", "K", "T", "IS", "J", "Q", "WD", "K", "WS", "T", "SC", "J", "IY", "Q", "TO", "K", "T", "J", "LS"],
            ["Q", "K", "T", "J", "IY", "Q", "SC", "K", "WD", "IS", "T", "J", "TO", "Q", "K", "WS", "T", "J", "LS", "Q"],
            ["K", "T", "J", "Q", "TO", "K", "T", "WD", "J", "IS", "Q", "K", "SC", "T", "WS", "J", "IY", "Q", "K", "LS"],
            ["T", "J", "Q", "K", "LS", "T", "IY", "J", "WD", "Q", "TO", "K", "SC", "T", "IS", "J", "WS", "Q", "K", "T"],
            ["LS", "SR", "TO", "IY", "IS", "WS", "SR", "LS", "TO", "IY", "IS", "SR", "WS", "LS"],
        ]

        WARPATH_REELS = [
            reel + [WILD, SCATTER, "LS"] if idx < 5 else reel
            for idx, reel in enumerate(BASE_REELS)
        ]

        TOTAL_WAR_REELS = [
            reel + [WILD, WILD, SCATTER, "LS", "TO"] if idx < 5 else reel + ["SR", "LS"]
            for idx, reel in enumerate(BASE_REELS)
        ]

        def reel_set_for_mode(mode: str):
            if mode == "total_war_spins":
                return TOTAL_WAR_REELS
            if mode == "warpath_spins":
                return WARPATH_REELS
            return BASE_REELS

        def reel6_symbols_only_high_or_blackbird() -> bool:
            return all(symbol in HIGH_SYMBOLS + [SR71] for symbol in BASE_REELS[5])
    """)
    write("math/warpath_math/game_config.py", """
        from dataclasses import dataclass, field

        from .paytable import PAYTABLE
        from .reels import ROWS_PER_REEL
        from .symbols import HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, SR71, WILD


        @dataclass(frozen=True)
        class BetMode:
            name: str
            cost: float
            description: str
            is_buybonus: bool = False


        @dataclass(frozen=True)
        class GameConfig:
            game_id: str = "warpath_reels"
            provider_number: int = 0
            working_name: str = "Warpath Reels"
            win_type: str = "ways"
            wincap: int = 500000
            num_reels: int = 6
            num_rows: tuple[int, ...] = tuple(ROWS_PER_REEL)
            total_ways: int = 324
            low_symbols: tuple[str, ...] = tuple(LOW_SYMBOLS)
            high_symbols: tuple[str, ...] = tuple(HIGH_SYMBOLS)
            wild_symbol: str = WILD
            scatter_symbol: str = SCATTER
            reel6_special_symbol: str = SR71
            paytable: dict = field(default_factory=lambda: PAYTABLE)
            free_spin_triggers: dict = field(default_factory=lambda: {3: 10, 4: 12, 5: 15, 6: 20})
            total_war_triggers: dict = field(default_factory=lambda: {5: 12, 6: 20})
            escalation_levels: tuple[int, ...] = (1, 2, 3, 4, 5)
            bet_modes: tuple[BetMode, ...] = (
                BetMode("base", 1.0, "Base game"),
                BetMode("warpath_spins", 100.0, "Warpath Spins bonus buy", True),
                BetMode("total_war_spins", 300.0, "Total War Spins bonus buy", True),
                BetMode("blackbird_strike", 50.0, "Blackbird Strike Sequence demo", True),
                BetMode("boosters", 75.0, "Booster feature demo", True),
            )

            def validate(self) -> None:
                assert self.num_reels == len(self.num_rows)
                assert self.num_rows == (2, 3, 3, 3, 3, 2)
                assert self.total_ways == 2 * 3 * 3 * 3 * 3 * 2
    """)
    write("math/warpath_math/features.py", """
        from __future__ import annotations

        import random


        BOOSTERS = [
            "precision_strike",
            "super_precision_strike",
            "cascade_booster",
            "cascade_blackbird_booster",
            "overkill",
        ]


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


        def choose_booster(rng: random.Random, force: str | None = None) -> str | None:
            if force:
                return force
            roll = rng.random()
            if roll < 0.04:
                return "overkill"
            if roll < 0.10:
                return "cascade_blackbird_booster"
            if roll < 0.18:
                return "cascade_booster"
            if roll < 0.28:
                return "super_precision_strike"
            if roll < 0.42:
                return "precision_strike"
            return None
    """)
    write("math/warpath_math/gamestate.py", """
        from __future__ import annotations

        import random
        from dataclasses import dataclass, field
        from typing import Any

        from .features import choose_booster, escalation_level
        from .game_config import GameConfig
        from .paytable import PAYTABLE
        from .reels import ROWS_PER_REEL, reel_set_for_mode
        from .symbols import HIGH_SYMBOLS, LOW_SYMBOLS, SCATTER, SR71, WILD


        Board = list[list[dict[str, str]]]


        @dataclass
        class GameState:
            config: GameConfig = field(default_factory=GameConfig)
            rng: random.Random = field(default_factory=random.Random)

            def symbol(self, name: str) -> dict[str, str]:
                return {"name": name}

            def draw_board(self, mode: str) -> Board:
                reels = reel_set_for_mode(mode)
                board: Board = []
                for reel_index, rows in enumerate(ROWS_PER_REEL):
                    strip = reels[reel_index]
                    start = self.rng.randrange(len(strip))
                    board.append([self.symbol(strip[(start + row) % len(strip)]) for row in range(rows)])
                return board

            def count_scatter(self, board: Board) -> int:
                return sum(1 for reel in board for sym in reel if sym["name"] == SCATTER)

            def evaluate_ways(self, board: Board, multiplier: int = 1) -> tuple[float, list[dict[str, Any]]]:
                wins: list[dict[str, Any]] = []
                total = 0.0
                for symbol, pays in PAYTABLE.items():
                    ways = 1
                    matched_reels = 0
                    positions: list[list[int]] = []
                    for reel_index, reel in enumerate(board):
                        matches = [
                            row_index
                            for row_index, cell in enumerate(reel)
                            if cell["name"] == symbol or cell["name"] == WILD
                        ]
                        if not matches:
                            break
                        ways *= len(matches)
                        matched_reels += 1
                        positions.extend([[reel_index, row] for row in matches])
                    if matched_reels >= 3:
                        pay = pays.get(matched_reels, 0)
                        if pay:
                            win = round(pay * ways * multiplier, 2)
                            total += win
                            wins.append(
                                {
                                    "symbol": symbol,
                                    "kind": matched_reels,
                                    "ways": ways,
                                    "win": win,
                                    "positions": positions,
                                    "meta": {"multiplier": multiplier},
                                }
                            )
                return round(total, 2), wins

            def replace_wins_for_cascade(self, board: Board, wins: list[dict[str, Any]], mode: str) -> Board:
                winning_positions = {tuple(pos) for win in wins for pos in win["positions"]}
                reels = reel_set_for_mode(mode)
                next_board: Board = []
                for reel_index, reel in enumerate(board):
                    strip = reels[reel_index]
                    next_reel: list[dict[str, str]] = []
                    for row_index, cell in enumerate(reel):
                        if (reel_index, row_index) in winning_positions and cell["name"] != WILD:
                            next_reel.append(self.symbol(self.rng.choice(strip)))
                        else:
                            next_reel.append(cell)
                    next_board.append(next_reel)
                return next_board

            def maybe_stack_wilds(self, board: Board, events: list[dict[str, Any]], multiplier: int) -> int:
                wild_reels = []
                for reel_index in range(5):
                    if any(cell["name"] == WILD for cell in board[reel_index]):
                        board[reel_index] = [self.symbol(WILD) for _ in board[reel_index]]
                        wild_reels.append(reel_index)
                if wild_reels:
                    multiplier += len(wild_reels)
                    events.append(
                        {
                            "type": "wildMultiplier",
                            "multiplier": multiplier,
                            "wildReels": wild_reels,
                            "label": "Stealth Nuke Wild stacked full reel",
                        }
                    )
                return multiplier

            def maybe_reel6_special(self, board: Board, events: list[dict[str, Any]], force_blackbird: bool = False) -> None:
                reel6 = [cell["name"] for cell in board[5]]
                if force_blackbird or SR71 in reel6:
                    targets = [[self.rng.randrange(0, 5), self.rng.randrange(0, 3)] for _ in range(6)]
                    events.append(
                        {
                            "type": "blackbirdStrike",
                            "missiles": targets,
                            "label": "Blackbird Strike Sequence",
                        }
                    )
                elif any(symbol in HIGH_SYMBOLS for symbol in reel6) and self.rng.random() < 0.22:
                    symbol = self.rng.choice([s for s in reel6 if s in HIGH_SYMBOLS])
                    for reel_index in [3, 4, 5]:
                        board[reel_index] = [self.symbol(WILD) for _ in board[reel_index]]
                    events.append(
                        {
                            "type": "characterTakeover",
                            "symbol": symbol,
                            "targetReels": [3, 4, 5],
                            "label": "Reel 6 character takeover converts three reels to wilds",
                        }
                    )

            def add_booster_event(self, board: Board, events: list[dict[str, Any]], force: str | None = None) -> None:
                booster = choose_booster(self.rng, force)
                if not booster:
                    return
                target_reels = [self.rng.randrange(0, 5)]
                if booster in {"cascade_booster", "cascade_blackbird_booster", "overkill"}:
                    start = self.rng.randrange(0, 4)
                    target_reels = [start, start + 1, min(start + 2, 4)]
                    for reel in target_reels:
                        board[reel] = [self.symbol(WILD) for _ in board[reel]]
                events.append({"type": "booster", "booster": booster, "targetReels": target_reels})
                if booster in {"cascade_blackbird_booster", "overkill"}:
                    self.maybe_reel6_special(board, events, force_blackbird=True)

            def build_spin(self, sim_id: int, mode: str = "base", force: str | None = None) -> dict[str, Any]:
                self.rng.seed(sim_id * 7919 + hash(mode) % 1000)
                board = self.draw_board(mode)
                events: list[dict[str, Any]] = [
                    {
                        "index": 0,
                        "type": "reveal",
                        "board": board,
                        "paddingPositions": [self.rng.randrange(0, 99) for _ in range(6)],
                        "gameType": mode,
                        "anticipation": [0, 0, 0, 0, 0, int(any(c["name"] == SR71 for c in board[5]))],
                    }
                ]
                multiplier = 1
                total = 0.0
                multiplier = self.maybe_stack_wilds(board, events, multiplier)
                self.maybe_reel6_special(board, events, force_blackbird=(force == "blackbird"))
                self.add_booster_event(board, events, force=force if force and force != "blackbird" else None)

                cascades = 0
                for step in range(4):
                    win, wins = self.evaluate_ways(board, multiplier)
                    if not wins:
                        break
                    total += win
                    events.append({"type": "winInfo", "totalWin": round(total, 2), "wins": wins})
                    events.append({"type": "setWin", "amount": win, "winLevel": min(5, max(1, int(win // 10) + 1))})
                    next_board = self.replace_wins_for_cascade(board, wins, mode)
                    cascades += 1
                    multiplier += 1
                    events.append(
                        {
                            "type": "cascade",
                            "step": cascades,
                            "multiplier": multiplier,
                            "board": next_board,
                            "removedPositions": [pos for win_data in wins for pos in win_data["positions"]],
                        }
                    )
                    board = next_board
                    events.append({"type": "escalationUpdate", "level": escalation_level(step, cascades)})

                scatter_count = self.count_scatter(board)
                if mode == "base" and scatter_count >= 3:
                    spins = self.config.free_spin_triggers.get(scatter_count, 10)
                    bonus_mode = "total_war_spins" if scatter_count >= 5 else "warpath_spins"
                    events.append(
                        {
                            "type": "totalWarSpinsIntro" if bonus_mode == "total_war_spins" else "warpathSpinsIntro",
                            "spins": spins,
                            "scatterCount": scatter_count,
                        }
                    )
                if mode in {"warpath_spins", "total_war_spins"}:
                    events.insert(1, {"type": "freeSpinUpdate", "current": sim_id % 10 + 1, "total": 10, "mode": mode})
                    if mode == "total_war_spins":
                        events.insert(1, {"type": "totalWarTint", "active": True})

                events.append({"type": "setTotalWin", "amount": round(total, 2)})
                events.append({"type": "finalWin", "amount": round(total, 2)})
                for index, event in enumerate(events):
                    event["index"] = index
                return {
                    "id": sim_id,
                    "payoutMultiplier": round(total, 2),
                    "events": events,
                    "criteria": mode if total else "0",
                    "baseGameWins": round(total, 2) if mode == "base" else 0.0,
                    "freeGameWins": round(total, 2) if mode != "base" else 0.0,
                }
    """)
    write("math/generate_books.py", """
        from __future__ import annotations

        import csv
        import json
        import shutil
        from pathlib import Path

        from warpath_math.gamestate import GameState
        from warpath_math.game_config import GameConfig


        ROOT = Path(__file__).resolve().parent
        BOOK_DIR = ROOT / "library" / "books"
        LOOKUP_DIR = ROOT / "library" / "lookup_tables"
        PUBLISH_DIR = ROOT / "library" / "publish_files"
        FRONTEND_BOOK_DIR = ROOT.parent / "frontend" / "static" / "books"


        MODES = {
            "base": (90, None),
            "warpath_spins": (36, None),
            "total_war_spins": (28, None),
            "blackbird_strike": (12, "blackbird"),
            "boosters": (20, "overkill"),
        }


        def write_mode(mode: str, count: int, force: str | None) -> None:
            state = GameState()
            books_path = BOOK_DIR / f"books_{mode}.jsonl"
            lookup_path = LOOKUP_DIR / f"lookUpTable_{mode}.csv"
            criteria_path = LOOKUP_DIR / f"lookUpTableIdToCriteria_{mode}.csv"
            books_path.parent.mkdir(parents=True, exist_ok=True)
            lookup_path.parent.mkdir(parents=True, exist_ok=True)
            with books_path.open("w", encoding="utf-8") as books_file, lookup_path.open("w", newline="", encoding="utf-8") as lookup_file, criteria_path.open("w", newline="", encoding="utf-8") as criteria_file:
                lookup_writer = csv.writer(lookup_file)
                criteria_writer = csv.writer(criteria_file)
                lookup_writer.writerow(["id", "weight", "payoutMultiplier"])
                criteria_writer.writerow(["id", "criteria"])
                for sim_id in range(1, count + 1):
                    book = state.build_spin(sim_id, mode=mode if mode != "blackbird_strike" and mode != "boosters" else "base", force=force)
                    books_file.write(json.dumps(book, separators=(",", ":")) + "\\n")
                    lookup_writer.writerow([book["id"], 1, book["payoutMultiplier"]])
                    criteria_writer.writerow([book["id"], book["criteria"]])


        def main() -> None:
            GameConfig().validate()
            for directory in [BOOK_DIR, LOOKUP_DIR, PUBLISH_DIR, FRONTEND_BOOK_DIR]:
                directory.mkdir(parents=True, exist_ok=True)
            for mode, (count, force) in MODES.items():
                write_mode(mode, count, force)
            index = {
                "gameId": GameConfig().game_id,
                "workingName": GameConfig().working_name,
                "modes": list(MODES.keys()),
                "bookFormat": "jsonl",
                "note": "Development books generated for frontend animation and RGS integration testing; RTP not finalized.",
            }
            (PUBLISH_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
            (BOOK_DIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
            for path in BOOK_DIR.glob("books_*.jsonl"):
                shutil.copy2(path, FRONTEND_BOOK_DIR / path.name)
            shutil.copy2(BOOK_DIR / "index.json", FRONTEND_BOOK_DIR / "index.json")
            print(f"Generated {len(MODES)} book sets in {BOOK_DIR}")


        if __name__ == "__main__":
            main()
    """)
    write("math/run.py", """
        from generate_books import main

        if __name__ == "__main__":
            main()
    """)
    write("math/optimizer.py", """
        from __future__ import annotations

        from pathlib import Path


        def summarize_lookup_tables(root: Path = Path("library/lookup_tables")) -> dict[str, int]:
            summary: dict[str, int] = {}
            for path in root.glob("lookUpTable_*.csv"):
                with path.open("r", encoding="utf-8") as fh:
                    summary[path.stem] = max(0, sum(1 for _ in fh) - 1)
            return summary


        if __name__ == "__main__":
            print(summarize_lookup_tables())
    """)


def frontend_files() -> None:
    write("package.json", """
        {
          "name": "warpath-reels",
          "version": "1.0.0",
          "private": true,
          "type": "module",
          "scripts": {
            "dev": "pnpm --dir frontend dev",
            "build": "pnpm --dir frontend build",
            "preview": "pnpm --dir frontend preview",
            "generate:books": "python3 math/generate_books.py",
            "math": "python3 math/run.py"
          },
          "packageManager": "pnpm@10.33.0"
        }
    """)
    write("pnpm-workspace.yaml", """
        packages:
          - frontend
    """)
    write(".gitignore", """
        node_modules/
        .svelte-kit/
        build/
        dist/
        .DS_Store
        __pycache__/
        *.pyc
        .venv/
        .env
        .env.*
        !.env.example
        .claude-flow/
    """)
    write("frontend/package.json", """
        {
          "name": "warpath-reels-frontend",
          "version": "1.0.0",
          "private": true,
          "type": "module",
          "scripts": {
            "dev": "vite dev",
            "build": "vite build",
            "preview": "vite preview"
          },
          "dependencies": {
            "@pixi/sound": "^6.0.0",
            "@sveltejs/adapter-static": "^3.0.8",
            "@sveltejs/kit": "^2.27.0",
            "@sveltejs/vite-plugin-svelte": "^6.2.1",
            "pixi.js": "^8.14.3",
            "svelte": "^5.40.0",
            "vite": "^7.1.9"
          },
          "devDependencies": {
            "@types/node": "^24.7.2",
            "typescript": "^5.9.3"
          }
        }
    """)
    write("frontend/svelte.config.js", """
        import adapter from '@sveltejs/adapter-static';
        import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

        const config = {
          preprocess: vitePreprocess(),
          kit: {
            adapter: adapter({
              pages: 'build',
              assets: 'build',
              fallback: 'index.html'
            })
          }
        };

        export default config;
    """)
    write("frontend/vite.config.ts", """
        import { sveltekit } from '@sveltejs/kit/vite';
        import { defineConfig } from 'vite';

        export default defineConfig({
          plugins: [sveltekit()],
          server: {
            host: '0.0.0.0',
            port: 5173
          }
        });
    """)
    write("frontend/tsconfig.json", """
        {
          "extends": "./.svelte-kit/tsconfig.json",
          "compilerOptions": {
            "allowJs": true,
            "checkJs": true,
            "esModuleInterop": true,
            "forceConsistentCasingInFileNames": true,
            "resolveJsonModule": true,
            "skipLibCheck": true,
            "sourceMap": true,
            "strict": true,
            "moduleResolution": "bundler"
          }
        }
    """)
    write("frontend/src/app.html", """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <link rel="icon" href="/assets/ui/logo_warpath_reels.png" />
            %sveltekit.head%
          </head>
          <body data-sveltekit-preload-data="hover">
            <div style="display: contents">%sveltekit.body%</div>
          </body>
        </html>
    """)
    write("frontend/src/app.css", """
        :root {
          color-scheme: dark;
          font-family: "Rajdhani", "Oswald", "Arial Narrow", sans-serif;
          background: #050403;
          color: #eee6dc;
        }

        html,
        body {
          width: 100%;
          height: 100%;
          margin: 0;
          overflow: hidden;
          background: #050403;
        }

        button {
          font: inherit;
        }
    """)
    write("frontend/src/routes/+layout.ts", """
        import '../app.css';
    """)
    write("frontend/src/routes/+page.svelte", """
        <script lang="ts">
          import WarpathGame from '$lib/components/WarpathGame.svelte';
        </script>

        <svelte:head>
          <title>Warpath Reels</title>
          <meta name="description" content="Warpath Reels StakeEngine-style Svelte + PixiJS slot game." />
        </svelte:head>

        <WarpathGame />
    """)
    write("frontend/src/lib/game/constants.ts", """
        export const CANVAS_WIDTH = 1920;
        export const CANVAS_HEIGHT = 1080;
        export const ROWS_PER_REEL = [2, 3, 3, 3, 3, 2] as const;
        export const REEL_COUNT = ROWS_PER_REEL.length;
        export const SYMBOL_SIZE = 196;
        export const SYMBOL_GAP = 10;
        export const REEL_AREA_WIDTH = REEL_COUNT * SYMBOL_SIZE + (REEL_COUNT - 1) * SYMBOL_GAP;
        export const MAX_REEL_ROWS = 3;
        export const REEL_AREA_HEIGHT = MAX_REEL_ROWS * SYMBOL_SIZE + (MAX_REEL_ROWS - 1) * SYMBOL_GAP;
        export const REEL_AREA_X = (CANVAS_WIDTH - REEL_AREA_WIDTH) / 2;
        export const REEL_AREA_Y = 238;
        export const TOTAL_WAYS = 324;
        export const ASSET_PATH = '/assets';
        export const BOOK_PATH = '/books';
        export const BET_LEVELS = [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100];
    """)
    write("frontend/src/lib/game/symbols.ts", """
        import { ASSET_PATH } from './constants';

        export type SymbolTier = 'low' | 'high' | 'premium' | 'wild' | 'scatter' | 'special';

        export interface SymbolConfig {
          id: string;
          label: string;
          name: string;
          tier: SymbolTier;
          asset: string;
          tallAsset?: string;
        }

        export const SYMBOLS: Record<string, SymbolConfig> = {
          T: { id: 'T', label: '10', name: 'Ten', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_10.png` },
          J: { id: 'J', label: 'J', name: 'Jack', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_j.png` },
          Q: { id: 'Q', label: 'Q', name: 'Queen', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_q.png` },
          K: { id: 'K', label: 'K', name: 'King', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_k.png` },
          LS: { id: 'LS', label: 'LS', name: 'Latina Lady Soldier', tier: 'premium', asset: `${ASSET_PATH}/symbols/symbol_high_lady_soldier.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_lady_soldier_tall.png` },
          TO: { id: 'TO', label: 'TO', name: 'Old Desert Fighter', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_taliban_old.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_taliban_old_tall.png` },
          IY: { id: 'IY', label: 'IY', name: 'Young Iraqi Fighter', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_iraqi_young.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_iraqi_young_tall.png` },
          IS: { id: 'IS', label: 'IS', name: 'Iraqi Soldier', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_iraqi_soldier.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_iraqi_soldier_tall.png` },
          WS: { id: 'WS', label: 'WS', name: 'Field Woman Soldier', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_woman_soldier.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_woman_soldier_tall.png` },
          WD: { id: 'WD', label: 'W', name: 'Stealth Nuke Wild', tier: 'wild', asset: `${ASSET_PATH}/symbols/wild_stealth_nuke.png`, tallAsset: `${ASSET_PATH}/symbols/wild_stealth_nuke_3high.png` },
          SC: { id: 'SC', label: 'S', name: 'Warpath Flare', tier: 'scatter', asset: `${ASSET_PATH}/symbols/scatter_warpath_flare.png`, tallAsset: `${ASSET_PATH}/symbols/scatter_warpath_flare_3high.png` },
          SR: { id: 'SR', label: 'SR', name: 'SR-71 Blackbird Strike', tier: 'special', asset: `${ASSET_PATH}/symbols/reel6_sr71_blackbird_2high.png`, tallAsset: `${ASSET_PATH}/symbols/reel6_sr71_blackbird_full.png` }
        };

        export const SPIN_POOL = Object.keys(SYMBOLS);
        export const REEL6_POOL = ['LS', 'TO', 'IY', 'IS', 'WS', 'SR'];
    """)
    write("frontend/src/lib/game/types.ts", """
        export type SymbolCell = { name: string };
        export type Board = SymbolCell[][];

        export interface WinLine {
          symbol: string;
          kind: number;
          ways: number;
          win: number;
          positions: [number, number][];
          meta: Record<string, unknown>;
        }

        export type BookEvent =
          | { index: number; type: 'reveal'; board: Board; paddingPositions: number[]; gameType: string; anticipation: number[] }
          | { index: number; type: 'freeSpinUpdate'; current: number; total: number; mode: string }
          | { index: number; type: 'totalWarTint'; active: boolean }
          | { index: number; type: 'winInfo'; totalWin: number; wins: WinLine[] }
          | { index: number; type: 'setWin'; amount: number; winLevel: number }
          | { index: number; type: 'setTotalWin'; amount: number }
          | { index: number; type: 'finalWin'; amount: number }
          | { index: number; type: 'cascade'; step: number; multiplier: number; board: Board; removedPositions: [number, number][] }
          | { index: number; type: 'wildMultiplier'; multiplier: number; wildReels: number[]; label: string }
          | { index: number; type: 'escalationUpdate'; level: number }
          | { index: number; type: 'blackbirdStrike'; missiles: [number, number][]; label: string }
          | { index: number; type: 'characterTakeover'; symbol: string; targetReels: number[]; label: string }
          | { index: number; type: 'booster'; booster: string; targetReels: number[] }
          | { index: number; type: 'warpathSpinsIntro'; spins: number; scatterCount: number }
          | { index: number; type: 'totalWarSpinsIntro'; spins: number; scatterCount: number };

        export interface Book {
          id: number;
          payoutMultiplier: number;
          events: BookEvent[];
          criteria: string;
          baseGameWins: number;
          freeGameWins: number;
        }

        export type EmitterEvent =
          | { type: 'reelsSpin'; board: Board; anticipation: number[]; mode: string }
          | { type: 'winHighlight'; wins: WinLine[]; totalWin: number }
          | { type: 'winCounter'; amount: number; level: number }
          | { type: 'totalWinUpdate'; amount: number }
          | { type: 'finalWin'; amount: number }
          | { type: 'cascadeExplode'; positions: [number, number][]; board: Board; multiplier: number; step: number }
          | { type: 'wildPulse'; multiplier: number; wildReels: number[] }
          | { type: 'escalationUpdate'; level: number }
          | { type: 'blackbirdStrike'; missiles: [number, number][] }
          | { type: 'characterTakeover'; symbol: string; targetReels: number[] }
          | { type: 'boosterIntro'; booster: string; targetReels: number[] }
          | { type: 'featureIntro'; mode: 'warpath' | 'totalWar'; spins: number; scatterCount: number }
          | { type: 'freeSpinUpdate'; current: number; total: number; mode: string }
          | { type: 'totalWarTint'; active: boolean }
          | { type: 'toast'; message: string; tone?: 'red' | 'amber' | 'blue' };
    """)
    write("frontend/src/lib/game/eventEmitter.ts", """
        import type { EmitterEvent } from './types';

        type Handler<T extends EmitterEvent = EmitterEvent> = (event: T) => void | Promise<void>;
        type HandlerMap = Partial<{ [K in EmitterEvent['type']]: Handler<Extract<EmitterEvent, { type: K }>> }>;

        class WarpathEventEmitter {
          private handlers = new Map<string, Set<Handler>>();

          broadcast<T extends EmitterEvent>(event: T): void {
            const handlers = this.handlers.get(event.type);
            if (!handlers) return;
            for (const handler of handlers) {
              void handler(event);
            }
          }

          async broadcastAsync<T extends EmitterEvent>(event: T): Promise<void> {
            const handlers = this.handlers.get(event.type);
            if (!handlers) return;
            await Promise.all(Array.from(handlers).map((handler) => handler(event)));
          }

          subscribeOnMount(map: HandlerMap): () => void {
            const entries = Object.entries(map) as [string, Handler][];
            for (const [type, handler] of entries) {
              if (!this.handlers.has(type)) this.handlers.set(type, new Set());
              this.handlers.get(type)!.add(handler);
            }
            return () => {
              for (const [type, handler] of entries) {
                this.handlers.get(type)?.delete(handler);
              }
            };
          }
        }

        export const eventEmitter = new WarpathEventEmitter();
    """)
    write("frontend/src/lib/game/bookEventHandlers.ts", """
        import { eventEmitter } from './eventEmitter';
        import type { BookEvent } from './types';

        export type BookEventContext = { bookEvents: BookEvent[] };
        type Handler<T extends BookEvent = BookEvent> = (event: T, context: BookEventContext) => Promise<void> | void;
        type HandlerMap = { [K in BookEvent['type']]: Handler<Extract<BookEvent, { type: K }>> };

        export const bookEventHandlerMap: HandlerMap = {
          reveal: async (event) => {
            await eventEmitter.broadcastAsync({
              type: 'reelsSpin',
              board: event.board,
              anticipation: event.anticipation,
              mode: event.gameType
            });
          },
          freeSpinUpdate: (event) => {
            eventEmitter.broadcast({ type: 'freeSpinUpdate', current: event.current, total: event.total, mode: event.mode });
          },
          totalWarTint: (event) => {
            eventEmitter.broadcast({ type: 'totalWarTint', active: event.active });
          },
          winInfo: async (event) => {
            await eventEmitter.broadcastAsync({ type: 'winHighlight', wins: event.wins, totalWin: event.totalWin });
          },
          setWin: (event) => {
            eventEmitter.broadcast({ type: 'winCounter', amount: event.amount, level: event.winLevel });
          },
          setTotalWin: (event) => {
            eventEmitter.broadcast({ type: 'totalWinUpdate', amount: event.amount });
          },
          finalWin: (event) => {
            eventEmitter.broadcast({ type: 'finalWin', amount: event.amount });
          },
          cascade: async (event) => {
            await eventEmitter.broadcastAsync({
              type: 'cascadeExplode',
              positions: event.removedPositions,
              board: event.board,
              multiplier: event.multiplier,
              step: event.step
            });
          },
          wildMultiplier: async (event) => {
            eventEmitter.broadcast({ type: 'toast', message: `STEALTH NUKE MULTIPLIER x${event.multiplier}`, tone: 'blue' });
            await eventEmitter.broadcastAsync({ type: 'wildPulse', multiplier: event.multiplier, wildReels: event.wildReels });
          },
          escalationUpdate: (event) => {
            eventEmitter.broadcast({ type: 'escalationUpdate', level: event.level });
          },
          blackbirdStrike: async (event) => {
            eventEmitter.broadcast({ type: 'toast', message: 'BLACKBIRD STRIKE SEQUENCE', tone: 'amber' });
            await eventEmitter.broadcastAsync({ type: 'blackbirdStrike', missiles: event.missiles });
          },
          characterTakeover: async (event) => {
            eventEmitter.broadcast({ type: 'toast', message: 'REEL 6 TAKEOVER', tone: 'red' });
            await eventEmitter.broadcastAsync({ type: 'characterTakeover', symbol: event.symbol, targetReels: event.targetReels });
          },
          booster: async (event) => {
            const label = event.booster.replaceAll('_', ' ').toUpperCase();
            eventEmitter.broadcast({ type: 'toast', message: label, tone: event.booster === 'overkill' ? 'red' : 'amber' });
            await eventEmitter.broadcastAsync({ type: 'boosterIntro', booster: event.booster, targetReels: event.targetReels });
          },
          warpathSpinsIntro: async (event) => {
            await eventEmitter.broadcastAsync({ type: 'featureIntro', mode: 'warpath', spins: event.spins, scatterCount: event.scatterCount });
          },
          totalWarSpinsIntro: async (event) => {
            await eventEmitter.broadcastAsync({ type: 'featureIntro', mode: 'totalWar', spins: event.spins, scatterCount: event.scatterCount });
          }
        };
    """)
    write("frontend/src/lib/game/bookPlayer.ts", """
        import { bookEventHandlerMap, type BookEventContext } from './bookEventHandlers';
        import type { Book, BookEvent } from './types';

        export async function playBookEvent(event: BookEvent, context: BookEventContext): Promise<void> {
          const handler = bookEventHandlerMap[event.type] as ((event: BookEvent, context: BookEventContext) => Promise<void> | void) | undefined;
          if (!handler) {
            console.warn(`[Warpath] No handler for book event ${event.type}`);
            return;
          }
          await handler(event, context);
        }

        export async function playBookEvents(book: Book): Promise<void> {
          const context = { bookEvents: book.events };
          for (const event of book.events) {
            await playBookEvent(event, context);
          }
        }
    """)
    write("frontend/src/lib/game/books.ts", """
        import { BOOK_PATH } from './constants';
        import type { Book } from './types';

        export type BookMode = 'base' | 'warpath_spins' | 'total_war_spins' | 'blackbird_strike' | 'boosters';
        const cache = new Map<BookMode, Book[]>();

        export async function loadBooks(mode: BookMode): Promise<Book[]> {
          if (cache.has(mode)) return cache.get(mode)!;
          const response = await fetch(`${BOOK_PATH}/books_${mode}.jsonl`);
          if (!response.ok) throw new Error(`Unable to load books for ${mode}`);
          const text = await response.text();
          const books = text
            .split('\\n')
            .map((line) => line.trim())
            .filter(Boolean)
            .map((line) => JSON.parse(line) as Book);
          cache.set(mode, books);
          return books;
        }

        export async function pickBook(mode: BookMode): Promise<Book> {
          const books = await loadBooks(mode);
          return books[Math.floor(Math.random() * books.length)];
        }
    """)
    write("frontend/src/lib/components/PixiStage.svelte", """
        <script lang="ts">
          import { onDestroy, onMount } from 'svelte';
          import {
            Application,
            Assets,
            BlurFilter,
            ColorMatrixFilter,
            Container,
            Graphics,
            Sprite,
            Text,
            Texture
          } from 'pixi.js';
          import {
            ASSET_PATH,
            CANVAS_HEIGHT,
            CANVAS_WIDTH,
            MAX_REEL_ROWS,
            REEL_AREA_HEIGHT,
            REEL_AREA_WIDTH,
            REEL_AREA_X,
            REEL_AREA_Y,
            REEL_COUNT,
            ROWS_PER_REEL,
            SYMBOL_GAP,
            SYMBOL_SIZE
          } from '$lib/game/constants';
          import { eventEmitter } from '$lib/game/eventEmitter';
          import { REEL6_POOL, SPIN_POOL, SYMBOLS } from '$lib/game/symbols';
          import type { Board, WinLine } from '$lib/game/types';

          let canvas: HTMLCanvasElement;
          let app: Application | undefined;
          let root = new Container();
          let bgLayer = new Container();
          let reelLayer = new Container();
          let fxLayer = new Container();
          let overlayLayer = new Container();
          let currentBoard: Board = emptyBoard();
          let symbols: Container[][] = [];
          let loaded = false;
          let unsubscribe = () => {};
          let totalWarFilter: ColorMatrixFilter | undefined;
          let sandFar: Sprite | undefined;
          let sandNear: Sprite | undefined;
          let resolveReady: (() => void) | undefined;
          const readyPromise = new Promise<void>((resolve) => {
            resolveReady = resolve;
          });

          export async function ready() {
            await readyPromise;
          }

          function emptyBoard(): Board {
            return ROWS_PER_REEL.map((rows) => Array.from({ length: rows }, () => ({ name: 'T' })));
          }

          function sleep(ms: number) {
            return new Promise((resolve) => setTimeout(resolve, ms));
          }

          function reelX(reel: number) {
            return REEL_AREA_X + reel * (SYMBOL_SIZE + SYMBOL_GAP);
          }

          function reelYOffset(reel: number) {
            const rows = ROWS_PER_REEL[reel];
            const reelHeight = rows * SYMBOL_SIZE + (rows - 1) * SYMBOL_GAP;
            return (REEL_AREA_HEIGHT - reelHeight) / 2;
          }

          function cellY(reel: number, row: number) {
            return REEL_AREA_Y + reelYOffset(reel) + row * (SYMBOL_SIZE + SYMBOL_GAP);
          }

          function textureFor(symbol: string): Texture {
            return Texture.from(SYMBOLS[symbol]?.asset ?? SYMBOLS.T.asset);
          }

          function makeSymbol(symbol: string, reel: number, row: number) {
            const container = new Container();
            container.x = reelX(reel);
            container.y = cellY(reel, row);
            const frame = new Graphics()
              .roundRect(0, 0, SYMBOL_SIZE, SYMBOL_SIZE, 18)
              .fill({ color: symbol === 'LS' ? 0x34111a : 0x161514, alpha: 0.92 })
              .stroke({ color: symbol === 'LS' ? 0xd93652 : 0x4a4139, width: 3, alpha: 0.9 });
            const sprite = new Sprite(textureFor(symbol));
            sprite.width = SYMBOL_SIZE - 16;
            sprite.height = SYMBOL_SIZE - 16;
            sprite.x = 8;
            sprite.y = 8;
            const label = new Text({
              text: SYMBOLS[symbol]?.label ?? symbol,
              style: {
                fontFamily: 'Impact, sans-serif',
                fontSize: symbol.length > 1 ? 30 : 52,
                fill: symbol === 'LS' ? 0xff556e : 0xc6b9a3,
                stroke: { color: 0x000000, width: 4 }
              }
            });
            label.anchor.set(0.5);
            label.x = SYMBOL_SIZE / 2;
            label.y = SYMBOL_SIZE - 26;
            container.addChild(frame, sprite, label);
            return container;
          }

          function renderBoard(board: Board) {
            currentBoard = board;
            reelLayer.removeChildren();
            symbols = [];
            const back = new Graphics()
              .roundRect(REEL_AREA_X - 28, REEL_AREA_Y - 28, REEL_AREA_WIDTH + 56, REEL_AREA_HEIGHT + 56, 30)
              .fill({ color: 0x070605, alpha: 0.82 })
              .stroke({ color: 0x682015, width: 4, alpha: 0.9 });
            reelLayer.addChild(back);
            for (let reel = 0; reel < REEL_COUNT; reel++) {
              const reelFrame = new Graphics()
                .roundRect(reelX(reel) - 6, REEL_AREA_Y + reelYOffset(reel) - 6, SYMBOL_SIZE + 12, ROWS_PER_REEL[reel] * SYMBOL_SIZE + (ROWS_PER_REEL[reel] - 1) * SYMBOL_GAP + 12, 18)
                .fill({ color: 0x11100f, alpha: 0.9 })
                .stroke({ color: reel === 5 ? 0x8c1c18 : 0x3d302b, width: reel === 5 ? 4 : 2, alpha: 0.9 });
              reelLayer.addChild(reelFrame);
              symbols[reel] = [];
              for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
                const container = makeSymbol(board[reel]?.[row]?.name ?? 'T', reel, row);
                symbols[reel][row] = container;
                reelLayer.addChild(container);
              }
            }
          }

          async function spinTo(board: Board, anticipation: number[], mode: string) {
            eventEmitter.broadcast({ type: 'toast', message: mode === 'base' ? 'REELS HOT' : mode.replaceAll('_', ' ').toUpperCase(), tone: mode === 'total_war_spins' ? 'red' : 'amber' });
            for (let reel = 0; reel < REEL_COUNT; reel++) {
              const rows = ROWS_PER_REEL[reel];
              const pool = reel === 5 ? REEL6_POOL : SPIN_POOL;
              const reelSymbols = symbols[reel] ?? [];
              const blur = new BlurFilter({ strength: 8 });
              for (const sym of reelSymbols) sym.filters = [blur];
              const duration = 320 + reel * 170 + (anticipation[reel] ? 700 : 0);
              const start = performance.now();
              while (performance.now() - start < duration) {
                for (let row = 0; row < rows; row++) {
                  currentBoard[reel][row] = { name: pool[Math.floor(Math.random() * pool.length)] };
                }
                renderBoard(currentBoard);
                await sleep(52);
              }
              for (let row = 0; row < rows; row++) currentBoard[reel][row] = board[reel][row];
              renderBoard(currentBoard);
              await screenShake(2 + reel, 45);
            }
            emitAmbient('smoke', 4);
          }

          function cellCenter(reel: number, row: number) {
            return { x: reelX(reel) + SYMBOL_SIZE / 2, y: cellY(reel, row) + SYMBOL_SIZE / 2 };
          }

          function particleTexture(name: string) {
            return Texture.from(`${ASSET_PATH}/particles/${name}.png`);
          }

          function emitParticle(name: string, x: number, y: number, count: number, tint?: number) {
            for (let i = 0; i < count; i++) {
              const sprite = new Sprite(particleTexture(name));
              sprite.anchor.set(0.5);
              sprite.x = x + (Math.random() - 0.5) * 30;
              sprite.y = y + (Math.random() - 0.5) * 30;
              sprite.scale.set(0.18 + Math.random() * 0.45);
              sprite.alpha = 0.8;
              if (tint) sprite.tint = tint;
              fxLayer.addChild(sprite);
              const vx = (Math.random() - 0.5) * 8;
              const vy = (Math.random() - 0.8) * 8;
              const life = 35 + Math.random() * 45;
              let age = 0;
              const ticker = () => {
                age += 1;
                sprite.x += vx;
                sprite.y += vy + age * 0.08;
                sprite.rotation += 0.08;
                sprite.alpha = Math.max(0, 1 - age / life);
                sprite.scale.x *= 0.992;
                sprite.scale.y *= 0.992;
                if (age >= life && app) {
                  app.ticker.remove(ticker);
                  sprite.destroy();
                }
              };
              app?.ticker.add(ticker);
            }
          }

          function emitAmbient(kind: 'embers' | 'smoke' | 'sand', amount: number) {
            for (let i = 0; i < amount; i++) {
              const x = Math.random() * CANVAS_WIDTH;
              const y = kind === 'embers' ? 880 + Math.random() * 160 : 520 + Math.random() * 380;
              emitParticle(kind === 'embers' ? 'ember_particle' : kind === 'sand' ? 'sand_grain' : 'smoke_puff', x, y, kind === 'sand' ? 2 : 1);
            }
          }

          async function highlightWins(wins: WinLine[], totalWin: number) {
            for (const reel of symbols) for (const sym of reel) sym.alpha = 0.28;
            const positions = wins.flatMap((win) => win.positions);
            for (const [reel, row] of positions) {
              const sym = symbols[reel]?.[row];
              if (!sym) continue;
              sym.alpha = 1;
              sym.scale.set(1.07);
              const center = cellCenter(reel, row);
              emitParticle(totalWin > 20 ? 'blood_drop' : 'spark', center.x, center.y, totalWin > 20 ? 7 : 5);
            }
            await screenShake(Math.min(20, 4 + totalWin / 10), Math.min(900, 180 + totalWin * 8));
            await sleep(620);
            for (const reel of symbols) for (const sym of reel) {
              sym.alpha = 1;
              sym.scale.set(1);
            }
          }

          async function cascadeExplode(positions: [number, number][], board: Board, multiplier: number, step: number) {
            for (const [reel, row] of positions) {
              const center = cellCenter(reel, row);
              emitParticle('debris_chunk', center.x, center.y, 5);
              emitParticle('blood_drop', center.x, center.y, 2);
            }
            await screenShake(5 + step * 2, 180);
            await sleep(220);
            renderBoard(board);
            const stamp = new Text({
              text: `CASCADE +${step}  x${multiplier}`,
              style: { fontFamily: 'Impact', fontSize: 54, fill: 0xff6330, stroke: { color: 0x000000, width: 6 } }
            });
            stamp.anchor.set(0.5);
            stamp.x = CANVAS_WIDTH / 2;
            stamp.y = REEL_AREA_Y - 70;
            overlayLayer.addChild(stamp);
            await sleep(420);
            stamp.destroy();
          }

          async function wildPulse(multiplier: number, wildReels: number[]) {
            for (const reel of wildReels) {
              for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
                const center = cellCenter(reel, row);
                emitParticle('nuke_glow_ring', center.x, center.y, 2, 0x7edcff);
              }
            }
            await screenShake(10 + multiplier, 350);
            await sleep(360);
          }

          async function blackbirdStrike(missiles: [number, number][]) {
            const plane = Sprite.from(`${ASSET_PATH}/symbols/reel6_sr71_blackbird_full.png`);
            plane.anchor.set(0.5);
            plane.width = 520;
            plane.height = 250;
            plane.x = -320;
            plane.y = 148;
            overlayLayer.addChild(plane);
            for (let frame = 0; frame < 44; frame++) {
              plane.x += 58;
              plane.y = 145 + Math.sin(frame / 4) * 14;
              emitParticle('missile_smoke', plane.x - 170, plane.y + 42, 2);
              await sleep(18);
            }
            for (const [reel, row] of missiles) {
              const center = cellCenter(reel, Math.min(row, ROWS_PER_REEL[reel] - 1));
              emitParticle('spark', center.x, center.y, 16);
              emitParticle('debris_chunk', center.x, center.y, 9);
              await screenShake(8, 90);
              await sleep(90);
            }
            plane.destroy();
          }

          async function characterTakeover(symbol: string, targetReels: number[]) {
            const config = SYMBOLS[symbol];
            const sprite = Sprite.from(config?.tallAsset ?? SYMBOLS.LS.tallAsset!);
            sprite.anchor.set(0.5);
            sprite.x = reelX(targetReels[0]) + ((SYMBOL_SIZE + SYMBOL_GAP) * targetReels.length) / 2 - SYMBOL_GAP;
            sprite.y = REEL_AREA_Y + REEL_AREA_HEIGHT / 2;
            sprite.width = SYMBOL_SIZE * targetReels.length;
            sprite.height = REEL_AREA_HEIGHT + 70;
            sprite.alpha = 0;
            overlayLayer.addChild(sprite);
            for (let i = 0; i < 18; i++) {
              sprite.alpha = i / 18;
              sprite.scale.set(1 + Math.sin(i / 18) * 0.05);
              await sleep(24);
            }
            await screenShake(14, 450);
            await sleep(500);
            sprite.destroy();
          }

          async function boosterIntro(booster: string, targetReels: number[]) {
            const label = new Text({
              text: booster.replaceAll('_', ' ').toUpperCase(),
              style: { fontFamily: 'Impact', fontSize: booster === 'overkill' ? 88 : 66, fill: booster === 'overkill' ? 0xff2920 : 0xff9338, stroke: { color: 0x000000, width: 8 } }
            });
            label.anchor.set(0.5);
            label.x = CANVAS_WIDTH / 2;
            label.y = 185;
            overlayLayer.addChild(label);
            for (const reel of targetReels) {
              const x = reelX(reel) + SYMBOL_SIZE / 2;
              emitParticle('flare_ring', x, REEL_AREA_Y + REEL_AREA_HEIGHT / 2, 4);
            }
            await screenShake(booster === 'overkill' ? 18 : 10, 420);
            await sleep(520);
            label.destroy();
          }

          async function featureIntro(mode: 'warpath' | 'totalWar', spins: number) {
            const blocker = new Graphics().rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT).fill({ color: mode === 'totalWar' ? 0x5a0000 : 0x120806, alpha: 0.82 });
            const text = new Text({
              text: `${mode === 'totalWar' ? 'TOTAL WAR SPINS' : 'WARPATH SPINS'}\\n${spins} DEPLOYED`,
              style: { fontFamily: 'Impact', fontSize: 92, align: 'center', fill: mode === 'totalWar' ? 0xff342c : 0xff7b32, stroke: { color: 0x000000, width: 10 } }
            });
            text.anchor.set(0.5);
            text.x = CANVAS_WIDTH / 2;
            text.y = CANVAS_HEIGHT / 2;
            overlayLayer.addChild(blocker, text);
            await screenShake(16, 620);
            await sleep(1100);
            blocker.destroy();
            text.destroy();
          }

          async function screenShake(intensity: number, duration: number) {
            const start = performance.now();
            while (performance.now() - start < duration) {
              root.x = (Math.random() - 0.5) * intensity;
              root.y = (Math.random() - 0.5) * intensity;
              await sleep(16);
            }
            root.x = 0;
            root.y = 0;
          }

          async function init() {
            app = new Application();
            await app.init({
              canvas,
              width: CANVAS_WIDTH,
              height: CANVAS_HEIGHT,
              backgroundColor: 0x050403,
              antialias: true,
              resolution: window.devicePixelRatio || 1,
              autoDensity: true
            });
            app.stage.addChild(root);
            root.addChild(bgLayer, reelLayer, fxLayer, overlayLayer);
            const assets = [
              `${ASSET_PATH}/backgrounds/background_desert_futuristic_night.png`,
              `${ASSET_PATH}/backgrounds/sandstorm_far.png`,
              `${ASSET_PATH}/backgrounds/sandstorm_near.png`,
              `${ASSET_PATH}/backgrounds/total_war_red_overlay.png`,
              ...Object.values(SYMBOLS).flatMap((s) => [s.asset, s.tallAsset].filter(Boolean) as string[])
            ];
            await Assets.load(assets);
            const bg = Sprite.from(`${ASSET_PATH}/backgrounds/background_desert_futuristic_night.png`);
            bg.width = CANVAS_WIDTH;
            bg.height = CANVAS_HEIGHT;
            sandFar = Sprite.from(`${ASSET_PATH}/backgrounds/sandstorm_far.png`);
            sandNear = Sprite.from(`${ASSET_PATH}/backgrounds/sandstorm_near.png`);
            bgLayer.addChild(bg, sandFar, sandNear);
            totalWarFilter = new ColorMatrixFilter();
            totalWarFilter.brightness(0.78, false);
            totalWarFilter.sepia(true);
            renderBoard(currentBoard);
            app.ticker.add(() => {
              if (sandFar) sandFar.x = ((sandFar.x - 0.22) % CANVAS_WIDTH);
              if (sandNear) sandNear.x = ((sandNear.x - 0.68) % CANVAS_WIDTH);
              if (Math.random() < 0.18) emitAmbient('embers', 1);
              if (Math.random() < 0.08) emitAmbient('sand', 1);
            });
            unsubscribe = eventEmitter.subscribeOnMount({
              reelsSpin: (event) => spinTo(event.board, event.anticipation, event.mode),
              winHighlight: (event) => highlightWins(event.wins, event.totalWin),
              cascadeExplode: (event) => cascadeExplode(event.positions, event.board, event.multiplier, event.step),
              wildPulse: (event) => wildPulse(event.multiplier, event.wildReels),
              blackbirdStrike: (event) => blackbirdStrike(event.missiles),
              characterTakeover: (event) => characterTakeover(event.symbol, event.targetReels),
              boosterIntro: (event) => boosterIntro(event.booster, event.targetReels),
              featureIntro: (event) => featureIntro(event.mode, event.spins),
              totalWarTint: (event) => {
                root.filters = event.active && totalWarFilter ? [totalWarFilter] : [];
              }
            });
            loaded = true;
            resolveReady?.();
          }

          onMount(() => {
            void init();
          });

          onDestroy(() => {
            unsubscribe();
            app?.destroy(true);
          });
        </script>

        <canvas bind:this={canvas} class:loaded aria-label="Warpath Reels PixiJS game canvas"></canvas>

        <style>
          canvas {
            width: 100%;
            height: 100%;
            display: block;
            opacity: 0;
            transition: opacity 0.3s ease;
          }

          canvas.loaded {
            opacity: 1;
          }
        </style>
    """)
    write("frontend/src/lib/components/WarpathGame.svelte", """
        <script lang="ts">
          import { onDestroy, onMount } from 'svelte';
          import PixiStage from './PixiStage.svelte';
          import { BET_LEVELS, CANVAS_HEIGHT, CANVAS_WIDTH, TOTAL_WAYS } from '$lib/game/constants';
          import { eventEmitter } from '$lib/game/eventEmitter';
          import { pickBook, type BookMode } from '$lib/game/books';
          import { playBookEvents } from '$lib/game/bookPlayer';

          let stage: PixiStage;
          let scale = 1;
          let playing = false;
          let balance = 10000;
          let betIndex = 2;
          let currentWin = 0;
          let totalWin = 0;
          let winLevel = 0;
          let escalationLevel = 1;
          let freeSpinLabel = '';
          let totalWarActive = false;
          let toast = 'READY';
          let toastTone: 'red' | 'amber' | 'blue' = 'amber';
          let lastMode: BookMode = 'base';
          let unsubscribe = () => {};

          $: bet = BET_LEVELS[betIndex];

          function resize() {
            scale = Math.min(window.innerWidth / CANVAS_WIDTH, window.innerHeight / CANVAS_HEIGHT);
          }

          function adjustBet(direction: number) {
            if (playing) return;
            betIndex = Math.max(0, Math.min(BET_LEVELS.length - 1, betIndex + direction));
          }

          async function play(mode: BookMode = 'base') {
            if (playing) return;
            playing = true;
            lastMode = mode;
            currentWin = 0;
            totalWin = 0;
            winLevel = 0;
            freeSpinLabel = '';
            totalWarActive = mode === 'total_war_spins';
            const cost = mode === 'warpath_spins' ? bet * 100 : mode === 'total_war_spins' ? bet * 300 : mode === 'blackbird_strike' ? bet * 50 : mode === 'boosters' ? bet * 75 : bet;
            balance = Math.max(0, balance - cost);
            try {
              await stage.ready();
              const book = await pickBook(mode);
              await playBookEvents(book);
              balance += book.payoutMultiplier * bet;
            } catch (error) {
              console.error(error);
              toast = 'BOOK LOAD FAILED';
              toastTone = 'red';
            } finally {
              playing = false;
            }
          }

          onMount(() => {
            resize();
            window.addEventListener('resize', resize);
            window.addEventListener('orientationchange', resize);
            const keydown = (event: KeyboardEvent) => {
              if (event.code === 'Space') {
                event.preventDefault();
                void play('base');
              }
            };
            window.addEventListener('keydown', keydown);
            unsubscribe = eventEmitter.subscribeOnMount({
              winCounter: (event) => {
                currentWin = event.amount * bet;
                winLevel = event.level;
              },
              totalWinUpdate: (event) => {
                totalWin = event.amount * bet;
              },
              finalWin: (event) => {
                totalWin = event.amount * bet;
                if (event.amount > 0) {
                  toast = `PAID ${totalWin.toFixed(2)}`;
                  toastTone = event.amount > 75 ? 'red' : 'amber';
                }
              },
              escalationUpdate: (event) => {
                escalationLevel = event.level;
              },
              freeSpinUpdate: (event) => {
                freeSpinLabel = `${event.current}/${event.total} ${event.mode === 'total_war_spins' ? 'TOTAL WAR' : 'WARPATH'} SPINS`;
                totalWarActive = event.mode === 'total_war_spins';
              },
              totalWarTint: (event) => {
                totalWarActive = event.active;
              },
              featureIntro: (event) => {
                toast = `${event.mode === 'totalWar' ? 'TOTAL WAR' : 'WARPATH'} SPINS x${event.spins}`;
                toastTone = event.mode === 'totalWar' ? 'red' : 'amber';
              },
              toast: (event) => {
                toast = event.message;
                toastTone = event.tone ?? 'amber';
              }
            });
            return () => {
              window.removeEventListener('resize', resize);
              window.removeEventListener('orientationchange', resize);
              window.removeEventListener('keydown', keydown);
            };
          });

          onDestroy(() => {
            unsubscribe();
          });
        </script>

        <div class="viewport">
          <div class="game-shell" style:transform={`scale(${scale})`}>
            <PixiStage bind:this={stage} />

            <div class="grain"></div>
            <header class="title-block">
              <div class="eyebrow">OPERATION ESCALATION</div>
              <h1>WARPATH REELS</h1>
              <div class="ways">{TOTAL_WAYS} WAYS · 6 REELS · 2-3-3-3-3-2</div>
            </header>

            <section class="meter" class:total-war={totalWarActive}>
              <span>WARPATH ESCALATION</span>
              <div class="pips">
                {#each [1, 2, 3, 4, 5] as level}
                  <b class:active={level <= escalationLevel}>{level}</b>
                {/each}
              </div>
            </section>

            <section class="status" class:red={toastTone === 'red'} class:blue={toastTone === 'blue'}>
              {toast}
            </section>

            {#if freeSpinLabel}
              <section class="free-spins" class:total-war={totalWarActive}>{freeSpinLabel}</section>
            {/if}

            {#if currentWin > 0 || totalWin > 0}
              <section class="win-panel level-{winLevel}">
                <span>WIN</span>
                <strong>${currentWin.toFixed(2)}</strong>
                <em>TOTAL ${totalWin.toFixed(2)}</em>
              </section>
            {/if}

            <footer class="controls">
              <div class="readout">
                <span>BALANCE</span>
                <strong>${balance.toFixed(2)}</strong>
              </div>
              <div class="bet">
                <button on:click={() => adjustBet(-1)} disabled={playing}>-</button>
                <div><span>BET</span><strong>${bet.toFixed(2)}</strong></div>
                <button on:click={() => adjustBet(1)} disabled={playing}>+</button>
              </div>
              <button class="spin" on:click={() => play('base')} disabled={playing}>{playing ? 'FIRING' : 'SPIN'}</button>
              <button class="buy" on:click={() => play('warpath_spins')} disabled={playing}>WARPATH BUY</button>
              <button class="buy red" on:click={() => play('total_war_spins')} disabled={playing}>TOTAL WAR BUY</button>
              <button class="mini" on:click={() => play('blackbird_strike')} disabled={playing}>BLACKBIRD</button>
              <button class="mini" on:click={() => play('boosters')} disabled={playing}>OVERKILL</button>
            </footer>

            <aside class="mechanics">
              <b>REEL 6:</b> SR-71 + high-pay characters only
              <b>WILD:</b> Stealth Nuke stacked, cascade +1 multiplier
              <b>SCATTER:</b> Warpath Flare
            </aside>
          </div>
        </div>

        <style>
          .viewport {
            width: 100vw;
            height: 100vh;
            display: grid;
            place-items: center;
            overflow: hidden;
            background: radial-gradient(circle at 50% 40%, #26100c 0, #050403 55%, #000 100%);
          }

          .game-shell {
            position: relative;
            width: 1920px;
            height: 1080px;
            transform-origin: center;
            overflow: hidden;
            background: #050403;
          }

          .grain {
            position: absolute;
            inset: 0;
            pointer-events: none;
            opacity: 0.18;
            mix-blend-mode: overlay;
            background-image:
              linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px),
              linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px);
            background-size: 7px 11px;
            animation: drift 1.3s steps(2) infinite;
          }

          .title-block {
            position: absolute;
            top: 28px;
            left: 50%;
            width: 900px;
            transform: translateX(-50%);
            text-align: center;
            pointer-events: none;
            text-shadow: 0 6px 0 #000, 0 0 28px rgba(180, 28, 24, 0.4);
          }

          .eyebrow,
          .ways {
            color: #a66e50;
            letter-spacing: 8px;
            font-size: 18px;
            font-weight: 900;
          }

          h1 {
            margin: 0;
            color: #d6d0c2;
            font-size: 86px;
            letter-spacing: 18px;
            line-height: 0.95;
          }

          .meter {
            position: absolute;
            left: 52px;
            top: 170px;
            padding: 16px 18px;
            background: rgba(10, 8, 7, 0.78);
            border: 2px solid rgba(139, 50, 36, 0.85);
            box-shadow: 0 0 32px rgba(130, 26, 18, 0.24);
          }

          .meter span {
            display: block;
            color: #8d7c6e;
            font-size: 15px;
            letter-spacing: 4px;
            margin-bottom: 10px;
            font-weight: 900;
          }

          .pips {
            display: flex;
            gap: 9px;
          }

          .pips b {
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            color: #3d332e;
            background: #14100e;
            clip-path: polygon(14% 0, 100% 0, 86% 100%, 0% 100%);
            border: 1px solid #3f332e;
          }

          .pips b.active {
            color: #0c0504;
            background: linear-gradient(#ff8338, #a82418);
            box-shadow: 0 0 22px rgba(255, 77, 42, 0.7);
          }

          .status,
          .free-spins {
            position: absolute;
            right: 58px;
            top: 170px;
            min-width: 330px;
            padding: 18px 24px;
            color: #ffad5f;
            font-size: 30px;
            font-weight: 900;
            letter-spacing: 3px;
            text-align: center;
            background: rgba(12, 9, 8, 0.78);
            border: 2px solid rgba(180, 82, 38, 0.75);
            text-shadow: 0 3px 0 #000;
          }

          .status.red,
          .free-spins.total-war {
            color: #ff3d35;
            border-color: #cc2018;
            box-shadow: 0 0 42px rgba(200, 0, 0, 0.42);
          }

          .status.blue {
            color: #84dbff;
            border-color: #4ac6ff;
          }

          .free-spins {
            top: 252px;
            color: #d9cfc2;
            font-size: 24px;
          }

          .win-panel {
            position: absolute;
            left: 50%;
            bottom: 178px;
            transform: translateX(-50%) rotate(-1deg);
            min-width: 460px;
            padding: 22px 46px;
            text-align: center;
            background: linear-gradient(100deg, rgba(48, 12, 8, .94), rgba(130, 35, 20, .92));
            border: 4px solid rgba(255, 110, 48, .7);
            box-shadow: 0 0 55px rgba(180, 30, 18, .55);
            animation: stamp 0.22s ease-out;
          }

          .win-panel span,
          .win-panel em {
            display: block;
            color: #21110b;
            font-weight: 900;
            letter-spacing: 5px;
          }

          .win-panel strong {
            display: block;
            color: #ffe4c8;
            font-size: 74px;
            line-height: 1;
            text-shadow: 0 5px 0 #000;
          }

          .controls {
            position: absolute;
            left: 50%;
            bottom: 34px;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 18px 22px;
            background: rgba(8, 7, 6, .9);
            border: 2px solid rgba(100, 70, 52, .9);
            box-shadow: 0 0 44px rgba(0, 0, 0, .7);
          }

          .readout,
          .bet {
            min-width: 150px;
            color: #d1c5b6;
            font-weight: 900;
          }

          .readout span,
          .bet span {
            display: block;
            color: #74675d;
            font-size: 12px;
            letter-spacing: 3px;
          }

          .readout strong,
          .bet strong {
            font-size: 26px;
          }

          .bet {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
          }

          button {
            cursor: pointer;
            border: 0;
            color: #130805;
            font-weight: 1000;
            letter-spacing: 2px;
            background: linear-gradient(#ff8c3b, #a92817);
            box-shadow: inset 0 2px rgba(255,255,255,.18), 0 5px 0 #3b0f09;
            transition: transform .08s ease, filter .15s ease;
          }

          button:disabled {
            cursor: not-allowed;
            filter: grayscale(1) brightness(.55);
          }

          button:not(:disabled):active {
            transform: translateY(4px);
            box-shadow: inset 0 2px rgba(255,255,255,.12), 0 1px 0 #3b0f09;
          }

          .bet button {
            width: 42px;
            height: 42px;
            font-size: 30px;
          }

          .spin {
            width: 180px;
            height: 86px;
            font-size: 36px;
            background: linear-gradient(#ffbd5f, #db401e 55%, #67150e);
          }

          .buy,
          .mini {
            height: 62px;
            padding: 0 22px;
            font-size: 18px;
          }

          .buy.red {
            color: #fff0e8;
            background: linear-gradient(#ff4d40, #7f0704);
          }

          .mini {
            color: #d6d0c2;
            background: linear-gradient(#45403b, #171312);
            box-shadow: inset 0 2px rgba(255,255,255,.12), 0 5px 0 #050403;
          }

          .mechanics {
            position: absolute;
            left: 52px;
            bottom: 170px;
            width: 300px;
            display: grid;
            gap: 6px;
            color: #8d7f72;
            font-size: 14px;
            line-height: 1.25;
            padding: 16px;
            background: rgba(8,7,6,.72);
            border-left: 4px solid #792318;
          }

          .mechanics b {
            color: #d1c5b6;
            letter-spacing: 2px;
          }

          @keyframes drift {
            from { transform: translate3d(0, 0, 0); }
            to { transform: translate3d(7px, 11px, 0); }
          }

          @keyframes stamp {
            from { transform: translateX(-50%) scale(1.4) rotate(-5deg); opacity: 0; }
            to { transform: translateX(-50%) scale(1) rotate(-1deg); opacity: 1; }
          }
        </style>
    """)
    write("frontend/src/lib/stories/base_books.ts", """
        import type { Book } from '$lib/game/types';

        export const note = 'Storybook-style fixture module. Runtime demo loads JSONL books from /static/books.';
        export const books: Book[] = [];
    """)
    write("frontend/src/lib/stories/book_events.ts", """
        import type { BookEvent } from '$lib/game/types';

        export const events: Partial<Record<BookEvent['type'], BookEvent>> = {};
    """)


def readme_and_manifest() -> None:
    asset_files = sorted(str(path.relative_to(ROOT / "frontend" / "static")) for path in (ROOT / "frontend" / "static" / "assets").glob("**/*") if path.is_file())
    manifest = {
        "game": "Warpath Reels",
        "artDirection": "Gritty painted comic-book placeholders. Latina lady soldier is the only vivid cool red focus; other symbols are desaturated.",
        "assets": asset_files,
    }
    write("asset-manifest.json", json.dumps(manifest, indent=2))
    write("README.md", """
        # Warpath Reels

        Clean GitHub-ready StakeEngine-style slot game repository for **Warpath Reels**.

        ## What is Included

        - SvelteKit + PixiJS frontend with animated reels, cascades, particle effects, screen shake, sandstorm parallax, Total War tint, Blackbird Strike, boosters, and Reel 6 takeover.
        - Python math package with `game_config.py`, `gamestate.py`, `features.py`, `reels.py`, `paytable.py`, `symbols.py`, and generated RGS-style JSONL books.
        - Placeholder PNG assets using the requested filenames and art direction placeholders.
        - GitHub-ready root files: `.gitignore`, `README.md`, `pnpm-workspace.yaml`, root `package.json`, and `asset-manifest.json`.

        ## Requirements

        StakeEngine frontend docs recommend Node `18.18.0` and `pnpm 10.5.0`. This repo was generated with a newer local Node and `pnpm`, but the frontend uses standard SvelteKit/PixiJS dependencies.

        ## Run Locally

        ```bash
        pnpm install
        pnpm generate:books
        pnpm dev
        ```

        Open `http://localhost:5173`.

        ## Build

        ```bash
        pnpm build
        ```

        Static output is written to `frontend/build`.

        ## Math Books

        Generated books live in:

        - `math/library/books/books_base.jsonl`
        - `math/library/books/books_warpath_spins.jsonl`
        - `math/library/books/books_total_war_spins.jsonl`
        - `math/library/books/books_blackbird_strike.jsonl`
        - `math/library/books/books_boosters.jsonl`

        The frontend dev mock loads copies from `frontend/static/books/`.

        ## Notes

        RTP and production math balancing are intentionally not finalized. The current math package is deterministic and suitable for frontend animation, RGS event integration, and future math iteration.

        ## Official Docs Read

        Implementation follows the public StakeEngine documentation patterns for dependencies, getting started, Storybook-style book fixtures, flowchart/bookEvent sequencing, task breakdown, adding events, file structure, context/event emitter ideas, UI, and Math SDK JSONL/lookup table outputs.
    """)


def generate_books_inline() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "math"))
    from generate_books import main

    main()


def create_static_reels() -> None:
    static_dir = ROOT / "math" / "static-reels"
    static_dir.mkdir(parents=True, exist_ok=True)
    from warpath_math.reels import BASE_REELS, TOTAL_WAR_REELS, WARPATH_REELS

    for name, reels in [("reels_base.csv", BASE_REELS), ("reels_warpath.csv", WARPATH_REELS), ("reels_totalwar.csv", TOTAL_WAR_REELS)]:
        with (static_dir / name).open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([f"reel_{idx + 1}" for idx in range(len(reels))])
            max_len = max(len(reel) for reel in reels)
            for row in range(max_len):
                writer.writerow([reel[row % len(reel)] for reel in reels])


def main() -> None:
    random.seed(77)
    make_background()
    make_symbols()
    make_particles()
    make_effect_sheets()
    make_ui()
    python_math_files()
    frontend_files()
    generate_books_inline()
    create_static_reels()
    readme_and_manifest()
    print("Warpath Reels repository scaffolded.")


if __name__ == "__main__":
    main()
