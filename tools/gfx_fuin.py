# -*- coding: utf-8 -*-
r"""유나 3 — «封»(CH05/FUIN.GS8, 8bpp 128×128, 글자는 왼쪽 위 64×64) → «봉» (2026-09-28)
  원본 색 = 바깥부터 0x67(테두리) · 0x66 · 0x64 · 0x63 · 속 0x62 동심 5겹 → 한글 마스크를 가장자리부터 1px 씩 깎아 같은 순서로 칠함
  글꼴 = Black Han Sans(굵은 획), 64×64 안 2px 여백
  python tools/gfx_fuin.py → work/gfx/FUIN.GS8 + my files/그래픽/비교_FUIN.png
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = r'C:\claude\utils\font\logo\BlackHanSans.ttf'
LAYERS = [0x67, 0x66, 0x64, 0x63]             # 바깥 → 안, 나머지 속 = 0x62
CORE = 0x62


def main():
    src = open(os.path.join(ROOT, 'work', 'disc', 'CH05', 'FUIN.GS8'), 'rb').read()
    W, H = struct.unpack_from('<HH', src, 0x36)
    head, px = src[:0x100], bytearray(src[0x100:])
    orig = bytes(px[:W * H])
    for y in range(64):
        for x in range(64):
            px[y * W + x] = 0
    for s in range(80, 20, -1):
        f = ImageFont.truetype(FONT, s)
        l, t, r, b = f.getbbox('봉')
        if r - l <= 58 and b - t <= 58:
            break
    m = Image.new('L', (64, 64), 0)
    ImageDraw.Draw(m).text(((64 - (r - l)) // 2 - l, (64 - (b - t)) // 2 - t), '봉', font=f, fill=255)
    cur = m.point(lambda v: 255 if v >= 128 else 0)
    for c in LAYERS:
        inner = cur.filter(ImageFilter.MinFilter(3))
        for y in range(64):
            for x in range(64):
                if cur.getpixel((x, y)) and not inner.getpixel((x, y)):
                    px[y * W + x] = c
        cur = inner
    for y in range(64):
        for x in range(64):
            if cur.getpixel((x, y)):
                px[y * W + x] = CORE
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'gfx', 'FUIN.GS8'), 'wb').write(head + bytes(px))
    C = open(os.path.join(ROOT, 'work', 'mem', 'st3', 'CRAM.bin'), 'rb').read()
    pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', C[:512])]
    cmp_ = Image.new('RGB', (128, 64))
    for j, d in enumerate((orig, bytes(px[:W * H]))):
        im = Image.new('RGB', (W, H)); im.putdata([pal[v] if v else (208, 216, 184) for v in d]); cmp_.paste(im.crop((0, 0, 64, 64)), (64 * j, 0))
    cmp_.resize((384, 192), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_FUIN.png'))
    print('FUIN → work/gfx/FUIN.GS8 (글꼴 %dpx)' % s)


if __name__ == '__main__':
    main()
