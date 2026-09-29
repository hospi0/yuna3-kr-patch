# -*- coding: utf-8 -*-
r"""유나 3 — 장 제목 그림 한글(CH0N/CHAPN.SS1, 320×240 16비트) (2026-09-28)
  원본에서 «Chapter.N» 아래 일본어 줄(글자 있는 가로줄 묶음 중 둘째)만 바탕색으로 지우고 한글을 그린다.
  글자 = 나눔고딕 Bold, 기울임(원본처럼), 속 = 원본 글자 속색(가장 밝은 색), 테두리 = 원본 테두리색(속 바로 바깥 픽셀 최빈값)
  python tools/gfx_chap.py → work/gfx/CHAPN.SS1 + my files/그래픽/비교_CHAPN.png(위 원본 / 아래 한글)
"""
import collections, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ss1

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
TITLES = {1: '네오 도쿄의 위기！', 2: '싸움의 우주로・・・', 3: '결전！칠흑의 요새・・・',
          4: '맹공！악의 기계화 제국・・・', 5: '모두의 마음은 영원히・・・'}
SHEAR = 0.22


def bands(px, w, h, bg):
    rows = [any(px[y * w + x] != bg for x in range(w)) for y in range(h)]
    out = []; y = 0
    while y < h:
        if rows[y]:
            s = y
            while y < h and rows[y]:
                y += 1
            out.append((s, y))
        y += 1
    return out


def render(text, height, fill, edge, maxw):
    text = text.replace('・', '•')
    """원본처럼 3겹: 흰 속 / 검정 틈 1px / 회색 바깥 1px. 폭이 넘치면 누르지 않고 글자를 줄인다"""
    for px in range(40, 8, -1):
        f = ImageFont.truetype(FONT, px)
        l, t, r, b = f.getbbox(text)
        if b - t <= height - 8 and (r - l) + SHEAR * (b - t) + 8 <= maxw:
            break
    W, H = r - l + 40, b - t + 12
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).text((20 - l, 6 - t), text, font=f, fill=255)                # 가운뎃점은 원본처럼 크게(• 로 그림)
    mask = mask.transform((W, H), Image.AFFINE, (1, SHEAR, -SHEAR * H / 2, 0, 1, 0), Image.BICUBIC)
    bb = mask.getbbox(); mask = mask.crop((bb[0] - 3, bb[1] - 3, bb[2] + 3, bb[3] + 3))
    core = mask.point(lambda v: 255 if v >= 120 else 0)
    gap = core.filter(ImageFilter.MaxFilter(3))
    ring = gap.filter(ImageFilter.MaxFilter(3))
    out = Image.new('RGBA', mask.size, (0, 0, 0, 0))
    out.paste(Image.new('RGBA', mask.size, edge), (0, 0), ring)
    out.paste(Image.new('RGBA', mask.size, (0, 0, 0, 255)), (0, 0), gap)
    out.paste(Image.new('RGBA', mask.size, fill), (0, 0), core)
    return out


def rgb(v):
    return ((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3, 255)


def v16(c):
    return 0x8000 | (c[0] >> 3) | (c[1] >> 3) << 5 | (c[2] >> 3) << 10


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    out = os.path.join(ROOT, 'work', 'gfx'); os.makedirs(out, exist_ok=True)
    G = os.path.join(ROOT, 'my files', '그래픽'); os.makedirs(G, exist_ok=True)
    for n, text in TITLES.items():
        src = os.path.join(ROOT, 'work', 'disc', 'CH0%d' % n, 'CHAP%d.SS1' % n)
        b = open(src, 'rb').read()
        w, h, px, _ = ss1.decode(b)
        bg = collections.Counter(px).most_common(1)[0][0]
        bd = bands(px, w, h, bg)
        y0, y1 = bd[1]                                                  # 둘째 묶음 = 일본어 줄
        inner = collections.Counter(px[y * w + x] for y in range(y0, y1) for x in range(w) if px[y * w + x] != bg)
        fill = max(inner, key=lambda v: sum(rgb(v)[:3]))
        ec = collections.Counter()
        for y in range(y0, y1):
            for x in range(1, w - 1):
                if px[y * w + x] == fill:
                    for q in (px[y * w + x - 1], px[y * w + x + 1]):
                        if q not in (fill, bg):
                            ec[q] += 1
        edge = ec.most_common(1)[0][0]
        im = ss1.to_png(w, h, px)
        orig = im.copy()
        ImageDraw.Draw(im).rectangle((0, y0 - 2, w - 1, y1 + 2), fill=rgb(bg))
        g = render(text, (y1 - y0) + 4, rgb(fill), rgb(edge), w - 16)
        im.alpha_composite(g, ((w - g.width) // 2, (y0 + y1) // 2 - g.height // 2))
        npx = [v16(c) if c[3] else bg for c in im.getdata()]
        nb = ss1.encode(w, h, npx)
        open(os.path.join(out, 'CHAP%d.SS1' % n), 'wb').write(nb)
        cmp_ = Image.new('RGB', (w, h * 2)); cmp_.paste(orig.convert('RGB'), (0, 0)); cmp_.paste(im.convert('RGB'), (0, h))
        cmp_.save(os.path.join(G, '비교_CHAP%d.png' % n))
        print('CHAP%d  %d → %d B  줄 %d‥%d  속 %04X 테두리 %04X' % (n, len(b), len(nb), y0, y1, fill, edge))


if __name__ == '__main__':
    main()
