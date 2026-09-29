# -*- coding: utf-8 -*-
r"""유나 3 — 전투 명령 버튼 한글(BTCOM.GS8: 0x100 머리 + 8bpp 384×128) (2026-09-28)
  버튼 40×24, 윗줄(y 0) = 보통 7개, 둘째 줄(y 24) = 선택 7개, x = 40×k. 글자 칸 x 6‥33 · y 7‥17(28×11).
  글자 칸(x 6‥33 · y 7‥17)은 통째로 바탕으로 지운 뒤 그림. 보통: 바탕 0x3B, 글자 0x71(밝음)‥0x7F(진함) 15단계 / 선택: 바탕 0x40, 글자 0x47(가장자리)‥0x44(속, 밝은 노랑) 4단계
  글자 = 나눔고딕 Bold 안티앨리어싱(원본처럼 약간 기울임) — 덮을 때 글자 칸의 옛 글자색만 바탕으로 지운다(테두리 그대로)
  python tools/gfx_btcom.py → work/gfx/BTCOM.GS8 + my files/그래픽/비교_BTCOM.png
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
LABELS = ['이동', '공격', '기술', '아이템', '정보', '종료', '행동']
W = 384
X0, X1, Y0, Y1 = 6, 33, 7, 17
SHEAR = 0.18


def mask(text, w, h):
    for px in range(14, 7, -1):
        f = ImageFont.truetype(FONT, px)
        l, t, r, b = f.getbbox(text)
        if b - t <= h and (r - l) + SHEAR * (b - t) <= w:
            break
    m = Image.new('L', (w + 20, h + 10), 0)
    ImageDraw.Draw(m).text((10 - l + (w - (r - l)) // 2, 5 - t + (h - (b - t)) // 2), text, font=f, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, SHEAR, -SHEAR * m.height / 2, 0, 1, 0), Image.BICUBIC)
    return m.crop((10, 5, 10 + w, 5 + h))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = open(os.path.join(ROOT, 'work', 'disc', 'BTCOM.GS8'), 'rb').read()
    head, px = src[:0x100], bytearray(src[0x100:])
    orig = bytes(px)
    for k, text in enumerate(LABELS):
        m = mask(text, X1 - X0 + 1, Y1 - Y0 + 1)
        for sel in (0, 1):
            bx, by = 40 * k, 24 * sel
            bg = 0x40 if sel else 0x3B
            txt = range(0x44, 0x48) if sel else range(0x71, 0x80)
            for y in range(Y0 - 2, Y1 + 3):                     # 원본 글자는 칸 위아래로 한 줄씩 넘친다 — 넓게, 글자색만 지움
                for x in range(X0 - 2, X1 + 3):
                    i = (by + y) * W + bx + x
                    if px[i] in txt:
                        px[i] = bg
            for y in range(Y0, Y1 + 1):
                for x in range(X0, X1 + 1):
                    i = (by + y) * W + bx + x
                    px[i] = bg                                  # 글자 칸은 통째로 바탕(원본 글자에 섞인 다른 색 점도 지움)
                    v = m.getpixel((x - X0, y - Y0)) / 255
                    if sel:
                        if v > 0.12:
                            px[i] = 0x44 if v > 0.75 else 0x45 if v > 0.5 else 0x46 if v > 0.3 else 0x47
                    elif v > 0.07:
                        px[i] = 0x70 + max(1, min(15, round(v * 15)))
    out = os.path.join(ROOT, 'work', 'gfx'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'BTCOM.GS8'), 'wb').write(head + bytes(px))
    C = open(os.path.join(ROOT, 'work', 'mem', 'st3', 'CRAM.bin'), 'rb').read()
    pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', C[:512])]
    cmp_ = Image.new('RGB', (280, 96))
    for j, data in enumerate((orig, bytes(px))):
        im = Image.new('RGB', (W, 48)); im.putdata([pal[v] for v in data[:W * 48]])
        cmp_.paste(im.crop((0, 0, 280, 48)), (0, 48 * j))
    cmp_.resize((280 * 3, 96 * 3), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_BTCOM.png'))
    print('BTCOM 버튼 %d개 × 2 → work/gfx/BTCOM.GS8' % len(LABELS))


if __name__ == '__main__':
    main()
