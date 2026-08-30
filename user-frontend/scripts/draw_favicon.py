"""手绘 favicon 光栅化器：把与 logo.svg 等价的几何描述渲染成 PNG（预览）与多尺寸 ICO。

纯标准库（math/struct/zlib），8 倍超采样抗锯齿；
ICO 采用 PNG-in-ICO（Vista+ 与全部现代浏览器支持）。
"""
import math
import struct
import zlib
from pathlib import Path

# ── 设计系统取色 ──
BG = (0x4F, 0x46, 0xE5)      # accent indigo-600
WHITE = (0xFF, 0xFF, 0xFF)
MINT = (0x6E, 0xE7, 0xB7)    # ok 强调亮版

CX, CY = 16.0, 17.0          # 画布逻辑 32×32
HUB_R = 3.6
SAT_R = 2.0
MINT_SAT_R = 2.3
LINE_W = 2.0
LINE_ALPHA = 1.0

SATELLITES = [
    (16.0, 7.5, MINT_SAT_R, MINT),
    (25.0, 14.1, SAT_R, WHITE),
    (21.6, 24.7, SAT_R, WHITE),
    (10.4, 24.7, SAT_R, WHITE),
    (7.0, 14.1, SAT_R, WHITE),
]
LINES_TO = [(x, y) for x, y, _, _ in SATELLITES]


def in_rounded_rect(x, y, cx=16.0, cy=16.0, w=32.0, h=32.0, r=7.0):
    dx = abs(x - cx) - (w / 2 - r)
    dy = abs(y - cy) - (h / 2 - r)
    if dx <= 0 or dy <= 0:
        return abs(x - cx) <= w / 2 and abs(y - cy) <= h / 2
    return dx * dx + dy * dy <= r * r


def in_circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def dist_to_seg(x, y, x1, y1, x2, y2):
    vx, vy = x2 - x1, y2 - y1
    wx, wy = x - x1, y - y1
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / (vx * vx + vy * vy)))
    px, py = x1 + t * vx, y1 + t * vy
    return math.hypot(x - px, y - py)


def blend(base, overlay, alpha):
    return tuple(round(bc * (1 - alpha) + oc * alpha) for bc, oc in zip(base, overlay))


def sample(x, y):
    """单个逻辑坐标点的 RGBA 颜色。"""
    if not in_rounded_rect(x, y):
        return (0, 0, 0, 0)
    r, g, b = BG
    for lx, ly in LINES_TO:
        if dist_to_seg(x, y, CX, CY, lx, ly) <= LINE_W / 2:
            r, g, b = blend((r, g, b), WHITE, LINE_ALPHA)
    for sx, sy, sr, color in SATELLITES:
        if in_circle(x, y, sx, sy, sr):
            r, g, b = color
    if in_circle(x, y, CX, CY, HUB_R):
        r, g, b = WHITE
    return (r, g, b, 255)


def render(size, ss=8):
    """渲染 size×size 的 RGBA 像素数组（8 倍超采样抗锯齿）。"""
    grid = []
    step = 32.0 / size
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    x = (px + (sx + 0.5) / ss) * step
                    y = (py + (sy + 0.5) / ss) * step
                    c = sample(x, y)
                    acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]; acc[3] += c[3]
            n = ss * ss
            row.append(tuple(v // n for v in acc))
        grid.append(row)
    return grid


def grid_to_png(grid):
    size = len(grid)
    raw = b""
    for row in grid:
        raw += b"\x00" + b"".join(struct.pack("4B", *px) for px in row)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def build_ico(pngs):
    """PNG-in-ICO：多尺寸打包。"""
    entries = []
    images = b""
    for size in sorted(pngs, reverse=True):
        data = pngs[size]
        entries.append(struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), len(images)))
        images += data
    return struct.pack("<HHH", 0, 1, len(entries)) + b"".join(entries) + images


if __name__ == "__main__":
    out = Path(__file__).parent
    pngs = {s: grid_to_png(render(s, ss=10)) for s in (16, 32, 48, 64)}
    (out / "_preview_128.png").write_bytes(grid_to_png(render(128, ss=6)))
    (out / "_preview_64.png").write_bytes(pngs[64])
    # 16px 实际大小预览（放大 4 倍最近邻，模拟浏览器中的观感）
    small = render(16, ss=10)
    up = []
    for row in small:
        up.append([px for px in row for _ in range(4)])
    (out / "_preview_16_upscaled.png").write_bytes(grid_to_png([row for row in up for _ in range(4)]))
    (out / "favicon.ico").write_bytes(build_ico(pngs))
    print("渲染完成：_preview_128.png / _preview_64.png / favicon.ico")
