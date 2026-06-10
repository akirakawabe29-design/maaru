from pathlib import Path
from PIL import Image, ImageChops, ImageFilter


SOURCE = Path("/Users/kawabeakira/Downloads/ChatGPT Image 2026年6月10日 12_13_38.png")
OUTPUT = Path(__file__).resolve().parents[1] / "brand" / "logo"

DARK = "#172B33"
CORAL = "#F06F61"


def color_masks(image):
    image = image.convert("RGB")
    dark = Image.new("L", image.size)
    coral = Image.new("L", image.size)
    dark_pixels = []
    coral_pixels = []

    for r, g, b in image.getdata():
        dark_pixels.append(255 if max(r, g, b) < 145 and b >= r * 0.75 else 0)
        coral_pixels.append(
            255 if r > 145 and r > g * 1.22 and r > b * 1.18 and g < 180 else 0
        )

    dark.putdata(dark_pixels)
    coral.putdata(coral_pixels)

    # Smooth only the antialiased image edge, without changing the logo geometry.
    dark = dark.filter(ImageFilter.GaussianBlur(0.55)).point(lambda p: 255 if p >= 112 else 0)
    coral = coral.filter(ImageFilter.GaussianBlur(0.55)).point(lambda p: 255 if p >= 112 else 0)
    return dark, coral


def mask_bbox(*masks):
    boxes = [mask.getbbox() for mask in masks if mask.getbbox()]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def boundary_loops(mask):
    pixels = mask.load()
    width, height = mask.size
    edges = {}

    def add(start, end):
        edges.setdefault(start, []).append(end)

    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                continue
            if y == 0 or pixels[x, y - 1] == 0:
                add((x, y), (x + 1, y))
            if x == width - 1 or pixels[x + 1, y] == 0:
                add((x + 1, y), (x + 1, y + 1))
            if y == height - 1 or pixels[x, y + 1] == 0:
                add((x + 1, y + 1), (x, y + 1))
            if x == 0 or pixels[x - 1, y] == 0:
                add((x, y + 1), (x, y))

    loops = []
    while edges:
        start = next(iter(edges))
        current = start
        loop = [start]
        while True:
            options = edges.get(current)
            if not options:
                break
            nxt = options.pop()
            if not options:
                del edges[current]
            current = nxt
            if current == start:
                break
            loop.append(current)
        if len(loop) >= 4 and current == start:
            loops.append(loop)
    return loops


def remove_collinear(points):
    if len(points) < 4:
        return points
    result = []
    count = len(points)
    for i, point in enumerate(points):
        prev = points[i - 1]
        nxt = points[(i + 1) % count]
        if (point[0] - prev[0]) * (nxt[1] - point[1]) == (
            point[1] - prev[1]
        ) * (nxt[0] - point[0]):
            continue
        result.append(point)
    return result


def perpendicular_distance(point, start, end):
    if start == end:
        return ((point[0] - start[0]) ** 2 + (point[1] - start[1]) ** 2) ** 0.5
    numerator = abs(
        (end[1] - start[1]) * point[0]
        - (end[0] - start[0]) * point[1]
        + end[0] * start[1]
        - end[1] * start[0]
    )
    denominator = ((end[1] - start[1]) ** 2 + (end[0] - start[0]) ** 2) ** 0.5
    return numerator / denominator


def rdp(points, epsilon):
    if len(points) < 3:
        return points
    start, end = points[0], points[-1]
    distances = [perpendicular_distance(point, start, end) for point in points[1:-1]]
    if not distances:
        return [start, end]
    maximum = max(distances)
    index = distances.index(maximum) + 1
    if maximum > epsilon:
        left = rdp(points[: index + 1], epsilon)
        right = rdp(points[index:], epsilon)
        return left[:-1] + right
    return [start, end]


def simplify_closed(points, epsilon=0.45):
    points = remove_collinear(points)
    if len(points) < 5:
        return points
    anchor = min(range(len(points)), key=lambda i: (points[i][0], points[i][1]))
    rotated = points[anchor:] + points[:anchor]
    simplified = rdp(rotated + [rotated[0]], epsilon)
    return simplified[:-1]


def path_data(mask, origin):
    commands = []
    ox, oy = origin
    for loop in boundary_loops(mask):
        loop = simplify_closed(loop)
        if len(loop) < 3:
            continue
        commands.append(f"M{loop[0][0] - ox} {loop[0][1] - oy}")
        commands.extend(f"L{x - ox} {y - oy}" for x, y in loop[1:])
        commands.append("Z")
    return "".join(commands)


def write_svg(path, dark_mask, coral_mask, bbox, title):
    left, top, right, bottom = bbox
    padding = 24
    origin = (left - padding, top - padding)
    width = right - left + padding * 2
    height = bottom - top + padding * 2

    dark_crop = dark_mask.crop((left, top, right, bottom))
    coral_crop = coral_mask.crop((left, top, right, bottom))
    dark_path = path_data(dark_crop, (-padding, -padding))
    coral_path = path_data(coral_crop, (-padding, -padding))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">
  <path fill="{DARK}" fill-rule="evenodd" d="{dark_path}"/>
  <path fill="{CORAL}" fill-rule="evenodd" d="{coral_path}"/>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def write_monochrome_svg(path, mask, bbox, title):
    left, top, right, bottom = bbox
    padding = 24
    width = right - left + padding * 2
    height = bottom - top + padding * 2
    cropped = mask.crop((left, top, right, bottom))
    data = path_data(cropped, (-padding, -padding))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{title}">
  <path fill="{DARK}" fill-rule="evenodd" d="{data}"/>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image = Image.open(SOURCE)
    dark, coral = color_masks(image)
    full_bbox = mask_bbox(dark, coral)
    write_svg(
        OUTPUT / "maaru-logo-horizontal.svg",
        dark,
        coral,
        full_bbox,
        "MAARU logo",
    )
    write_monochrome_svg(
        OUTPUT / "maaru-logo-monochrome.svg",
        ImageChops.lighter(dark, coral),
        full_bbox,
        "MAARU monochrome logo",
    )

    symbol_box = (90, 320, 500, 760)
    symbol_dark = dark.crop(symbol_box)
    symbol_coral = coral.crop(symbol_box)
    local_bbox = mask_bbox(symbol_dark, symbol_coral)
    symbol_bbox = (
        local_bbox[0] + symbol_box[0],
        local_bbox[1] + symbol_box[1],
        local_bbox[2] + symbol_box[0],
        local_bbox[3] + symbol_box[1],
    )
    write_svg(
        OUTPUT / "maaru-symbol.svg",
        dark,
        coral,
        symbol_bbox,
        "MAARU symbol",
    )


if __name__ == "__main__":
    main()
