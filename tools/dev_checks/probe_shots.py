# -*- coding: utf-8 -*-
"""分析用户截图：box 边框线 / 红色标注框的像素坐标。

image3 = v1.9.4 满宽布局（蓝框参照）
image4 = v1.9.3 旧窄栏布局（要回退到的目标）
image5 = v1.9.4 + 红框标注（4 处间隔改 5px）
"""
from PIL import Image

CLIP = r"C:\Users\zouzu\.workbuddy\clipboard-images"
IMGS = {
    "image3_v194": CLIP + r"\clipboard-2026-09-30T10-42-27-568Z-e155cef1.png",
    "image4_v193": CLIP + r"\clipboard-2026-09-30T10-42-27-568Z-45d5ce01.png",
    "image5_red": CLIP + r"\clipboard-2026-09-30T10-42-27-569Z-13f2e1e0.png",
}


def is_green(c):
    r, g, b = c.red(), c.green(), c.blue()
    return g > 90 and g > r + 30 and g > b + 30


def is_red(c):
    r, g, b = c.red(), c.green(), c.blue()
    return r > 180 and g < 90 and b < 90


def hlines(img, x0, x1, y0, y1, pred, min_run):
    """找横向线：某行内连续满足 pred 的最长游程 > min_run 则记录。"""
    out = []
    for y in range(y0, min(y1, img.height)):
        best = cur = 0
        start = bs = None
        for x in range(x0, min(x1, img.width)):
            if pred(img.pixelColor(x, y)):
                if cur == 0:
                    start = x
                cur += 1
                if cur > best:
                    best, bs = cur, start
            else:
                cur = 0
        if best >= min_run:
            out.append((y, bs, bs + best - 1, best))
    return out


def vlines(img, x0, x1, y0, y1, pred, min_run):
    out = []
    for x in range(x0, min(x1, img.width)):
        best = cur = 0
        start = bs = None
        for y in range(y0, min(y1, img.height)):
            if pred(img.pixelColor(x, y)):
                if cur == 0:
                    start = y
                cur += 1
                if cur > best:
                    best, bs = cur, start
            else:
                cur = 0
        if best >= min_run:
            out.append((x, bs, bs + best - 1, best))
    return out


def merge_adjacent(rows, gap=3):
    """相邻(差<=gap)的线合并为一组，返回每组 (y_start, y_end)。"""
    if not rows:
        return []
    rows = sorted(rows)
    groups = [[rows[0]]]
    for r in rows[1:]:
        if r[0] - groups[-1][-1][0] <= gap:
            groups[-1].append(r)
        else:
            groups.append([r])
    return [(g[0][0], g[-1][0]) for g in groups]


def red_boxes(img):
    """红色标注像素的连通包围盒（粗网格聚类）。"""
    pts = []
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            if is_red(img.pixelColor(x, y)):
                pts.append((x, y))
    if not pts:
        return []
    # 简单并查集聚类（网格间距 2，阈值 12）
    parent = list(range(len(pts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    grid = {}
    for i, (x, y) in enumerate(pts):
        grid[(x // 16, y // 16)] = i
    for i, (x, y) in enumerate(pts):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                j = grid.get((x // 16 + dx, y // 16 + dy))
                if j is not None:
                    a, b = find(i), find(j)
                    if a != b:
                        parent[a] = b
    clusters = {}
    for i, (x, y) in enumerate(pts):
        clusters.setdefault(find(i), []).append((x, y))
    boxes = []
    for cpts in clusters.values():
        if len(cpts) < 30:
            continue
        xs = [p[0] for p in cpts]; ys = [p[1] for p in cpts]
        boxes.append((min(xs), min(ys), max(xs), max(ys), len(cpts)))
    return sorted(boxes, key=lambda b: (b[1], b[0]))


for tag, path in IMGS.items():
    src = Image.open(path).convert("RGBA")
    # PIL Image -> 简单包装出 pixelColor 兼容
    class W:
        def __init__(self, im):
            self.im = im
            self.width, self.height = im.size

        def pixelColor(self, x, y):
            r, g, b, a = self.im.getpixel((x, y))
            return type("C", (), {"red": lambda s: r, "green": lambda s: g,
                                  "blue": lambda s: b})()

    img = W(src)
    print("=" * 70)
    print(tag, "size =", src.size)
    if tag == "image5_red":
        print("-- 红色横线段 (y, x0..x1, len) len>=40 --")
        for y, x0, x1, n in hlines(img, 0, img.width, 0, img.height, is_red, 40):
            print("    y=%d x=%d..%d len=%d → page y=%d x=%d..%d"
                  % (y, x0, x1, n, y - 8, x0 - 8, x1 - 8))
        print("-- 红色纵线段 (x, y0..y1, len) len>=40 --")
        for x, y0, y1, n in vlines(img, 0, img.width, 0, img.height, is_red, 40):
            print("    x=%d y=%d..%d len=%d → page x=%d y=%d..%d"
                  % (x, y0, y1, n, x - 8, y0 - 8, y1 - 8))
        continue
    if tag == "image4_v193":
        # 中缝水印：淡绿（低透明度）像素，按行/列密度过滤出龙形主体
        rows = {}
        cols = {}
        for y in range(370, 600):
            for x in range(194, 337):
                c = img.pixelColor(x, y)
                r, g, b = c.red(), c.green(), c.blue()
                if g > 140 and g > r + 15 and g > b + 15:
                    rows[y] = rows.get(y, 0) + 1
                    cols[x] = cols.get(x, 0) + 1
        ys = [y for y, n in rows.items() if n >= 25]
        xs = [x for x, n in cols.items() if n >= 8]
        print("-- 中缝水印主体 rows≥25: y=%d..%d (page %d..%d, h=%d)"
              % (min(ys), max(ys), min(ys) - 8, max(ys) - 8, max(ys) - min(ys)))
        print("   cols≥8: x=%d..%d (page %d..%d, w=%d)"
              % (min(xs), max(xs), min(xs) - 8, max(xs) - 8, max(xs) - min(xs)))
        continue
    print("-- 横向绿线组 (y范围) x=20..500 --")
    for g in merge_adjacent(hlines(img, 20, 500, 0, img.height, is_green, 120)):
        print("   y=%d..%d" % g)
    print("-- 纵向绿线组 (x范围) y=%d..%d --" % (300, min(700, img.height)))
    for g in merge_adjacent(vlines(img, 0, img.width, 300, min(700, img.height),
                                   is_green, 60)):
        print("   x=%d..%d" % g)
