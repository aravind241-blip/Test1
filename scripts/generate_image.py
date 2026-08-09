"""
Generates a 1080x1350 "Breaking News" style image for a given article:
white header block ("BREAKING" + headline + short subheadline) on top,
the article's own photo (from the news API/RSS feed) filling the rest,
with a date badge and the AravindNews24 brand mark at the bottom.

If the article has no usable image, falls back to an original gradient
template (no source credit, no external photo) so a post never breaks.
"""

import os
import io
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")

SIZE_W = 1080
SIZE_H = 1350

BRAND_NAME = "AravindNews24"

# Category -> accent color, label, fallback gradient colors
CATEGORY_STYLE = {
    "india": ((255, 153, 51), "INDIA NEWS", (20, 30, 55), (10, 15, 30)),
    "world": ((66, 165, 245), "WORLD NEWS", (15, 25, 50), (8, 12, 25)),
    "business": ((76, 217, 100), "BUSINESS NEWS", (20, 35, 30), (8, 15, 12)),
    "sports": ((255, 87, 51), "SPORTS NEWS", (45, 20, 20), (18, 8, 8)),
}

IMAGE_DOWNLOAD_TIMEOUT = 12


def _wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _download_image(url: str):
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AravindNews24Bot/1.0)"
        })
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type.lower():
            return None
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return img
    except Exception as e:
        print(f"[generate_image] photo download failed: {e}")
        return None


def _cover_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize+crop an image to fill target_w x target_h, cropping the overflow (like CSS 'cover')."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale) + 1, int(src_h * scale) + 1
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) / 2
    top = (new_h - target_h) / 2
    return img.crop((left, top, left + target_w, top + target_h))


def _draw_header(draw, canvas, category, headline, description):
    accent, label, _, _ = CATEGORY_STYLE.get(category, CATEGORY_STYLE["world"])

    y = 0
    pad_x = 50

    # ---- BREAKING banner ----
    banner_font = ImageFont.truetype(FONT_BOLD, 84)
    bbox = draw.textbbox((0, 0), "BREAKING", font=banner_font)
    tw = bbox[2] - bbox[0]
    y += 40
    draw.text(((SIZE_W - tw) / 2, y), "BREAKING", font=banner_font, fill=(15, 15, 15))
    y += 105

    # ---- category pill ----
    label_font = ImageFont.truetype(FONT_BOLD, 30)
    lbbox = draw.textbbox((0, 0), label, font=label_font)
    lw, lh = lbbox[2] - lbbox[0], lbbox[3] - lbbox[1]
    pad = 12
    pill_w, pill_h = lw + pad * 4, lh + pad * 2
    pill_x = (SIZE_W - pill_w) / 2
    draw.rounded_rectangle(
        [pill_x, y, pill_x + pill_w, y + pill_h], radius=pill_h / 2, fill=accent
    )
    draw.text((pill_x + pad * 2, y + pad - 2), label, font=label_font, fill=(15, 15, 15))
    y += pill_h + 30

    # ---- headline ----
    headline_font = ImageFont.truetype(FONT_BOLD, 56)
    max_w = SIZE_W - pad_x * 2
    lines = _wrap_text(draw, headline, headline_font, max_w)
    while len(lines) > 4 and headline_font.size > 36:
        headline_font = ImageFont.truetype(FONT_BOLD, headline_font.size - 4)
        lines = _wrap_text(draw, headline, headline_font, max_w)
    lines = lines[:5]

    line_height = headline_font.size + 12
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        lw = bbox[2] - bbox[0]
        x = (SIZE_W - lw) / 2
        draw.text((x, y), line, font=headline_font, fill=(15, 15, 15))
        y += line_height
    y += 16

    # ---- short subheadline (from description) ----
    if description:
        sub_font = ImageFont.truetype(FONT_REGULAR, 30)
        sub_lines = _wrap_text(draw, description, sub_font, max_w)[:2]
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            lw = bbox[2] - bbox[0]
            x = (SIZE_W - lw) / 2
            draw.text((x, y), line, font=sub_font, fill=(90, 90, 90))
            y += sub_font.size + 10
        y += 20
    else:
        y += 20

    return y  # total header height used


def _draw_footer(img_canvas, draw, category, top_y):
    accent, _, _, _ = CATEGORY_STYLE.get(category, CATEGORY_STYLE["world"])

    # dark gradient at the bottom of the photo for text legibility
    grad_h = 170
    gradient = Image.new("L", (1, grad_h), 0)
    for i in range(grad_h):
        gradient.putpixel((0, i), int(200 * (i / grad_h)))
    gradient = gradient.resize((SIZE_W, grad_h))
    black_block = Image.new("RGB", (SIZE_W, grad_h), (0, 0, 0))
    img_canvas.paste(
        Image.composite(black_block, img_canvas.crop((0, SIZE_H - grad_h, SIZE_W, SIZE_H)), gradient),
        (0, SIZE_H - grad_h),
    )
    draw = ImageDraw.Draw(img_canvas)

    # date badge, bottom-left
    date_font = ImageFont.truetype(FONT_BOLD, 30)
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b").upper()
    dbbox = draw.textbbox((0, 0), date_str, font=date_font)
    dw, dh = dbbox[2] - dbbox[0], dbbox[3] - dbbox[1]
    pad = 16
    badge_w, badge_h = dw + pad * 2, dh + pad * 2
    badge_x, badge_y = 34, SIZE_H - badge_h - 34
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=8, fill=accent
    )
    draw.text((badge_x + pad, badge_y + pad - 4), date_str, font=date_font, fill=(15, 15, 15))

    # brand mark, bottom-right
    brand_font = ImageFont.truetype(FONT_BOLD, 32)
    bbbox = draw.textbbox((0, 0), BRAND_NAME, font=brand_font)
    bw = bbbox[2] - bbbox[0]
    draw.text((SIZE_W - 34 - bw, SIZE_H - 34 - (dh + 6)), BRAND_NAME, font=brand_font, fill=(255, 255, 255))


def _generate_fallback(article: dict, output_path: str) -> str:
    """Used only when no article photo is available - original gradient template, no external image."""
    category = article.get("category", "world")
    accent, label, top_color, bottom_color = CATEGORY_STYLE.get(category, CATEGORY_STYLE["world"])

    img = Image.new("RGB", (SIZE_W, SIZE_H), top_color)
    draw = ImageDraw.Draw(img)
    for y in range(SIZE_H):
        ratio = y / SIZE_H
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (SIZE_W, y)], fill=(r, g, b))

    draw.rectangle([0, 0, SIZE_W, 10], fill=accent)

    banner_font = ImageFont.truetype(FONT_BOLD, 78)
    draw.rectangle([0, 60, SIZE_W, 180], fill=(255, 255, 255))
    bbox = draw.textbbox((0, 0), "BREAKING", font=banner_font)
    tw = bbox[2] - bbox[0]
    draw.text(((SIZE_W - tw) / 2, 80), "BREAKING", font=banner_font, fill=(20, 20, 20))

    headline = article.get("title", "").strip()
    headline_font = ImageFont.truetype(FONT_BOLD, 64)
    max_w = SIZE_W - 140
    lines = _wrap_text(draw, headline, headline_font, max_w)
    while len(lines) > 6 and headline_font.size > 40:
        headline_font = ImageFont.truetype(FONT_BOLD, headline_font.size - 4)
        lines = _wrap_text(draw, headline, headline_font, max_w)

    line_height = headline_font.size + 14
    total_h = line_height * len(lines)
    start_y = (SIZE_H - total_h) / 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=headline_font)
        lw = bbox[2] - bbox[0]
        x = (SIZE_W - lw) / 2
        y = start_y + i * line_height
        draw.text((x, y), line, font=headline_font, fill=(255, 255, 255))

    date_font = ImageFont.truetype(FONT_BOLD, 28)
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y")
    draw.rectangle([0, SIZE_H - 80, SIZE_W, SIZE_H], fill=(0, 0, 0))
    draw.text((40, SIZE_H - 55), date_str, font=date_font, fill=(220, 220, 220))
    brand_font = ImageFont.truetype(FONT_BOLD, 28)
    bbbox = draw.textbbox((0, 0), BRAND_NAME, font=brand_font)
    bw = bbbox[2] - bbbox[0]
    draw.text((SIZE_W - 40 - bw, SIZE_H - 55), BRAND_NAME, font=brand_font, fill=accent)

    img.save(output_path, "PNG")
    return output_path


def generate(article: dict, output_path: str) -> str:
    category = article.get("category", "world")
    headline = article.get("title", "").strip()
    description = article.get("description", "").strip()

    photo = _download_image(article.get("image_url"))
    if photo is None:
        return _generate_fallback(article, output_path)

    canvas = Image.new("RGB", (SIZE_W, SIZE_H), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    header_h = _draw_header(draw, canvas, category, headline, description)
    header_h = min(header_h, SIZE_H - 300)  # always leave room for the photo

    photo_area_h = SIZE_H - int(header_h)
    photo_cropped = _cover_crop(photo, SIZE_W, photo_area_h)
    canvas.paste(photo_cropped, (0, int(header_h)))

    _draw_footer(canvas, draw, category, int(header_h))

    canvas.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    sample = {
        "title": "India Announces New Metro Line Connecting Major Tech Hubs",
        "description": "The government unveiled plans for a new metro corridor to ease traffic congestion.",
        "category": "india",
        "image_url": None,  # no network in this sandbox test -> exercises fallback path
    }
    generate(sample, "/tmp/sample_fallback.png")
    print("saved /tmp/sample_fallback.png")
