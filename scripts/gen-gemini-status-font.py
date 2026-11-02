#!/usr/bin/env python3
"""Bake Noto Sans CJK SC glyphs into initramfs/gemini-status-font.h."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/usr/lib/python3/dist-packages")
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "initramfs", "gemini-status-font.h")
SRC = os.path.join(ROOT, "initramfs", "gemini-status.c")
PREVIEW = os.path.join(ROOT, "out", "gemini-status-font-preview.png")
TTC = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

UI = "Armbian Mi 5 Wi-Fi CPU GPU Kryo Adreno MHz Connected Network Password Signal"

# Additional glyphs preserve international network-name rendering.
COMMON_CODEPOINTS = (
    0x4e00, 0x4e07, 0x4e09, 0x4e0a, 0x4e0b, 0x4e0d, 0x4e0e, 0x4e2a, 0x4e2d, 0x4e3a, 0x4e3b, 0x4e48,
    0x4e4b, 0x4e5f, 0x4e86, 0x4e8b, 0x4e8c, 0x4e8e, 0x4e9b, 0x4eae, 0x4eba, 0x4ec0, 0x4ece, 0x4ed6,
    0x4ee5, 0x4eec, 0x4efb, 0x4f1a, 0x4f20, 0x4f4d, 0x4f53, 0x4f5c, 0x4f60, 0x4fdd, 0x4fe1, 0x5019,
    0x505a, 0x5145, 0x514b, 0x5165, 0x5168, 0x516c, 0x5173, 0x5176, 0x5185, 0x518d, 0x519b, 0x51e0,
    0x51fa, 0x5206, 0x5220, 0x5229, 0x5230, 0x5236, 0x5237, 0x524d, 0x529b, 0x529f, 0x52a0, 0x52a8,
    0x5316, 0x5317, 0x5339, 0x533a, 0x5341, 0x5360, 0x5361, 0x539f, 0x53bb, 0x53c8, 0x53cd, 0x53d1,
    0x53d6, 0x53e3, 0x53ea, 0x53ef, 0x53f7, 0x5404, 0x540c, 0x540e, 0x542f, 0x547d, 0x548c, 0x5668,
    0x56de, 0x56e0, 0x56fd, 0x5728, 0x5730, 0x573a, 0x5740, 0x5904, 0x5907, 0x5916, 0x591a, 0x5927,
    0x5929, 0x5931, 0x5934, 0x5973, 0x597d, 0x5982, 0x5b50, 0x5b58, 0x5b66, 0x5b89, 0x5b8c, 0x5b9a,
    0x5b9e, 0x5bb6, 0x5bc6, 0x5bf9, 0x5c06, 0x5c0f, 0x5c1a, 0x5c31, 0x5c4f, 0x5de5, 0x5df2, 0x5e02,
    0x5e55, 0x5e73, 0x5e74, 0x5e76, 0x5ea6, 0x5f00, 0x5f3a, 0x5f53, 0x5f88, 0x5f97, 0x5fc3, 0x5fd8,
    0x6001, 0x6027, 0x606f, 0x60c5, 0x610f, 0x611f, 0x6210, 0x6211, 0x6216, 0x6237, 0x6240, 0x624b,
    0x6253, 0x626b, 0x627e, 0x62e9, 0x62ff, 0x6307, 0x6309, 0x63a5, 0x63cf, 0x63d0, 0x653e, 0x6570,
    0x6587, 0x65b0, 0x65b9, 0x65e0, 0x65e5, 0x65f6, 0x662f, 0x663e, 0x6709, 0x672a, 0x673a, 0x6765,
    0x67e5, 0x68c0, 0x6b21, 0x6b63, 0x6b64, 0x6bb5, 0x6c11, 0x6c14, 0x6c34, 0x6c60, 0x6ca1, 0x6cd5,
    0x6d88, 0x6e90, 0x70b9, 0x7136, 0x72b6, 0x7387, 0x73b0, 0x7406, 0x751f, 0x7528, 0x7531, 0x7535,
    0x7684, 0x76f8, 0x770b, 0x7740, 0x77e5, 0x77ed, 0x7801, 0x786e, 0x793a, 0x793e, 0x79cd, 0x79d1,
    0x79d2, 0x7a0d, 0x7a7a, 0x7b2c, 0x7b49, 0x7ebf, 0x7ecf, 0x7ed9, 0x7edc, 0x7eea, 0x7f51, 0x7f8e,
    0x8005, 0x800c, 0x8017, 0x80fd, 0x81ea, 0x85cf, 0x884c, 0x8868, 0x897f, 0x8981, 0x89c1, 0x89e3,
    0x8ba4, 0x8bb0, 0x8bbe, 0x8bd5, 0x8bdd, 0x8be6, 0x8bf4, 0x8bf7, 0x8d25, 0x8d44, 0x8d77, 0x8d85,
    0x8eab, 0x8f7d, 0x8f93, 0x8fc7, 0x8fd0, 0x8fd4, 0x8fd8, 0x8fd9, 0x8fdb, 0x8fde, 0x9009, 0x9053,
    0x90a3, 0x90e8, 0x90fd, 0x914d, 0x91cc, 0x91cd, 0x91cf, 0x9501, 0x952e, 0x95e8, 0x95ed, 0x95f2,
    0x95f4, 0x9664, 0x9690, 0x9700, 0x9762, 0x97f3, 0x9879, 0x9891, 0x9898, 0x9ad8,
)
COMMON = "".join(chr(cp) for cp in COMMON_CODEPOINTS)

ASCII = "".join(chr(i) for i in range(32, 127))
EXTRA = "…·—–°%‰℃±×÷≈≠≤≥•●○★☆【】「」『』（）”“‘’、，。！？：；"


def cps():
    s = set(UI + COMMON + ASCII + EXTRA)
    try:
        src = open(SRC, encoding="utf-8").read()
        s.update(c for c in src if ord(c) > 127)
    except OSError:
        pass
    return sorted(ord(c) for c in s if c not in "\n")


def raster(font: ImageFont.FreeTypeFont, cp: int, px: int, ascent: int, descent: int):
    ch = chr(cp)
    adv = int(round(font.getlength(ch))) or (px if cp > 127 else max(px // 3, 1))
    if ch == " ":
        return {
            "cp": cp,
            "w": 0,
            "h": 0,
            "adv": adv,
            "xoff": 0,
            "yoff": 0,
            "bits": b"",
        }
    pad = 8
    line_top = pad
    baseline = pad + ascent
    canvas_w = max(px * 3, adv + pad * 2, 16)
    canvas_h = pad + ascent + descent + pad
    img = Image.new("L", (canvas_w, canvas_h), 0)
    # Left-baseline so '.' '-' '%' sit on the same line as letters.
    ImageDraw.Draw(img).text((pad, baseline), ch, font=font, fill=255, anchor="ls")
    data = img.tobytes()
    w = canvas_w
    ys = [y for y in range(canvas_h) if any(data[y * w + x] > 12 for x in range(w))]
    xs = [x for x in range(w) if any(data[y * w + x] > 12 for y in range(canvas_h))]
    if not xs or not ys:
        return {
            "cp": cp,
            "w": 0,
            "h": 0,
            "adv": adv,
            "xoff": 0,
            "yoff": 0,
            "bits": b"",
        }
    nx0, nx1 = xs[0], xs[-1] + 1
    ny0, ny1 = ys[0], ys[-1] + 1
    nw, nh = nx1 - nx0, ny1 - ny0
    bits = bytes(data[y * w + x] for y in range(ny0, ny1) for x in range(nx0, nx1))
    return {
        "cp": cp,
        "w": nw,
        "h": nh,
        "adv": adv,
        "xoff": nx0 - pad,
        "yoff": ny0 - line_top,
        "bits": bits,
    }


def dump_face(name: str, px: int, index: int, codes):
    font = ImageFont.truetype(TTC, px, index=index)
    ascent, descent = font.getmetrics()
    glyphs = []
    blob = bytearray()
    for cp in codes:
        g = raster(font, cp, px, ascent, descent)
        off = len(blob)
        blob.extend(g["bits"])
        glyphs.append((g, off))
    lines = [f"static const uint8_t {name}_bits[] = {{"]
    row = []
    for i, b in enumerate(blob):
        row.append(str(b))
        if len(row) == 16:
            lines.append("\t" + ",".join(row) + ",")
            row = []
    if row:
        lines.append("\t" + ",".join(row) + ",")
    lines.append("};")
    lines.append(f"static const struct gs_glyph {name}_glyphs[] = {{")
    for g, off in glyphs:
        lines.append(
            f"\t{{ {g['cp']}, {g['w']}, {g['h']}, {g['adv']}, {g['xoff']}, {g['yoff']}, {off} }},"
        )
    lines.append("};")
    lines.append(
        f"static const struct gs_font {name} = {{ {px}, {ascent}, {descent}, "
        f"{len(glyphs)}, {name}_glyphs, {name}_bits }};"
    )
    return "\n".join(lines) + "\n", glyphs, bytes(blob), px


def blit(img: Image.Image, font_px, glyphs, blob, x, y, text, fill):
    lookup = {g["cp"]: (g, off) for (g, off) in glyphs}
    px = x
    for ch in text:
        cp = ord(ch)
        if cp not in lookup:
            px += font_px // 2
            continue
        g, off = lookup[cp]
        if g["w"] and g["h"]:
            tile = Image.frombytes("L", (g["w"], g["h"]), blob[off : off + g["w"] * g["h"]])
            pos = (px + g["xoff"], y + g["yoff"])
            col = Image.new("RGBA", tile.size, fill + (0,))
            col.putalpha(tile)
            img.alpha_composite(col, pos)
        px += g["adv"]


def preview(faces):
    img = Image.new("RGBA", (1080, 900), (11, 14, 20, 255))
    y = 40
    samples = [
        ("title", "XiaoMi 5"),
        ("body", "Ubuntu 26.04  ·  gemini"),
        ("title", "Wi-Fi"),
        ("num", "37%  0%  12%"),
        ("body", "Power sleeps the display · Found 3 networks"),
        ("body", "Connection failed; check the password"),
    ]
    for name, s in samples:
        glyphs, blob, px = faces[name]
        blit(img, px, glyphs, blob, 48, y, s, (245, 248, 252))
        y += px + 18
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    img.convert("RGB").save(PREVIEW)
    print("preview", PREVIEW)


def main():
    codes = cps()
    body = dump_face("font_body", 32, 2, codes)
    title = dump_face("font_title", 44, 2, codes)
    num = dump_face("font_num", 60, 2, sorted(ord(c) for c in "0123456789%./:-"))
    parts = [
        "/* SPDX-License-Identifier: GPL-2.0-only */",
        "/* Generated by scripts/gen-gemini-status-font.py — do not edit. */",
        "#ifndef GEMINI_STATUS_FONT_H",
        "#define GEMINI_STATUS_FONT_H",
        "#include <stdint.h>",
        "struct gs_glyph {",
        "\tuint32_t cp;",
        "\tuint16_t w, h, adv;",
        "\tint16_t xoff, yoff;",
        "\tuint32_t off;",
        "};",
        "struct gs_font {",
        "\tint px, ascent, descent, n;",
        "\tconst struct gs_glyph *g;",
        "\tconst uint8_t *bits;",
        "};",
        "",
        body[0],
        title[0],
        num[0],
        "#endif",
        "",
    ]
    with open(OUT, "w") as f:
        f.write("\n".join(parts))
    faces = {
        "body": (body[1], body[2], body[3]),
        "title": (title[1], title[2], title[3]),
        "num": (num[1], num[2], num[3]),
    }
    preview(faces)
    # sanity: CJK must be near font size, not 10px slivers
    g_wei = next(g for g, _ in title[1] if g["cp"] == 0x672A)
    g_w = next(g for g, _ in title[1] if g["cp"] == ord("W"))
    g_dot = next(g for g, _ in body[1] if g["cp"] == ord("."))
    g_pct = next(g for g, _ in num[1] if g["cp"] == ord("%"))
    g_hy = next(g for g, _ in title[1] if g["cp"] == ord("-"))
    print(f"wrote {OUT}")
    print(f"U+672A {g_wei['w']}x{g_wei['h']} adv={g_wei['adv']} yoff={g_wei['yoff']}")
    print(f"W  {g_w['w']}x{g_w['h']} adv={g_w['adv']} yoff={g_w['yoff']}")
    print(f".  {g_dot['w']}x{g_dot['h']} yoff={g_dot['yoff']}")
    print(f"%  {g_pct['w']}x{g_pct['h']} yoff={g_pct['yoff']}")
    print(f"-  {g_hy['w']}x{g_hy['h']} yoff={g_hy['yoff']}")
    if g_wei["h"] < 28 or g_w["h"] < 20:
        raise SystemExit("glyph too small — bake still clipped")
    if g_dot["yoff"] < 16:
        raise SystemExit("period yoff too small — still sitting on the line top")
    cps_num = [g["cp"] for g, _ in num[1]]
    if cps_num != sorted(cps_num):
        raise SystemExit("font_num not sorted; binary search will miss %")


if __name__ == "__main__":
    main()
