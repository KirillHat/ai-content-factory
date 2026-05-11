"""Starter AI card generator (V2 Stats Card layout, locked-in design).

Asymmetric: name+desc left, logo right (rounded white card).
Outcome stat row (3 cards) with hours/money/price.
No edition numbering. Big readable type via Avenir Next.

Usage:
  generate_card(name='ChatGPT', domain='openai.com',
                description='AI-ассистент для текстов, идей',
                pricing='Free → $20/мес',
                hours_saved='12 ч/нед', money_saved='$1.5K/мес',
                output='/tmp/card.png')

  generate_stack_card(name='Салон под ключ', niche_label='САЛОН',
                      tool_domains=[('Canva','canva.com'), ('Make','make.com')],
                      description='...', pricing='$35/мес',
                      hours_saved='12 ч/нед', money_saved='$1.5K/мес',
                      output='/tmp/stack.png')
"""
import os
import urllib.request
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Optional SVG renderer for gilbarbara/logos fallback (reliable for known brands).
# Brew cairo isn't on default search path on Apple Silicon — patch find_library before import.
try:
    import ctypes.util as _cu
    _orig_find = _cu.find_library
    _BREW_CAIRO = "/opt/homebrew/lib/libcairo.2.dylib"
    if os.path.exists(_BREW_CAIRO):
        _cu.find_library = lambda n: _BREW_CAIRO if "cairo" in n.lower() else _orig_find(n)
    import cairosvg as _cairosvg
    _SVG_OK = True
except Exception:
    _SVG_OK = False

# Canvas
WIDTH, HEIGHT = 1080, 1350

# Brand palette
BG_COLOR = (250, 248, 244)         # warm light cream
NAVY = (28, 38, 64)                # primary text
ACCENT_BLUE = (66, 102, 178)       # secondary accent
SOFT_GRAY = (105, 100, 95)         # warm gray — matches cream BG (was cool 95,105,130)
TINY_GRAY = (155, 150, 140)        # warm tiny gray
CARD_WHITE = (255, 255, 255)
CARD_SHADOW = (220, 220, 230)

# Fonts (Avenir Next gives the cleanest cyrillic + latin balance)
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
CYR_FALLBACK = "/Library/Fonts/Arial Unicode.ttf"


def load_font(path, size, idx=0):
    try:
        return ImageFont.truetype(path, size, index=idx)
    except Exception:
        try:
            return ImageFont.truetype(CYR_FALLBACK, size)
        except Exception:
            return ImageFont.load_default()


def _try_gilbarbara_svg(domain, size):
    """gilbarbara/logos has high-quality SVG icons for thousands of brands.
    Try {slug}-icon.svg first (just the mark), fall back to {slug}.svg (wordmark).
    Returns RGBA PIL Image or None.
    """
    if not _SVG_OK:
        return None
    slug = domain.split(".")[0].lower()
    # Manual aliases for tools whose domain != logo slug
    aliases = {
        "openai": "openai",
        "chatgpt": "openai",
        "notion": "notion",
        "fireflies": "fireflies",
    }
    candidates = [aliases.get(slug, slug)]
    if slug not in candidates:
        candidates.append(slug)
    for s in candidates:
        for variant in (f"{s}-icon.svg", f"{s}.svg"):
            url = f"https://cdn.jsdelivr.net/gh/gilbarbara/logos/logos/{variant}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                svg = urllib.request.urlopen(req, timeout=10).read()
                if not svg.lstrip().startswith(b"<"):
                    continue
                png_bytes = _cairosvg.svg2png(bytestring=svg, output_width=size)
                img = Image.open(BytesIO(png_bytes)).convert("RGBA")
                # Skip wordmark logos (very wide aspect): only square-ish OK as icon
                if img.size[0] > img.size[1] * 1.6:
                    continue
                return img
            except Exception:
                continue
    return None


# Hardcoded high-res logo URLs (1024x1024 from App Store) — most reliable for known tools.
# Use full domain keys so lookup is direct.
KNOWN_LOGOS = {
    'capcut.com':    'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/d9/77/07/d97707ba-5fca-f0cd-edc5-c18169a180af/AppIcon-0-0-1x_U007emarketing-0-8-0-85-220.png/1024x1024bb.jpg',
    'openai.com':    'https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/2b/9d/12/2b9d12b1-5337-56a4-463b-ad977809a336/AppIcon-0-0-1x_U007epad-0-0-0-1-0-P3-85-220.png/1024x1024bb.jpg',
    'notion.com':    'https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/b9/79/3e/b9793e81-1ed4-e213-9661-25bae8124748/AppIconProd-0-0-1x_U007epad-0-0-0-1-0-0-P3-85-220.png/1024x1024bb.jpg',
    'canva.com':     'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/37/bd/b5/37bdb5a5-1d36-fed0-7e55-80c2f67fe901/AppIcon-0-0-1x_U007epad-0-11-0-85-220.png/1024x1024bb.jpg',
    'grammarly.com': 'https://is1-ssl.mzstatic.com/image/thumb/Purple221/v4/82/3f/fc/823ffc16-2235-39bf-73f5-fa175fcf2307/AppIcon-0-0-1x_U007epad-0-1-sRGB-85-220.png/1024x1024bb.jpg',
    'fireflies.ai':  'https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/0d/4a/17/0d4a179a-9c54-173d-3843-31a8794055c6/AppIcon-0-0-1x_U007epad-0-1-85-220.png/1024x1024bb.jpg',
    'make.com':      'https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/33/79/3e/33793e73-366d-1a71-2223-5f28869b981a/AppIcon-0-0-1x_U007emarketing-0-6-0-sRGB-85-220.png/1024x1024bb.jpg',
}


def _try_known_logo(domain):
    """Direct fetch from hand-curated 1024px App Store URLs. Returns RGBA Image or None."""
    url = KNOWN_LOGOS.get(domain.lower())
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AppleWebKit/605.1.15"})
        data = urllib.request.urlopen(req, timeout=15).read()
        img = Image.open(BytesIO(data)).convert("RGBA")
        return img
    except Exception:
        return None


def _trim_logo(img):
    """Crop transparent padding from logo so it fills its container consistently.

    Source SVGs/PNGs have varying internal whitespace — Grammarly fills 100%,
    CapCut has 30%+ padding inside the artboard. This normalizes them.
    """
    if img.mode != "RGBA":
        return img
    bbox = img.getbbox()  # alpha-aware tight bounding box
    if not bbox:
        return img
    # Square-pad the trim so non-square logos don't squash on resize
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    side = max(w, h)
    nx = max(0, x0 - (side - w) // 2)
    ny = max(0, y0 - (side - h) // 2)
    nx2 = min(img.size[0], nx + side)
    ny2 = min(img.size[1], ny + side)
    return img.crop((nx, ny, nx2, ny2))


def fetch_logo(domain, size=512):
    """Try multiple sources for real brand logo. Returns RGBA PIL Image.

    Priority:
    1. gilbarbara/logos SVG — transparent bg, scalable, no iOS app frame
    2. KNOWN_LOGOS App Store 1024px — high-res but has iOS rounded-square bg
    3. unavatar.io — broad coverage, rate-limits
    4. Google FaviconV2, DuckDuckGo — small, last resort
    """
    # 1. SVG from gilbarbara (cleanest)
    svg_logo = _try_gilbarbara_svg(domain, size)
    if svg_logo is not None:
        return svg_logo
    # 2. Hardcoded 1024x1024 from App Store
    known = _try_known_logo(domain)
    if known is not None:
        return known
    candidates = [
        f"https://unavatar.io/{domain}?fallback=false",
        f"https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=https://{domain}&size=128",
        f"https://icons.duckduckgo.com/ip3/{domain}.ico",
    ]
    last_err = None
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AppleWebKit/605.1.15"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
            if len(data) < 500:
                continue
            img = Image.open(BytesIO(data)).convert("RGBA")
            # Skip if obviously tiny / fallback (< 64px is usually error)
            if img.size[0] < 64:
                continue
            # Upscale carefully if needed — multi-step for cleaner result
            target = max(size, img.size[0])
            while img.size[0] < target:
                next_step = min(img.size[0] * 2, target)
                img = img.resize((next_step, next_step), Image.LANCZOS)
            if img.size[0] != target:
                img = img.resize((target, target), Image.LANCZOS)
            # Sharpen edges (UnsharpMask)
            img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=140, threshold=2))
            return img
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"No logo for {domain}: {last_err}")


def text_w(draw, txt, f):
    b = draw.textbbox((0, 0), txt, font=f)
    return b[2] - b[0]


def text_h(draw, txt, f):
    b = draw.textbbox((0, 0), txt, font=f)
    return b[3] - b[1]


def round_rect(draw, xy, radius, **kw):
    draw.rounded_rectangle(xy, radius=radius, **kw)


def wrap_text(text, font, max_width, draw):
    words = text.split()
    lines, current = [], []
    for w in words:
        test = " ".join(current + [w])
        if text_w(draw, test, font) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_brand_header(draw, side="solo"):
    """Top-left brand mark only (no edition number)."""
    f_brand = load_font(AVENIR, 32, idx=2)  # Demi
    draw.text((80, 70), "Starter AI", font=f_brand, fill=NAVY)


def _safe_pricing(text):
    """Replace glyphs Avenir doesn't render (→ etc) with safe alternatives."""
    return text.replace("→", "·").replace("⟶", "·")


def _paste_shadow(img, x, y, w, h, radius=24, offset=6, blur=12, alpha=22):
    """Soft drop-shadow under a rounded rect — gives depth to white cards on cream."""
    pad = blur * 3
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    round_rect(ld, (pad, pad, pad + w, pad + h), radius=radius, fill=(0, 0, 0, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    img.paste(layer, (x - pad + offset // 2, y - pad + offset), layer)


def _stat_card(draw, x, y, w, h, big_value, small_label, accent=NAVY):
    """Stat card — value+label block vertically centered."""
    big_value = _safe_pricing(big_value)
    # Card body (shadow drawn separately by caller, before draw)
    round_rect(draw, (x, y, x + w, y + h), radius=24, fill=CARD_WHITE)

    # Pick value font size that fits, allow 2-line wrap
    f_lbl = load_font(AVENIR, 22, idx=7)
    inner_w = w - 48
    f_big = load_font(AVENIR, 56, idx=2)
    for sz in [56, 50, 44, 38, 34, 30]:
        f_big = load_font(AVENIR, sz, idx=2)
        if text_w(draw, big_value, f_big) <= inner_w:
            break
    lines = [big_value]
    if text_w(draw, big_value, f_big) > inner_w:
        wrapped = wrap_text(big_value, f_big, max_width=inner_w, draw=draw)[:2]
        if wrapped:
            lines = wrapped
    f_lbl_lines = wrap_text(small_label, f_lbl, max_width=w - 56, draw=draw)[:2]

    # Block: label + 14px gap + value lines
    label_h = 28 * len(f_lbl_lines)
    value_h = f_big.size * len(lines) + (len(lines) - 1) * 6
    block_h = label_h + 16 + value_h
    block_y = y + (h - block_h) // 2

    for i, ln in enumerate(f_lbl_lines):
        draw.text((x + 28, block_y + i * 28), ln, font=f_lbl, fill=TINY_GRAY)
    for i, ln in enumerate(lines):
        draw.text((x + 28, block_y + label_h + 16 + i * (f_big.size + 6)), ln, font=f_big, fill=NAVY)


def generate_card(name, domain, description, pricing,
                  output, *, hours_saved=None, setup_time=None, money_saved=None):
    """Single tool card with outcome stat row.

    Universal metrics (no money — varies by country):
      - hours_saved (e.g. '12 ч/нед')
      - setup_time  (e.g. 'Setup 1 час')
      - pricing     (always shown)
    money_saved kept for backward-compat but ignored by default render.
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(img)

    # Logo card (right, vertically aligned with name) — with soft drop shadow
    card_w = 380
    card_h = 380
    card_x = WIDTH - 80 - card_w
    card_y = 140
    _paste_shadow(img, card_x, card_y, card_w, card_h, radius=32)
    round_rect(d, (card_x, card_y, card_x + card_w, card_y + card_h), radius=32, fill=CARD_WHITE)
    try:
        logo = fetch_logo(domain, size=512)
        logo = _trim_logo(logo)  # remove internal whitespace for consistent visual mass
        # Fit to 75% of card (was 80%) — guaranteed breathing room, no edge bleed
        target = int(min(card_w, card_h) * 0.75)
        logo = logo.resize((target, target), Image.LANCZOS)
        lx = card_x + (card_w - target) // 2
        ly = card_y + (card_h - target) // 2
        img.paste(logo, (lx, ly), logo)
    except Exception:
        target = int(min(card_w, card_h) * 0.55)
        ex = card_x + (card_w - target) // 2
        ey = card_y + (card_h - target) // 2
        d.ellipse((ex, ey, ex + target, ey + target), fill=ACCENT_BLUE)

    # Name — vertically centered with logo card (baseline-fit)
    fn = load_font(AVENIR, 140, idx=2)  # Demi (was 150 → 140 for better ratio with description)
    name_max_w = card_x - 100
    while text_w(d, name, fn) > name_max_w and fn.size > 80:
        fn = load_font(AVENIR, fn.size - 10, idx=2)
    name_bbox = d.textbbox((0, 0), name, font=fn)
    name_h = name_bbox[3] - name_bbox[1]
    # Name + domain block centered vertically with logo card
    f_dom = load_font(AVENIR, 28, idx=7)
    domain_label = domain
    block_h = name_h + 18 + f_dom.size
    block_y = card_y + (card_h - block_h) // 2 - name_bbox[1]
    d.text((80, block_y), name, font=fn, fill=NAVY)
    d.text((80 + 6, block_y + name_h + 18 + name_bbox[1]), domain_label, font=f_dom, fill=TINY_GRAY)

    # Description — Avenir Next Regular, 44pt (was 40) — better ratio with 140pt headline
    fd = load_font(AVENIR, 44, idx=7)
    LINE_H = 60
    desc_y_top = card_y + card_h + 50
    description = _safe_pricing(description)
    desc_max_w = WIDTH - 160
    desc_lines = wrap_text(description, fd, max_width=desc_max_w, draw=d)
    cur_y = desc_y_top
    for ln in desc_lines:
        d.text((80, cur_y), ln, font=fd, fill=SOFT_GRAY)
        cur_y += LINE_H

    # Subtle divider between description and stat row
    divider_y = 850
    d.line((80, divider_y, WIDTH - 80, divider_y), fill=(225, 218, 205), width=2)

    # Stat row — short uniform Russian labels, pinned vertical position
    stat_items = []
    if hours_saved:
        stat_items.append((hours_saved, "экономия/нед"))
    if setup_time:
        stat_items.append((setup_time, "запуск"))
    stat_items.append((pricing, "цена"))
    while len(stat_items) < 3:
        stat_items.insert(0, ("Free", "тариф"))
    stat_items = stat_items[:3]

    stat_card_w = (WIDTH - 160 - 40) // 3
    stat_card_h = 220
    stat_y = 890
    for i, (big, small) in enumerate(stat_items):
        sx = 80 + i * (stat_card_w + 20)
        _paste_shadow(img, sx, stat_y, stat_card_w, stat_card_h, radius=24, offset=4, blur=10, alpha=18)
        _stat_card(d, sx, stat_y, stat_card_w, stat_card_h, big, small)

    # Bottom strip — compact + better hierarchy (tagline 20pt vs 24pt)
    strip_top = HEIGHT - 180
    d.rectangle((0, strip_top, WIDTH, HEIGHT), fill=NAVY)
    f_tag = load_font(AVENIR, 40, idx=2)
    tag_text = "Starter AI"
    tw = text_w(d, tag_text, f_tag)
    f_sub = load_font(AVENIR, 20, idx=7)  # was 24 → 20 for stronger hierarchy
    sub_text = "Simple AI tools for small business growth"
    sw = text_w(d, sub_text, f_sub)
    block_h = f_tag.size + 14 + f_sub.size
    block_y = strip_top + (HEIGHT - strip_top - block_h) // 2
    d.text(((WIDTH - tw) // 2, block_y), tag_text, font=f_tag, fill=(255, 255, 255))
    d.text(((WIDTH - sw) // 2, block_y + f_tag.size + 14), sub_text, font=f_sub, fill=(170, 185, 215))

    img.save(output, "PNG", optimize=True)
    return output


def generate_stack_card(name, niche_label, tool_domains, description, pricing,
                         output, *, hours_saved=None, setup_time=None, money_saved=None):
    """Stack card: niche badge + multiple tool logos + name + outcome stats.

    tool_domains: list of (tool_name, domain) tuples, max 4
    """
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(img)

    _draw_brand_header(d)

    # Niche badge top-right
    f_badge = load_font(AVENIR, 26, idx=2)
    bbox = d.textbbox((0, 0), niche_label, font=f_badge)
    bw = bbox[2] - bbox[0] + 40
    bh = bbox[3] - bbox[1] + 22
    bx, by = WIDTH - 80 - bw, 70
    round_rect(d, (bx, by, bx + bw, by + bh), radius=14, fill=ACCENT_BLUE)
    d.text((bx + 20, by + 8), niche_label, font=f_badge, fill=(255, 255, 255))

    # Logo grid (3-4 logos in white card)
    n = len(tool_domains)
    logo_size = 160 if n >= 4 else 200
    gap = 50
    total_w = logo_size * n + gap * (n - 1)
    grid_card_pad = 40
    card_w = total_w + grid_card_pad * 2
    card_h = logo_size + grid_card_pad * 2
    card_x = (WIDTH - card_w) // 2
    card_y = 200
    round_rect(d, (card_x, card_y, card_x + card_w, card_y + card_h), radius=32, fill=CARD_WHITE)

    for i, (_, domain) in enumerate(tool_domains):
        try:
            logo = fetch_logo(domain, size=logo_size)
            logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
            x = card_x + grid_card_pad + i * (logo_size + gap)
            img.paste(logo, (x, card_y + grid_card_pad), logo)
        except Exception:
            x = card_x + grid_card_pad + i * (logo_size + gap)
            d.ellipse((x, card_y + grid_card_pad, x + logo_size, card_y + grid_card_pad + logo_size),
                      fill=ACCENT_BLUE)

    # "+" connectors between logos
    f_plus = load_font(AVENIR, 56, idx=2)
    for i in range(n - 1):
        cx = card_x + grid_card_pad + (i + 1) * logo_size + i * gap + gap // 2
        cy = card_y + grid_card_pad + logo_size // 2 - 30
        d.text((cx - 12, cy), "+", font=f_plus, fill=TINY_GRAY)

    # Stack name (large, centered)
    name_y = card_y + card_h + 60
    fn = load_font(AVENIR, 96, idx=2)
    while text_w(d, name, fn) > WIDTH - 160 and fn.size > 56:
        fn = load_font(AVENIR, fn.size - 8, idx=2)
    tw = text_w(d, name, fn)
    d.text(((WIDTH - tw) // 2, name_y), name, font=fn, fill=NAVY)

    # Tool list compact
    tools_text = "  ·  ".join(t[0] for t in tool_domains)
    f_tools = load_font(AVENIR, 28, idx=0)
    tw = text_w(d, tools_text, f_tools)
    d.text(((WIDTH - tw) // 2, name_y + 110), tools_text, font=f_tools, fill=TINY_GRAY)

    # Description (1 line, centered)
    fd = load_font(AVENIR, 32, idx=0)
    desc_lines = wrap_text(description, fd, max_width=WIDTH - 160, draw=d)[:1]
    for ln in desc_lines:
        tw = text_w(d, ln, fd)
        d.text(((WIDTH - tw) // 2, name_y + 175), ln, font=fd, fill=SOFT_GRAY)

    # Stat row — universal only (no $ savings)
    stat_items = []
    if hours_saved:
        stat_items.append((hours_saved, "экономии в неделю"))
    if setup_time:
        stat_items.append((setup_time, "на запуск"))
    stat_items.append((pricing, "цена стека"))
    while len(stat_items) < 3:
        stat_items.insert(0, ("—", "—"))
    stat_items = stat_items[:3]

    stat_y = HEIGHT - 360
    stat_card_w = (WIDTH - 160 - 40) // 3
    stat_card_h = 200
    for i, (big, small) in enumerate(stat_items):
        sx = 80 + i * (stat_card_w + 20)
        _stat_card(d, sx, stat_y, stat_card_w, stat_card_h, big, small)

    # CTA bottom — brand identifier (set BRAND_NAME / BRAND_TAGLINE in env)
    from app.config import BRAND_NAME, BRAND_TAGLINE, TELEGRAM_CHANNEL_USERNAME
    d.rectangle((0, HEIGHT - 140, WIDTH, HEIGHT), fill=NAVY)
    f_cta = load_font(AVENIR, 36, idx=2)
    cta_text = f"Follow {TELEGRAM_CHANNEL_USERNAME}" if TELEGRAM_CHANNEL_USERNAME else BRAND_NAME
    tw = text_w(d, cta_text, f_cta)
    d.text(((WIDTH - tw) // 2, HEIGHT - 100), cta_text, font=f_cta, fill=(255, 255, 255))
    f_cta2 = load_font(AVENIR, 22, idx=0)
    tw = text_w(d, BRAND_TAGLINE, f_cta2)
    d.text(((WIDTH - tw) // 2, HEIGHT - 50), BRAND_TAGLINE, font=f_cta2, fill=(180, 195, 220))

    img.save(output, "PNG", optimize=True)
    return output


if __name__ == "__main__":
    generate_card(
        name="ChatGPT",
        domain="openai.com",
        description="AI-ассистент для текстов, идей и рутинных задач",
        pricing="Free → $20/мес",
        hours_saved="12 ч/нед",
        setup_time="30 мин",
        output="/tmp/card_chatgpt.png",
    )
    print("Saved /tmp/card_chatgpt.png")
