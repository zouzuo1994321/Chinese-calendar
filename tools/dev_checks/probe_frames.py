# -*- coding: utf-8 -*-
"""从 build/_inspect 的裁剪图里检测红/蓝框的像素包围盒，反推用户在截图上标注的是哪些区块。

模型本身无法肉眼看图，只能用 PIL 统计强红/强蓝像素的包围盒，给出坐标与占比，
再结合截图源区域（红框来自约原图 300,300~400,400；蓝框来自图2多段）推断对应页面区块。
"""
import os
from PIL import Image

INSPECT = os.path.join(os.path.dirname(__file__), "..", "..", "build", "_inspect")


def scan(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    red_box = None
    blue_box = None
    red_n = blue_n = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            # 强红：R 高且明显高过 G、B
            if r > 150 and (r - g) > 70 and (r - b) > 70:
                red_n += 1
                red_box = (min(red_box[0], x) if red_box else x,
                           min(red_box[1], y) if red_box else y,
                           max(red_box[2], x) if red_box else x,
                           max(red_box[3], y) if red_box else y)
            # 强蓝：B 高且明显高过 R、G
            elif b > 150 and (b - r) > 70 and (b - g) > 50:
                blue_n += 1
                blue_box = (min(blue_box[0], x) if blue_box else x,
                            min(blue_box[1], y) if blue_box else y,
                            max(blue_box[2], x) if blue_box else x,
                            max(blue_box[3], y) if blue_box else y)
    out = "%s (%dx%d)\n" % (os.path.basename(path), w, h)
    if red_box:
        out += "  红框包围盒 x=%d..%d y=%d..%d  像素数=%d\n" % (
            red_box[0], red_box[2], red_box[1], red_box[3], red_n)
    else:
        out += "  红框：未检测到强红色像素\n"
    if blue_box:
        out += "  蓝框包围盒 x=%d..%d y=%d..%d  像素数=%d\n" % (
            blue_box[0], blue_box[2], blue_box[1], blue_box[3], blue_n)
    else:
        out += "  蓝框：未检测到强蓝色像素\n"
    return out


if __name__ == "__main__":
    for f in ("red.png", "blue1.png", "blue23.png", "blue4.png"):
        p = os.path.join(INSPECT, f)
        if os.path.exists(p):
            print(scan(p))
        else:
            print("%s 不存在\n" % f)
