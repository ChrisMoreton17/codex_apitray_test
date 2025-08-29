#!/usr/bin/env python3
"""
Generate a macOS .icns app icon at build time.

Creates a simple, high-contrast badge: colored circle with a white check.
Outputs to assets/AppIcon.icns for py2app to use.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw


SIZES = [16, 32, 64, 128, 256, 512, 1024]


def draw_icon(size: int, color: str = "#2ecc71", border: str = "#0b6623") -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Circle with border
    margin = int(size * 0.08)
    border_w = max(2, int(size * 0.06))
    # Outer border circle
    draw.ellipse(
        (margin, margin, size - margin, size - margin),
        outline=border,
        width=border_w,
        fill=color,
    )

    # Checkmark
    # Proportional points for a crisp check
    thickness = max(3, int(size * 0.08))
    x1, y1 = int(size * 0.28), int(size * 0.55)
    x2, y2 = int(size * 0.43), int(size * 0.70)
    x3, y3 = int(size * 0.75), int(size * 0.35)
    draw.line((x1, y1, x2, y2), fill=(255, 255, 255, 255), width=thickness, joint="curve")
    draw.line((x2, y2, x3, y3), fill=(255, 255, 255, 255), width=thickness, joint="curve")

    # Slight highlight ring
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(highlight)
    d2.ellipse((margin, margin, size - margin, size - margin), outline=(255, 255, 255, 40), width=max(1, border_w // 2))
    img.alpha_composite(highlight)
    return img


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def main():
    root = Path(__file__).resolve().parents[1]
    iconset = root / "assets" / "AppIcon.iconset"
    icns_out = root / "assets" / "AppIcon.icns"
    ensure_dir(iconset)

    # Base color can be changed if needed
    for s in SIZES:
        img = draw_icon(s)
        img.save(iconset / f"icon_{s}x{s}.png")
        img2 = draw_icon(s * 2)
        img2.save(iconset / f"icon_{s}x{s}@2x.png")

    # Convert to .icns via iconutil (macOS tool)
    # Defer the call to CI or local script to avoid platform issues when not on macOS.
    # The CI workflow runs: iconutil -c icns assets/AppIcon.iconset -o assets/AppIcon.icns
    print(f"Iconset created at {iconset}. Run iconutil to produce {icns_out}.")


if __name__ == "__main__":
    main()

