"""Generate WorkSleepRepeat.ico from the tray lamp sprite for PyInstaller."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from PIL import Image
import sprites
import config


def _image(grid, colors, size):
    cells = len(grid)
    scale = max(1, size // cells)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = img.load()
    for row, line in enumerate(grid):
        for col, ch in enumerate(line):
            color = colors.get(ch)
            if color is None:
                continue
            r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            for y in range(row * scale, min(size, (row + 1) * scale)):
                for x in range(col * scale, min(size, (col + 1) * scale)):
                    pixels[x, y] = (r, g, b, 255)
    return img


def main():
    out = os.path.join(os.path.dirname(__file__), "..", "WorkSleepRepeat.ico")
    sizes = [16, 32, 48, 64, 128, 256]
    images = [_image(sprites.TRAY_HEAD, sprites.TRAY_HEAD_COLORS, s) for s in sizes]
    images[0].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[1:])
    print("wrote", os.path.abspath(out))


if __name__ == "__main__":
    main()
