from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path.cwd()
GEN_ROOT = Path.home() / ".codex" / "generated_images"
ASSET_ROOT = ROOT / "frontend" / "static" / "assets"
SOURCE_DIR = ASSET_ROOT / "source_sheets"


def latest_generated_pngs(count: int = 2) -> list[Path]:
    files = sorted(GEN_ROOT.glob("**/*.png"), key=lambda path: path.stat().st_mtime)
    if len(files) < count:
        raise SystemExit(f"Expected at least {count} generated images under {GEN_ROOT}, found {len(files)}")
    return files[-count:]


def tile(image: Image.Image, cols: int, rows: int, index: int, inset: float = 0.035) -> Image.Image:
    width, height = image.size
    col = index % cols
    row = index // cols
    cell_w = width / cols
    cell_h = height / rows
    return image.crop(
        (
            int(col * cell_w + cell_w * inset),
            int(row * cell_h + cell_h * inset),
            int((col + 1) * cell_w - cell_w * inset),
            int((row + 1) * cell_h - cell_h * inset),
        )
    )


def grade(img: Image.Image, saturation: float, contrast: float = 1.0, brightness: float = 1.0) -> Image.Image:
    img = img.convert("RGBA")
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    return img


def save(source: Image.Image, cols: int, rows: int, index: int, path: str, size: tuple[int, int], saturation: float, contrast: float = 1.0, brightness: float = 1.0) -> None:
    out = grade(tile(source, cols, rows, index), saturation, contrast, brightness).resize(size, Image.Resampling.LANCZOS)
    target = ASSET_ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target)


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    symbol_sheet, fx_sheet = latest_generated_pngs()
    shutil.copy2(symbol_sheet, SOURCE_DIR / "chatgpt_revision_symbols_desaturated.png")
    shutil.copy2(fx_sheet, SOURCE_DIR / "chatgpt_revision_fx_slow_blackbird.png")

    symbols = Image.open(symbol_sheet).convert("RGB")
    fx = Image.open(fx_sheet).convert("RGB")

    symbol_map = [
        ("symbols/symbol_high_lady_soldier.png", (260, 260), 0, 1.18, 1.08, 1.03),
        ("symbols/symbol_high_taliban_old.png", (260, 260), 1, 0.12, 1.04, 0.96),
        ("symbols/symbol_high_iraqi_young.png", (260, 260), 2, 0.12, 1.04, 0.96),
        ("symbols/symbol_high_iraqi_soldier.png", (260, 260), 3, 0.12, 1.04, 0.96),
        ("symbols/symbol_high_woman_soldier.png", (260, 260), 4, 0.12, 1.04, 0.96),
        ("symbols/symbol_low_10.png", (260, 260), 5, 0.08, 1.08, 0.94),
        ("symbols/symbol_low_j.png", (260, 260), 6, 0.08, 1.08, 0.94),
        ("symbols/symbol_low_q.png", (260, 260), 7, 0.08, 1.08, 0.94),
        ("symbols/symbol_low_k.png", (260, 260), 8, 0.08, 1.08, 0.94),
        ("symbols/scatter_warpath_flare.png", (260, 260), 9, 0.58, 1.08, 1.0),
        ("symbols/wild_stealth_nuke.png", (260, 260), 10, 0.68, 1.12, 1.0),
        ("symbols/reel6_sr71_blackbird_2high.png", (260, 530), 11, 0.08, 1.04, 0.94),
        ("symbols/symbol_high_lady_soldier_tall.png", (260, 800), 12, 1.18, 1.08, 1.03),
        ("symbols/wild_stealth_nuke_3high.png", (260, 800), 13, 0.68, 1.12, 1.0),
        ("symbols/reel6_sr71_blackbird_full.png", (820, 800), 14, 0.08, 1.04, 0.94),
        ("ui/paytable_bg.png", (900, 680), 15, 0.08, 1.0, 0.9),
    ]
    for path, size, index, saturation, contrast, brightness in symbol_map:
        save(symbols, 4, 4, index, path, size, saturation, contrast, brightness)

    # Tall non-lady character takeovers use the desaturated square portraits until final bespoke tall art is requested.
    tall_aliases = [
        ("symbols/symbol_high_taliban_old.png", "symbols/symbol_high_taliban_old_tall.png"),
        ("symbols/symbol_high_iraqi_young.png", "symbols/symbol_high_iraqi_young_tall.png"),
        ("symbols/symbol_high_iraqi_soldier.png", "symbols/symbol_high_iraqi_soldier_tall.png"),
        ("symbols/symbol_high_woman_soldier.png", "symbols/symbol_high_woman_soldier_tall.png"),
    ]
    for source, target in tall_aliases:
        img = Image.open(ASSET_ROOT / source).resize((260, 800), Image.Resampling.LANCZOS)
        img.save(ASSET_ROOT / target)

    # Scatter tall uses the flare canister, not a nuke.
    save(symbols, 4, 4, 9, "symbols/scatter_warpath_flare_3high.png", (260, 800), 0.58, 1.08, 1.0)
    save(symbols, 4, 4, 14, "symbols/reel6_sr71_blackbird_3high.png", (260, 800), 0.08, 1.04, 0.94)

    fx_map = [
        ("animations/reel_spin_blur.png", (260, 260), 0, 0.18, 1.05, 0.96),
        ("animations/anticipation_glow.png", (260, 260), 1, 0.46, 1.08, 1.0),
        ("animations/symbol_shatter_sheet.png", (1024, 256), 2, 0.22, 1.1, 0.96),
        ("animations/cascade_animation_frames.png", (1024, 256), 3, 0.22, 1.1, 0.96),
        ("particles/nuke_glow_ring.png", (96, 96), 4, 0.65, 1.12, 1.0),
        ("animations/wild_pulse_sheet.png", (1024, 256), 5, 0.65, 1.12, 1.0),
        ("animations/multiplier_stamp.png", (260, 260), 6, 0.18, 1.08, 0.95),
        ("particles/flare_ring.png", (96, 96), 7, 0.55, 1.08, 1.0),
        ("symbols/reel6_sr71_blackbird_full.png", (820, 800), 8, 0.08, 1.04, 0.94),
        ("blackbird_missile_launch_sequence.png", (1536, 256), 9, 0.16, 1.06, 0.98),
        ("animations/missile_impact.png", (260, 260), 10, 0.28, 1.1, 1.0),
        ("animations/character_takeover_reveal.png", (260, 800), 11, 0.72, 1.08, 1.0),
        ("animations/escalation_meter_burst.png", (520, 140), 12, 0.48, 1.1, 1.0),
        ("backgrounds/total_war_red_overlay.png", (1920, 1080), 13, 0.7, 1.08, 1.0),
        ("particles/blood_drop.png", (96, 96), 14, 0.55, 1.1, 0.95),
        ("particles/smoke_puff.png", (96, 96), 15, 0.1, 1.0, 0.92),
    ]
    for path, size, index, saturation, contrast, brightness in fx_map:
        save(fx, 4, 4, index, path, size, saturation, contrast, brightness)

    shutil.copy2(ASSET_ROOT / "animations/cascade_animation_frames.png", ASSET_ROOT / "cascade_animation_frames.png")
    shutil.copy2(ASSET_ROOT / "blackbird_missile_launch_sequence.png", ASSET_ROOT / "animations/blackbird_missile_launch_sequence.png")

    # Derive the tiny particles from the revised FX palette.
    save(fx, 4, 4, 15, "particles/ember_particle.png", (96, 96), 0.36, 1.08, 0.96)
    save(fx, 4, 4, 15, "particles/sand_grain.png", (96, 96), 0.08, 1.0, 0.9)
    save(fx, 4, 4, 10, "particles/spark.png", (96, 96), 0.4, 1.15, 1.0)
    save(fx, 4, 4, 10, "particles/debris_chunk.png", (96, 96), 0.1, 1.05, 0.9)
    save(fx, 4, 4, 9, "particles/missile_smoke.png", (96, 96), 0.08, 1.0, 0.95)

    print("Applied desaturated revision sheets and non-nuke wild/scatter assets.")


if __name__ == "__main__":
    main()
