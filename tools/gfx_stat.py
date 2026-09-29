# -*- coding: utf-8 -*-
r"""유나 3 — 상태창 셀 글자(STAT.GB8: 0x100 머리 + VDP2 셀 8×8 8bpp × 298) 한글 (2026-09-28)
  일본어 한 글자 = 셀 하나. 게임은 셀을 이어 붙여 상태 문구를 만든다(攻+アップ+中 …) → 셀마다 한글 한 음절을 제자리에(셀 번호·배치 맵 그대로).
  셀 바탕 = 0x3B 고정, 글자 = 0x7E(진한 회갈색, 원본 글자 단계 안), 갈무리7 8px 비트맵(7×7), 가운데.
  «''» 는 빈 셀로(글자가 줄어든 자리). 영어·숫자·아이콘·«クランイ»(218‥221, 뜻 미확인)는 그대로.
  python tools/gfx_stat.py → work/gfx/STAT.GB8 + my files/그래픽/비교_STAT.png
"""
import collections, os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.ttf'
INK = 0x7E
CELLS = {}
for start, text in ((145, '지형효과'), (149, '행동불가'), (154, '기'), (156, '아이템'), (159, '공'),
                    (166, ' 상승'), (169, '중'), (170, '방어'), (176, ' 하락'), (179, '중'), (180, '체력'),
                    (182, ' 상승'), (185, '중'), (186, '대'), (187, '수면 '), (190, '소'), (191, '혼 란'),
                    (202, '이동력'), (208, '빛의전사'), (213, '기계화인병')):
    for k, ch in enumerate(text):
        CELLS[start + k] = ch.strip()


def main():
    src = open(os.path.join(ROOT, 'work', 'disc', 'STAT.GB8'), 'rb').read()
    head, px = src[:0x100], bytearray(src[0x100:])
    orig = bytes(px)
    f = ImageFont.truetype(FONT, 8)
    for c, ch in CELLS.items():
        cell = px[c * 64:(c + 1) * 64]
        bg = 0x3B                                                  # 베이지 고정(글자가 많은 셀은 최빈색이 글자색이라)
        for i in range(64):
            cell[i] = bg
        if ch:
            m = Image.new('L', (8, 8), 0); d = ImageDraw.Draw(m); d.fontmode = '1'
            l, t, r, b = f.getbbox(ch)
            d.text(((8 - (r - l)) // 2 - l, (8 - (b - t)) // 2 - t), ch, font=f, fill=255)
            for y in range(8):
                for x in range(8):
                    if m.getpixel((x, y)):
                        cell[y * 8 + x] = INK
        px[c * 64:(c + 1) * 64] = cell
    os.makedirs(os.path.join(ROOT, 'work', 'gfx'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'gfx', 'STAT.GB8'), 'wb').write(head + bytes(px))
    C = open(os.path.join(ROOT, 'work', 'mem', 'st3', 'CRAM.bin'), 'rb').read()
    pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', C[:512])]
    cells = list(range(144, 224)); S = 5; per = 16
    im = Image.new('RGB', (per * 8 * S, 2 * 5 * 8 * S + 10), (40, 40, 40))
    for j, data in enumerate((orig, bytes(px))):
        for k, c in enumerate(cells):
            ox, oy = (k % per) * 8 * S, j * (5 * 8 * S + 10) + (k // per) * 8 * S
            for y in range(8):
                for x in range(8):
                    im.paste(pal[data[c * 64 + y * 8 + x]], (ox + x * S, oy + y * S, ox + x * S + S, oy + y * S + S))
    im.save(os.path.join(ROOT, 'my files', '그래픽', '비교_STAT.png'))
    print('STAT 셀 %d개 → work/gfx/STAT.GB8' % len(CELLS))


if __name__ == '__main__':
    main()
