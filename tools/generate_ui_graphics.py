from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "static" / "assets" / "ui"
FONT_NARROW = Path("/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf")
FONT_DISPLAY = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def fit_font(text: str, path: Path, max_width: int, start_size: int) -> ImageFont.FreeTypeFont:
    size = start_size
    probe = ImageDraw.Draw(Image.new("RGBA", (16, 16)))
    while size > 20:
        candidate = font(path, size)
        box = probe.textbbox((0, 0), text, font=candidate, stroke_width=max(2, size // 18))
        if box[2] - box[0] <= max_width:
            return candidate
        size -= 4
    return font(path, size)


def center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, face: ImageFont.FreeTypeFont, **kwargs) -> None:
    stroke_width = int(kwargs.get("stroke_width", 0))
    bounds = draw.textbbox((0, 0), text, font=face, stroke_width=stroke_width)
    x = box[0] + (box[2] - box[0] - (bounds[2] - bounds[0])) / 2 - bounds[0]
    y = box[1] + (box[3] - box[1] - (bounds[3] - bounds[1])) / 2 - bounds[1]
    draw.text((x, y), text, font=face, **kwargs)


def add_noise_texture(img: Image.Image, strength: int = 26) -> None:
    random.seed(93)
    px = img.load()
    width, height = img.size
    for _ in range(width * height // 90):
        x = random.randrange(width)
        y = random.randrange(height)
        r, g, b, a = px[x, y]
        if a:
            delta = random.randint(-strength, strength)
            px[x, y] = (
                max(0, min(255, r + delta)),
                max(0, min(255, g + delta)),
                max(0, min(255, b + delta)),
                a,
            )


def blood_splatter(draw: ImageDraw.ImageDraw, width: int, height: int, density: int = 55) -> None:
    random.seed(width + height + density)
    for _ in range(density):
        cx = random.randint(0, width)
        cy = random.choice([random.randint(0, height // 4), random.randint(height * 2 // 3, height)])
        radius = random.randint(2, 14)
        color = random.choice([(114, 8, 4, 160), (160, 18, 10, 190), (62, 3, 2, 180)])
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)
        if random.random() < 0.28:
            draw.line((cx, cy, cx + random.randint(-90, 90), cy + random.randint(-28, 28)), fill=color, width=random.randint(2, 5))


def slash_cuts(layer: Image.Image, count: int, alpha: int = 185) -> None:
    draw = ImageDraw.Draw(layer)
    width, height = layer.size
    random.seed(count + width)
    for _ in range(count):
        y = random.randint(24, height - 20)
        x = random.randint(20, width - 80)
        draw.line(
            (x, y, x + random.randint(70, 190), y + random.randint(-18, 18)),
            fill=(10, 7, 6, alpha),
            width=random.randint(3, 8),
        )


def draw_plate(size: tuple[int, int], glow: bool = True) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((22, 30, width - 22, height - 20), radius=26, fill=(0, 0, 0, 205))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    draw.rounded_rectangle((28, 24, width - 28, height - 28), radius=22, fill=(18, 16, 14, 238), outline=(99, 35, 24, 255), width=5)
    draw.rounded_rectangle((42, 38, width - 42, height - 42), radius=18, outline=(178, 150, 121, 90), width=2)
    for y in range(35, height - 40, 13):
        tone = 18 + (y % 39)
        draw.line((46, y, width - 46, y + random.randint(-2, 2)), fill=(tone, tone - 4, tone - 8, 38), width=2)
    if glow:
        draw.rounded_rectangle((34, 31, width - 34, height - 34), radius=20, outline=(190, 20, 14, 135), width=3)
    blood_splatter(draw, width, height, 32)
    return img


def draw_logo() -> None:
    size = (1180, 320)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    warpath_font = fit_font("WARPATH", FONT_NARROW, 1060, 188)
    reels_font = fit_font("REELS", FONT_NARROW, 690, 138)
    center_text(shadow_draw, (45, 8, 1135, 176), "WARPATH", warpath_font, fill=(0, 0, 0, 255), stroke_width=24, stroke_fill=(0, 0, 0, 255))
    center_text(shadow_draw, (250, 140, 930, 288), "REELS", reels_font, fill=(0, 0, 0, 245), stroke_width=20, stroke_fill=(0, 0, 0, 245))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))

    red_slash = Image.new("RGBA", size, (0, 0, 0, 0))
    red_draw = ImageDraw.Draw(red_slash)
    red_draw.polygon([(210, 212), (998, 160), (1022, 200), (236, 256)], fill=(153, 14, 11, 205))
    red_draw.line((142, 284, 1060, 236), fill=(226, 39, 23, 190), width=8)
    red_draw.line((116, 63, 1040, 34), fill=(32, 21, 17, 170), width=10)
    img.alpha_composite(red_slash.filter(ImageFilter.GaussianBlur(1.2)))

    center_text(draw, (45, 0, 1135, 172), "WARPATH", warpath_font, fill=(238, 232, 214, 255), stroke_width=13, stroke_fill=(8, 6, 5, 255))
    center_text(draw, (250, 136, 930, 284), "REELS", reels_font, fill=(231, 43, 25, 255), stroke_width=11, stroke_fill=(10, 4, 4, 255))
    center_text(draw, (48, -7, 1138, 162), "WARPATH", warpath_font, fill=(255, 255, 246, 48), stroke_width=1, stroke_fill=(255, 255, 255, 28))
    center_text(draw, (253, 130, 933, 276), "REELS", reels_font, fill=(255, 104, 60, 60), stroke_width=1, stroke_fill=(255, 104, 60, 36))
    slash_cuts(img, 20, 135)
    blood_splatter(draw, size[0], size[1], 12)
    add_noise_texture(img, 22)
    bbox = img.getbbox()
    if bbox:
        pad = 18
        cropped = img.crop((
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(size[0], bbox[2] + pad),
            min(size[1], bbox[3] + pad),
        ))
        cropped.save(OUT / "logo_warpath_reels_crisp.png")
    else:
        img.save(OUT / "logo_warpath_reels_crisp.png")


def draw_bonus_missile_button(path: Path) -> None:
    size = (390, 142)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((42, 42, 318, 102), radius=30, fill=(0, 0, 0, 210))
    shadow_draw.polygon([(308, 42), (370, 72), (308, 102)], fill=(0, 0, 0, 210))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((34, 36, 318, 100), radius=32, fill=(34, 31, 27, 255), outline=(197, 181, 151, 245), width=5)
    draw.polygon([(306, 36), (372, 72), (306, 100)], fill=(190, 28, 19, 255), outline=(232, 196, 146, 230))
    draw.polygon([(58, 96), (16, 124), (86, 111)], fill=(156, 22, 17, 240))
    draw.polygon([(58, 40), (16, 16), (86, 29)], fill=(156, 22, 17, 225))
    draw.line((48, 48, 302, 48), fill=(255, 229, 182, 64), width=3)
    draw.line((58, 94, 300, 94), fill=(0, 0, 0, 120), width=4)
    for x in range(70, 292, 38):
        draw.ellipse((x - 4, 68, x + 4, 76), fill=(203, 185, 155, 210))
    face = fit_font("BONUS", FONT_NARROW, 226, 66)
    center_text(draw, (64, 40, 292, 100), "BONUS", face, fill=(239, 231, 208, 255), stroke_width=6, stroke_fill=(10, 6, 5, 255))
    center_text(draw, (64, 34, 292, 94), "BONUS", face, fill=(255, 255, 245, 42), stroke_width=1, stroke_fill=(255, 255, 255, 30))
    blood_splatter(draw, size[0], size[1], 8)
    add_noise_texture(img, 14)
    img.save(path)


def draw_buy_button(path: Path, spins: int, scatters: int) -> None:
    size = (260, 132)
    img = draw_plate(size, glow=True)
    draw = ImageDraw.Draw(img)
    small = font(FONT_NARROW, 25)
    big = font(FONT_NARROW, 82)
    mid = font(FONT_NARROW, 38)
    center_text(draw, (0, 5, 260, 77), str(spins), big, fill=(255, 80, 42, 255), stroke_width=7, stroke_fill=(12, 5, 4, 255))
    center_text(draw, (0, 64, 260, 104), "SPINS", mid, fill=(235, 226, 205, 255), stroke_width=4, stroke_fill=(10, 5, 4, 255))
    center_text(draw, (0, 101, 260, 127), f"{scatters} FLARES", small, fill=(218, 125, 72, 255), stroke_width=3, stroke_fill=(9, 5, 4, 255))
    add_noise_texture(img, 18)
    img.save(path)


def draw_spin_state(path: Path, label: str, red: bool = False) -> None:
    size = (260, 132)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 10, 252, 122), radius=64, fill=(17, 16, 15, 245), outline=(196, 175, 150, 210), width=5)
    draw.ellipse((30, 24, 230, 108), fill=(20, 16, 14, 250), outline=(160, 20, 12, 210), width=5)
    for angle in range(0, 360, 24):
        x = 130 + math.cos(math.radians(angle)) * 107
        y = 66 + math.sin(math.radians(angle)) * 48
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(166, 150, 128, 220))
    face = fit_font(label, FONT_NARROW, 165, 64)
    fill = (255, 71, 36, 255) if red else (235, 229, 212, 255)
    center_text(draw, (30, 26, 230, 108), label, face, fill=fill, stroke_width=6, stroke_fill=(7, 5, 4, 255))
    add_noise_texture(img, 16)
    img.save(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw_logo()
    draw_buy_button(OUT / "buy_warpath_8.png", 8, 3)
    draw_buy_button(OUT / "buy_warpath_10.png", 10, 4)
    draw_buy_button(OUT / "buy_warpath_12.png", 12, 5)
    draw_bonus_missile_button(OUT / "bonus_missile_button.png")
    draw_spin_state(OUT / "spin_button_idle_clean.png", "SPIN")
    draw_spin_state(OUT / "spin_button_next.png", "NEXT", red=True)
    draw_spin_state(OUT / "spin_button_firing.png", "FIRE", red=True)


if __name__ == "__main__":
    main()
