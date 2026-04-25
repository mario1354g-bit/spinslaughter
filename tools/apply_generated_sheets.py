from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageEnhance


ROOT = Path.cwd()
GEN_ROOT = Path.home() / ".codex" / "generated_images"
ASSET_ROOT = ROOT / "frontend" / "static" / "assets"
SOURCE_DIR = ASSET_ROOT / "source_sheets"


def latest_generated_pngs(count: int = 5) -> list[Path]:
    files = sorted(GEN_ROOT.glob("**/*.png"), key=lambda path: path.stat().st_mtime)
    if len(files) < count:
        raise SystemExit(f"Expected at least {count} generated images under {GEN_ROOT}, found {len(files)}")
    return files[-count:]


def tile_crop(image: Image.Image, cols: int, rows: int, index: int, inset_ratio: float = 0.035) -> Image.Image:
    width, height = image.size
    col = index % cols
    row = index // cols
    cell_w = width / cols
    cell_h = height / rows
    inset_x = cell_w * inset_ratio
    inset_y = cell_h * inset_ratio
    box = (
        int(col * cell_w + inset_x),
        int(row * cell_h + inset_y),
        int((col + 1) * cell_w - inset_x),
        int((row + 1) * cell_h - inset_y),
    )
    return image.crop(box)


def save_tile(image: Image.Image, cols: int, rows: int, index: int, out: str, size: tuple[int, int], inset_ratio: float = 0.035, contrast: float = 1.0) -> None:
    tile = tile_crop(image, cols, rows, index, inset_ratio)
    tile = tile.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    if contrast != 1.0:
        tile = ImageEnhance.Contrast(tile).enhance(contrast)
    path = ASSET_ROOT / out
    path.parent.mkdir(parents=True, exist_ok=True)
    tile.save(path)


def copy_panel(image: Image.Image, cols: int, rows: int, index: int, out: str, size: tuple[int, int], inset_ratio: float = 0.0, alpha: int | None = None) -> None:
    panel = tile_crop(image, cols, rows, index, inset_ratio)
    panel = panel.resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    if alpha is not None:
        panel.putalpha(alpha)
    path = ASSET_ROOT / out
    path.parent.mkdir(parents=True, exist_ok=True)
    panel.save(path)


def main() -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    symbols, tall, backgrounds, ui, fx = latest_generated_pngs()

    sheet_map = {
        "chatgpt_symbols_sheet.png": symbols,
        "chatgpt_tall_takeovers_sheet.png": tall,
        "chatgpt_backgrounds_sheet.png": backgrounds,
        "chatgpt_ui_sheet.png": ui,
        "chatgpt_fx_sheet.png": fx,
    }
    for name, src in sheet_map.items():
        shutil.copy2(src, SOURCE_DIR / name)

    symbols_img = Image.open(symbols).convert("RGB")
    tall_img = Image.open(tall).convert("RGB")
    backgrounds_img = Image.open(backgrounds).convert("RGB")
    ui_img = Image.open(ui).convert("RGB")
    fx_img = Image.open(fx).convert("RGB")

    symbol_outputs = [
        ("symbols/symbol_high_lady_soldier.png", (260, 260), 1.08),
        ("symbols/symbol_high_taliban_old.png", (260, 260), 0.92),
        ("symbols/symbol_high_iraqi_young.png", (260, 260), 0.92),
        ("symbols/symbol_high_iraqi_soldier.png", (260, 260), 0.92),
        ("symbols/symbol_high_woman_soldier.png", (260, 260), 0.92),
        ("symbols/symbol_low_10.png", (260, 260), 1.05),
        ("symbols/symbol_low_j.png", (260, 260), 1.05),
        ("symbols/symbol_low_q.png", (260, 260), 1.05),
        ("symbols/symbol_low_k.png", (260, 260), 1.05),
        ("symbols/scatter_warpath_flare.png", (260, 260), 1.08),
        ("symbols/wild_stealth_nuke.png", (260, 260), 1.08),
        ("symbols/reel6_sr71_blackbird_2high.png", (260, 530), 1.0),
        ("symbols/wild_stealth_nuke_3high.png", (260, 800), 1.05),
        ("symbols/scatter_warpath_flare_3high.png", (260, 800), 1.05),
        ("symbols/reel6_sr71_blackbird_full.png", (820, 800), 1.0),
        ("ui/paytable_bg.png", (900, 680), 0.92),
    ]
    for index, (out, size, contrast) in enumerate(symbol_outputs):
        save_tile(symbols_img, 4, 4, index, out, size, contrast=contrast)

    tall_outputs = [
        ("symbols/symbol_high_lady_soldier_tall.png", (260, 800), 1.08),
        ("symbols/symbol_high_taliban_old_tall.png", (260, 800), 0.92),
        ("symbols/symbol_high_iraqi_young_tall.png", (260, 800), 0.92),
        ("symbols/symbol_high_iraqi_soldier_tall.png", (260, 800), 0.92),
        ("symbols/symbol_high_woman_soldier_tall.png", (260, 800), 0.92),
        ("symbols/wild_stealth_nuke_3high.png", (260, 800), 1.08),
        ("symbols/scatter_warpath_flare_3high.png", (260, 800), 1.08),
        ("symbols/reel6_sr71_blackbird_2high.png", (260, 530), 1.0),
        ("symbols/reel6_sr71_blackbird_3high.png", (260, 800), 1.0),
        ("symbols/reel6_sr71_blackbird_full.png", (820, 800), 1.0),
        ("animations/cascade_animation_frames.png", (1024, 256), 1.0),
        ("animations/symbol_shatter_sheet.png", (1024, 256), 1.0),
    ]
    for index, (out, size, contrast) in enumerate(tall_outputs):
        save_tile(tall_img, 4, 3, index, out, size, contrast=contrast)

    copy_panel(backgrounds_img, 2, 2, 0, "backgrounds/background_desert_futuristic_night.png", (1920, 1080))
    copy_panel(backgrounds_img, 2, 2, 1, "backgrounds/sandstorm_far.png", (1920, 1080), alpha=130)
    copy_panel(backgrounds_img, 2, 2, 2, "backgrounds/sandstorm_near.png", (1920, 1080), alpha=165)
    copy_panel(backgrounds_img, 2, 2, 3, "backgrounds/total_war_red_overlay.png", (1920, 1080), alpha=132)

    ui_outputs = [
        ("ui/logo_warpath_reels.png", (720, 220)),
        ("ui/warpath_title.png", (540, 180)),
        ("ui/totalwar_title.png", (540, 180)),
        ("ui/spin_button_idle.png", (260, 132)),
        ("ui/spin_button_pressed.png", (260, 132)),
        ("ui/spin_button_disabled.png", (260, 132)),
        ("ui/buy_button_warpath.png", (320, 120)),
        ("ui/buy_button_totalwar.png", (340, 120)),
        ("ui/bet_panel_bg.png", (960, 150)),
        ("ui/paytable_bg.png", (900, 680)),
        ("ui/fs_counter_bg.png", (260, 120)),
        ("ui/win_banner_big.png", (640, 180)),
        ("ui/win_banner_mega.png", (680, 190)),
        ("ui/win_banner_epic.png", (700, 200)),
        ("ui/win_banner_legendary.png", (760, 220)),
        ("ui/settings_icon.png", (96, 96)),
    ]
    for index, (out, size) in enumerate(ui_outputs):
        save_tile(ui_img, 4, 4, index, out, size, contrast=1.05)
    # Derive simple icon variants from the icon-set tile.
    for icon_name in ["info_icon.png", "autoplay_icon.png", "sound_on_icon.png", "sound_off_icon.png", "coin_particle.png"]:
        shutil.copy2(ASSET_ROOT / "ui/settings_icon.png", ASSET_ROOT / "ui" / icon_name)

    fx_outputs = [
        ("particles/ember_particle.png", (96, 96)),
        ("particles/blood_drop.png", (96, 96)),
        ("particles/smoke_puff.png", (96, 96)),
        ("particles/sand_grain.png", (96, 96)),
        ("particles/spark.png", (96, 96)),
        ("particles/missile_smoke.png", (96, 96)),
        ("particles/debris_chunk.png", (96, 96)),
        ("particles/nuke_glow_ring.png", (96, 96)),
        ("particles/flare_ring.png", (96, 96)),
        ("cascade_animation_frames.png", (1024, 256)),
        ("animations/multiplier_stamp.png", (260, 260)),
        ("animations/wild_pulse_sheet.png", (1024, 256)),
        ("animations/symbol_shatter_sheet.png", (1024, 256)),
        ("animations/reel_spin_blur.png", (260, 260)),
        ("blackbird_missile_launch_sequence.png", (1536, 256)),
        ("animations/blackbird_missile_launch_sequence.png", (1536, 256)),
    ]
    for index, (out, size) in enumerate(fx_outputs):
        save_tile(fx_img, 4, 4, index, out, size, contrast=1.08)

    # Keep root-level aliases in sync with animation subfolder files.
    shutil.copy2(ASSET_ROOT / "animations/cascade_animation_frames.png", ASSET_ROOT / "cascade_animation_frames.png")
    shutil.copy2(ASSET_ROOT / "animations/blackbird_missile_launch_sequence.png", ASSET_ROOT / "blackbird_missile_launch_sequence.png")

    print("Applied generated ChatGPT image sheets to frontend/static/assets")


if __name__ == "__main__":
    main()
