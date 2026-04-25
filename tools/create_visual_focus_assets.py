from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "static" / "assets"
SYMBOLS = ASSETS / "symbols"
FONT_NARROW = Path("/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf")


def center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, size: int, **kwargs) -> None:
    face = ImageFont.truetype(str(FONT_NARROW), size)
    stroke_width = int(kwargs.get("stroke_width", 0))
    bounds = draw.textbbox((0, 0), text, font=face, stroke_width=stroke_width)
    x = box[0] + (box[2] - box[0] - (bounds[2] - bounds[0])) / 2 - bounds[0]
    y = box[1] + (box[3] - box[1] - (bounds[3] - bounds[1])) / 2 - bounds[1]
    draw.text((x, y), text, font=face, **kwargs)


def add_red_wild_treatment(source: Path, target: Path, *, badge: bool = False) -> None:
    image = Image.open(source).convert("RGBA")
    rgb = image.convert("RGB")
    rgb = ImageEnhance.Color(rgb).enhance(0.74)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.14)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.18)
    treated = rgb.convert("RGBA")
    treated.putalpha(image.getchannel("A"))

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    width, height = image.size
    radius = max(18, min(width, height) // 12)
    for index, alpha in enumerate((18, 26, 34, 50)):
        inset = 14 - index * 4
        draw.rounded_rectangle(
            [inset, inset, width - inset - 1, height - inset - 1],
            radius=radius,
            outline=(255, 30, 68, alpha),
            width=5 + index * 2,
        )
    veil = Image.new("RGBA", image.size, (126, 8, 28, 12))
    treated = Image.alpha_composite(treated, veil)
    treated = Image.alpha_composite(treated, glow.filter(ImageFilter.GaussianBlur(1.4)))
    if badge:
        badge_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        badge_draw = ImageDraw.Draw(badge_layer)
        width, height = image.size
        box = (42, height - 54, width - 42, height - 14)
        badge_draw.rounded_rectangle(box, radius=12, fill=(8, 6, 5, 205), outline=(226, 36, 51, 235), width=3)
        badge_draw.line((box[0] + 10, box[1] + 5, box[2] - 10, box[1] + 5), fill=(255, 104, 74, 115), width=2)
        center_text(
            badge_draw,
            box,
            "WILD",
            38,
            fill=(248, 234, 211, 255),
            stroke_width=4,
            stroke_fill=(30, 4, 5, 255),
        )
        treated = Image.alpha_composite(treated, badge_layer)
    target.parent.mkdir(parents=True, exist_ok=True)
    treated.save(target)


def main() -> None:
    add_red_wild_treatment(SYMBOLS / "symbol_high_lady_soldier.png", SYMBOLS / "symbol_wild_red_soldier.png", badge=True)
    add_red_wild_treatment(SYMBOLS / "symbol_high_lady_soldier_tall.png", SYMBOLS / "symbol_wild_red_soldier_3high.png")


if __name__ == "__main__":
    main()
