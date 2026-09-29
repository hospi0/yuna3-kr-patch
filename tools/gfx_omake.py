# -*- coding: utf-8 -*-
r"""유나 3 — OMAKE.SS1(320×240) 타원 속 «おまけ / モード» → «오마케 / 모드»(사용자 2026-09-28) (2026-09-28)
  타원(중심 67,134 · 안쪽 반지름 54×23) 안에서 분홍 계열(R−G > 40) + 둘레 1px 을 글자로 보고 주변 바탕 평균으로 메운 뒤,
  분홍 0xD41F(248,0,168) 로 두 줄(윗줄 중심 x 52, 아랫줄 x 78 — 원본 배치) 안티앨리어싱(바탕과 섞음)
  python tools/gfx_omake.py → work/gfx/OMAKE.SS1 + my files/그래픽/비교_OMAKE.png
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ss1

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
PINK = (248, 0, 168)
CX, CY, RX, RY = 67, 134, 54, 23
LINES = [('오마케', 52, 126), ('모드', 78, 146)]      # (글, 가운데 x, 가운데 y)


def main():
    b = open(os.path.join(ROOT, 'work', 'disc', 'OMAKE.SS1'), 'rb').read()
    w, h, px, _ = ss1.decode(b)
    im = ss1.to_png(w, h, px).convert('RGB'); orig = im.copy()
    P = im.load()
    inside = lambda x, y: ((x - CX) / RX) ** 2 + ((y - CY) / RY) ** 2 < 1
    txt = set()
    for y in range(CY - RY, CY + RY + 1):
        for x in range(CX - RX, CX + RX + 1):
            if inside(x, y):
                r, g, bb = P[x, y]
                if r - g > 40:
                    txt |= {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if inside(x + dx, y + dy)}
    for _ in range(8):                                           # 바깥부터 메우기
        left = set()
        for x, y in txt:
            nb = [P[x + dx, y + dy] for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2) if (x + dx, y + dy) not in txt and inside(x + dx, y + dy)]
            if len(nb) >= 3:
                P[x, y] = tuple(sum(c[i] for c in nb) // len(nb) for i in range(3))
            else:
                left.add((x, y))
        if not left:
            break
        txt = left
    for text, cx, cy in LINES:
        f = ImageFont.truetype(FONT, 19)
        l, t, r, bt = f.getbbox(text)
        m = Image.new('L', (r - l + 4, bt - t + 4), 0)
        ImageDraw.Draw(m).text((2 - l, 2 - t), text, font=f, fill=255)
        ox, oy = cx - m.width // 2, cy - m.height // 2
        for yy in range(m.height):
            for xx in range(m.width):
                a = m.getpixel((xx, yy)) / 255
                if a > 0.05:
                    bg = P[ox + xx, oy + yy]
                    P[ox + xx, oy + yy] = tuple(round(PINK[i] * a + bg[i] * (1 - a)) for i in range(3))
    npx = [0x8000 | (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10 for c in im.getdata()]
    npx = [o if not o & 0x8000 else n for o, n in zip(px, npx)]            # 원래 투명(최상위 비트 0) 픽셀은 그대로
    nb = ss1.encode(w, h, npx)
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'gfx', 'OMAKE.SS1'), 'wb').write(nb)
    cmp_ = Image.new('RGB', (140, 140))
    cmp_.paste(orig.crop((0, 100, 140, 170)), (0, 0)); cmp_.paste(im.crop((0, 100, 140, 170)), (0, 70))
    cmp_.resize((420, 420), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_OMAKE.png'))
    print('OMAKE %d → %d B' % (len(b), len(nb)))


if __name__ == '__main__':
    main()
