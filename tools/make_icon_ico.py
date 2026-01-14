from __future__ import annotations

from pathlib import Path


def main() -> int:
    icon_png = Path(__file__).resolve().parents[1] / "icons" / "icon.png"
    icon_ico = Path(__file__).resolve().parents[1] / "icons" / "icon.ico"

    if not icon_png.exists():
        raise FileNotFoundError(str(icon_png))

    from PIL import Image

    img = Image.open(icon_png)
    if img.mode not in ("RGBA", "RGB"):
        img = img.convert("RGBA")

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(icon_ico, format="ICO", sizes=sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

