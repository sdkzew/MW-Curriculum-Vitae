from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
SCALE = 4
SIZE = 256


def scaled(value: float) -> int:
    return round(value * SCALE)


canvas = Image.new("RGBA", (SIZE * SCALE, SIZE * SCALE), (0, 0, 0, 0))
glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow)
glow_draw.rounded_rectangle(
    (scaled(13), scaled(13), scaled(243), scaled(243)),
    radius=scaled(56),
    fill=(116, 61, 235, 100),
)
glow = glow.filter(ImageFilter.GaussianBlur(scaled(17)))
canvas.alpha_composite(glow)

draw = ImageDraw.Draw(canvas)
draw.rounded_rectangle(
    (scaled(18), scaled(18), scaled(238), scaled(238)),
    radius=scaled(50),
    fill=(9, 9, 15, 255),
    outline=(126, 74, 239, 255),
    width=scaled(4),
)
draw.rounded_rectangle(
    (scaled(27), scaled(27), scaled(229), scaled(229)),
    radius=scaled(42),
    outline=(77, 58, 117, 220),
    width=scaled(2),
)

points = [
    (43, 151),
    (72, 91),
    (95, 138),
    (121, 64),
    (146, 165),
    (170, 99),
    (192, 149),
    (218, 91),
]
draw.line(
    [(scaled(x), scaled(y)) for x, y in points],
    fill=(246, 243, 251, 255),
    width=scaled(15),
    joint="curve",
)
draw.ellipse(
    (scaled(204), scaled(48), scaled(225), scaled(69)),
    fill=(163, 111, 255, 255),
)

canvas = canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
png_path = STATIC / "mw-icon.png"
ico_path = STATIC / "mw-icon.ico"
canvas.save(png_path, format="PNG", optimize=True)
canvas.save(ico_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Generated {png_path} and {ico_path}")
