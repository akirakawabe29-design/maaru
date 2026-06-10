from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/Users/kawabeakira/Downloads/ChatGPT Image 2026年6月10日 12_13_38.png")
SVG_PREVIEW = Path("/private/tmp/maaru-logo-horizontal.svg.png")
OUTPUT = ROOT / "brand" / "logo"


def ink_bbox(image):
    rgb = image.convert("RGB")
    mask = Image.new("L", rgb.size)
    pixels = []
    for r, g, b in rgb.getdata():
        pixels.append(255 if min(r, g, b) < 225 else 0)
    mask.putdata(pixels)
    return mask.getbbox()


def crop_ink(image):
    box = ink_bbox(image)
    return image.crop(box), box


def main():
    source = Image.open(SOURCE).convert("RGB")
    preview = Image.open(SVG_PREVIEW).convert("RGB")
    src_logo, src_box = crop_ink(source)
    vec_logo, _ = crop_ink(preview)

    target_w, target_h = src_logo.size
    vec_logo.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

    vector_layer = Image.new("RGB", (target_w, target_h), "white")
    x = (target_w - vec_logo.width) // 2
    y = (target_h - vec_logo.height) // 2
    vector_layer.paste(vec_logo, (x, y))

    source_layer = src_logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    overlay = Image.blend(source_layer, vector_layer, 0.5)
    overlay_canvas = source.copy()
    overlay_canvas.paste(overlay, (src_box[0], src_box[1]))
    overlay_canvas.save(OUTPUT / "maaru-logo-overlay.png", quality=95)

    difference = ImageChops.difference(source_layer, vector_layer)
    difference = ImageEnhance.Contrast(difference).enhance(4)
    diff_canvas = Image.new("RGB", source.size, "white")
    diff_canvas.paste(difference, (src_box[0], src_box[1]))
    draw = ImageDraw.Draw(diff_canvas)
    draw.rectangle(src_box, outline=(210, 210, 210), width=2)
    diff_canvas.save(OUTPUT / "maaru-logo-difference.png", quality=95)


if __name__ == "__main__":
    main()
