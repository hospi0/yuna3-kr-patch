# -*- coding: utf-8 -*-
r"""유나 3 — 타이틀 옵션 화면 그림(OPT.CSA) 한글 (2026-09-29, 사용자 스크린샷 «옵션»)
  OPT.CSA = TCO +0x40 · GS8 +0x340(ACE 머리 0x100 → 8bpp 256×128 @+0x440) · TAN +0x8440. 화면 색 = CRAM 뱅크 0x700(스테이트 opt).
  시트: 위 224×80 = 메뉴 상자(キーコンフィグ·音声出力 진한 글자, ステレオ·モノラル 회색 = 고를 수 없는 쪽),
        아래 = 조각(ステレオ·モノラル 진한 글자, キーコンフィグ·ナビゲーション·音声出力 주황 = 고른 줄). ON·OFF·BGM·EXIT 는 영어 그대로.
  칸(안쪽, 양끝 포함)마다 «글자 색 번호»만 지우고(띠 모서리 장식 3C‥3F 는 안 건드림) 나눔고딕 Bold 기울임으로 다시 그림.
   · 베이지 띠(바탕 0x3B): 글자 0x71(옅음)‥0x7F(진함). 회색 글자는 원본에 쓰인 0x71‥0x73 만. «모 노» 는 ㅗ 가로획이 이어져 밑줄처럼 보여 한 칸 띄움.
   · 주황 띠(바탕 0x43): 글자 0x40·41·44‥47 — 새 글자는 세로 그러데이션 0x44(위)‥0x47(아래), 옅은 가장자리 0x42
  python tools/gfx_opt.py → work/gfx/OPT.CSA + my files/그래픽/비교_OPT.png
"""
import os, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc, gfx_sheet

W, H = 256, 128
DARK = list(range(0x71, 0x80)); GRAY = [0x71, 0x72, 0x73]; ORANGE = gfx_sheet.FIXED[0x43]
LABELS = [  # (x0, y0, x1, y1 안쪽), 한글, 바탕, 글자 번호 집합, 단계
    ((10, 9, 94, 19), '키 설정', 0x3B, DARK),
    ((10, 22, 61, 32), '음성 출력', 0x3B, DARK),
    ((100, 35, 150, 45), '스테레오', 0x3B, GRAY),
    ((160, 35, 215, 45), '모 노', 0x3B, GRAY),
    ((30, 81, 79, 91), '스테레오', 0x3B, DARK),
    ((28, 97, 78, 107), '모 노', 0x3B, DARK),
    ((82, 81, 166, 91), '키 설정', 0x43, ORANGE),
    ((82, 97, 166, 107), '내비게이션', 0x43, ORANGE),
    ((81, 113, 127, 123), '음성 출력', 0x43, ORANGE),
]
TEXT = {0x3B: set(range(0x70, 0x80)), 0x43: {0x40, 0x41, 0x44, 0x45, 0x46, 0x47}}
SHEAR = 0.2
GRAD = [0x44, 0x45, 0x46, 0x47]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dsk = disc.Disc(); loc = {n: (l, s) for n, l, s in dsk.walk()}['OPT.CSA']
    raw = bytearray(dsk.read(*loc))
    assert struct.unpack_from('<HH', raw, 0x340 + 0x36) == (W, H)
    g = bytearray(raw[0x440:0x440 + W * H]); orig = bytes(g)
    for (x0, y0, x1, y1), text, bg, ramp in LABELS:
        tp = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if g[y * W + x] in TEXT[bg]]
        assert tp, text
        tx0 = min(x for x, _ in tp); ty0 = min(y for _, y in tp); ty1 = max(y for _, y in tp)
        for x, y in tp:
            g[y * W + x] = bg
        bw, bh = x1 - tx0 + 1, ty1 - ty0 + 1
        m, small = gfx_sheet.text_mask(text, bw, bh, SHEAR)
        assert m.width <= bw, (text, m.width, bw)
        for yy in range(m.height):
            for xx in range(m.width):
                v = m.getpixel((xx, yy)) / 255
                if ramp is ORANGE:                                   # 원본처럼 위 밝은 노랑 → 아래 주황 세로 그러데이션, 옅은 가장자리는 0x42
                    if v > 0.45:
                        g[(ty0 + yy) * W + tx0 + xx] = GRAD[min(3, yy * 4 // m.height)]
                    elif v > 0.15:
                        g[(ty0 + yy) * W + tx0 + xx] = 0x42
                elif v > 0.1:
                    g[(ty0 + yy) * W + tx0 + xx] = ramp[min(len(ramp) - 1, int(v * len(ramp)))]
        print('%-10s 칸 %s 글자 %d×%d' % (text, (x0, y0, x1, y1), m.width, m.height))
    raw[0x440:0x440 + W * H] = g
    out = os.path.join(ROOT, 'work', 'gfx'); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'OPT.CSA'), 'wb').write(bytes(raw))
    C = open(os.path.join(ROOT, 'work', 'mem', 'opt', 'CRAM.bin'), 'rb').read()
    pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', C[0xE00:0x1000])]
    cmp_ = Image.new('RGB', (W, H * 2 + 4), (0, 0, 60))
    for j, d in enumerate((orig, bytes(g))):
        im = Image.new('RGB', (W, H)); im.putdata([pal[v] if v else (0, 0, 60) for v in d]); cmp_.paste(im, (0, (H + 4) * j))
    cmp_.resize((W * 3, (H * 2 + 4) * 3), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_OPT.png'))


if __name__ == '__main__':
    main()
