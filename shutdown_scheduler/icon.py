from __future__ import annotations

from PIL import Image, ImageDraw


def create_tray_image(enabled: bool) -> Image.Image:
    """Render a small power-glyph icon. Green when armed, gray when disabled."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    fg = (60, 175, 90, 255) if enabled else (140, 140, 140, 255)

    pad = 10
    # Outer ring.
    draw.ellipse((pad, pad, size - pad, size - pad), outline=fg, width=5)
    # Vertical power bar through the top of the ring.
    cx = size // 2
    draw.line((cx, pad - 2, cx, size // 2 + 2), fill=fg, width=6)
    return img
