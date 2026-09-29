# -*- coding: utf-8 -*-
r"""유나 3 — 한글 PoC (2026-09-28)
  대상: CH01 첫 대화 «ユナ「うわ～～い！»(DAT 블록 0x8000, 0x5002 본문 인수 @블록+0x9C) → «유나「우와～～！»
  · 글꼴: 한글 = KS X 1001 순번 i → 1수준 한자 SJIS(JIS 0x3021 + i) 코드에 배정.
          코드 → 색인(0.BIN 표 @0x0609A560 − 256) → TBL[색인] = 글리프 칸. PoC 는 한자 칸 1296‥ 을 덮는다(FON 크기 그대로).
          글리프 = 16×16 칸 왼쪽 위 12×12 — 갈무리11 12px 비트맵, 단계 14(맑은 고딕 안티앨리어싱은 획이 끊겨 보여 바꿈)
  · 대사: 원문은 두고 블록 빈 곳(사용 끝 뒤)에 새 문자열을 붙이고 참조 오프셋만 바꿈, B(문자열 영역 길이)도 늘림
  · 디스크: YUNA3.DAT·FON·TBL 크기 그대로 제자리(tools/iso.py)
  python tools/poc.py [--write]  → work/out/…(Track 1).bin
"""
import os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, iso

W = os.path.join(ROOT, 'work', 'disc')
OUT = os.path.join(ROOT, 'work', 'out')
EXE_LOAD, IDX = 0x06004000, 0x0609A560
HANGUL = [bytes([a, b]).decode('cp949') for a in range(0xB0, 0xC9) for b in range(0xA1, 0xFF)]
# 갈무리11 12px 비트맵(가장 진한 단계 14 하나). 맑은 고딕 안티앨리어싱은 얇은 획의 옅은 단계가 화면에서 바탕처럼 보여
# 글자가 끊겨 보였다(2026-09-28 실기 «글자 자체 모양이 깨짐»)
FONT = ImageFont.truetype(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.ttf', 12)


def sjis_of(ch):
    """한글 → 1수준 한자 SJIS 코드(JIS 0x3021 + KS 순번)"""
    n = 15 * 94 + HANGUL.index(ch)                  # JIS 16행 1열부터
    row, col = n // 94 + 1, n % 94 + 1
    lead = (row + 1) // 2 + (0x80 if row <= 62 else 0xC0)
    tr = col + 0x3F + (1 if col >= 64 else 0) if row & 1 else col + 0x9E
    return lead << 8 | tr


def tbl_index(exe, code):
    hi, lo = (code >> 8) - 0x81, code & 0xFF
    return struct.unpack_from('>H', exe, IDX - EXE_LOAD + 2 * (hi * 0xC0 + lo))[0] - 256


def glyph(ch):
    big = Image.new('L', (24, 24), 0)
    dr = ImageDraw.Draw(big); dr.fontmode = '1'             # 비트맵 그대로
    dr.text((4, 2), ch, font=FONT, fill=255)
    im = Image.new('L', (16, 16), 0)
    bb = big.getbbox()
    im.paste(big.crop(bb), (0 + (11 - (bb[2] - bb[0])) // 2, 1))   # 원본처럼 칸 왼쪽 위 12×12 안(1줄 아래, 11칸 폭 가운데)
    b = bytearray(128)
    for y in range(16):
        for x in range(16):
            v = round(im.getpixel((x, y)) * 14 / 255)
            b[y * 8 + x // 2] |= v << (4 if x % 2 == 0 else 0)
    return bytes(b)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    exe = open(os.path.join(W, '0.BIN'), 'rb').read()
    D = bytearray(open(os.path.join(W, 'YUNA3.DAT'), 'rb').read())
    F = bytearray(open(os.path.join(W, 'YUNA3.FON'), 'rb').read())
    T = bytearray(open(os.path.join(W, 'YUNA3.TBL'), 'rb').read())
    # 글꼴
    kr = '유나우와'
    for k, ch in enumerate(kr):
        code = sjis_of(ch); i = tbl_index(exe, code); slot = 1296 + k
        assert 0 <= i < 6000, (ch, hex(code), i)
        struct.pack_into('<H', T, 2 * i, slot)
        F[slot * 128:(slot + 1) * 128] = glyph(ch)
        print('%s → SJIS %04X · TBL[%d] = 칸 %d' % (ch, code, i, slot))
    # 대사
    b0 = 0x8000; blk = D[b0:b0 + 0x8000]
    A, B = struct.unpack_from('<HH', blk, 0); S = A + 6
    arg = 0x9C
    old = struct.unpack_from('<H', blk, arg)[0]
    e = blk.index(b'\0', S + old)
    assert blk[S + old:e].decode('cp932') == 'ユナ「うわ～～い！', blk[S + old:e]
    new = b''.join(struct.pack('>H', sjis_of(c)) if c in HANGUL else c.encode('cp932') for c in '유나「우와～～！') + b'\0'
    end = max(i for i in range(len(blk)) if blk[i]) + 1
    pos = end + 1
    blk[pos:pos + len(new)] = new
    struct.pack_into('<H', blk, arg, pos - S)
    struct.pack_into('<H', blk, 2, pos + len(new) - A)
    D[b0:b0 + 0x8000] = blk
    print('대사: 오프셋 %X → %X, B %X → %X' % (old, pos - S, B, pos + len(new) - A))
    if '--write' not in sys.argv:
        print('검사 끝 — 쓰려면 --write'); return
    os.makedirs(OUT, exist_ok=True)
    name = os.path.basename(disc.ROM)
    files = {'YUNA3.DAT': bytes(D), 'YUNA3.FON': bytes(F), 'YUNA3.TBL': bytes(T)}
    iso.patch(disc.ROM, os.path.join(OUT, name), files)
    iso.verify(os.path.join(OUT, name), files)
    print('→', os.path.join(OUT, name))


if __name__ == '__main__':
    main()
