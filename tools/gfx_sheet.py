# -*- coding: utf-8 -*-
r"""유나 3 — GS8 시트 속 글자 라벨 한글 (IDO·KAI·SENHYO·SYUKEI) (2026-09-28)
  라벨 = (찾을 범위 x0,y0,x1,y1, 한글, 정렬 c/l, 기울임). 범위 안에서 «글자 픽셀»을 찾아 꼭 맞는 상자를 잡고:
   · 글자 픽셀 = 범위 가장자리(위아래 1줄·좌우 1칸)에 안 나오는 색 — 바탕·무늬 색은 가장자리에 나오므로 빠진다
   · 지우기 = 같은 줄에서 무늬 주기 P 만큼 옆(상자 밖)의 픽셀로 채움(빗금 바탕도 이어짐, 민바탕이면 P=1)
   · 색 단계 = 원본 글자 픽셀 색을 «바탕과 먼 순»으로 늘어놓은 것 — 한글 안티앨리어싱 농도를 그 단계에 나눠 붙임
   · 글꼴 = 상자 높이 10px 이상은 나눔고딕 Bold(안티앨리어싱), 미만은 갈무리9(비트맵, 가장 진한 색 하나)
   · 새 글자는 원래 글자 상자 안(게임이 시트에서 정해진 사각형을 잘라 씀)
  python tools/gfx_sheet.py → work/gfx/<이름>.GS8 + my files/그래픽/비교_<이름>.png
"""
import collections, os, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

BOLD = r'C:\claude\utils\font\nanum-gothic\NanumGothicBold.ttf'
SMALL = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.ttf'
TINY = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.ttf'          # 8px 줄(상점 목록)
FIXED = {0x3B: list(range(0x71, 0x80)),            # 베이지 띠: 글자 0x71(옅음)‥0x7F(진함) — BTCOM 과 같은 단계
         0x43: [0x42, 0x47, 0x46, 0x45, 0x44]}      # 주황 띠: 가장자리 0x42 → 속 0x44(밝은 노랑)
SHEETS = {
    'MAP/IDO.GS8': [
        ((23, 0, 80, 12), '이동', 'c', 0.15), ((79, 0, 136, 12), '이동', 'c', 0.15),
        ((23, 16, 80, 28), '쇼핑', 'c', 0.15), ((79, 16, 136, 28), '쇼핑', 'c', 0.15),
        ((23, 32, 80, 44), '정보', 'c', 0.15), ((79, 32, 136, 44), '정보', 'c', 0.15),
        ((23, 48, 80, 60), '옵션', 'c', 0.15), ((79, 48, 136, 60), '옵션', 'c', 0.15),
        ((23, 64, 80, 75), '세이브', 'c', 0.15), ((79, 64, 136, 75), '세이브', 'c', 0.15),
    ],
    'MAP/KAI.GS8': [
        ((1, 24, 41, 36), '사기', 'c', 0.15), ((49, 24, 89, 36), '사기', 'c', 0.15),
        ((1, 40, 41, 52), '팔기', 'c', 0.15), ((49, 40, 89, 52), '팔기', 'c', 0.15),
        ((95, 1, 215, 15), '뭘 사고 싶어？', 'l', 0), ((95, 17, 215, 31), '뭘 팔아 줄 거야？', 'l', 0),
        ((95, 33, 176, 47), '이걸로 됐지？', 'l', 0),
        ((-1, 87, 24, 96), '가격', 'l', 0), ((-1, 95, 40, 104), '살 개수', 'l', 0), ((-1, 103, 32, 112), '팔 개수', 'l', 0),
        ((-1, 111, 56, 120), '가진 개수', 'l', 0), ((-1, 119, 40, 128), '합계G', 'l', 0),
    ],
    'BATTLE/SENHYO.GS8': [
        ((30, 6, 120, 26), '전투 평가', 'c', 0.2), ((60, 32, 112, 49), '랭크', 'c', 0.2),
        ((30, 55, 75, 67), '생존율', 'l', 0), ((30, 68, 75, 80), '격파율', 'l', 0),
    ],
    'BATTLE/SYUKEI.GS8': [
        ((20, 6, 130, 25), '포인트 집계', 'c', 0.2), ((22, 30, 70, 45), '획득G', 'l', 0), ((22, 62, 70, 76), '소지G', 'l', 0),
    ],
}


def load(p):
    b = open(p, 'rb').read(); w, h = struct.unpack_from('<HH', b, 0x36)
    return b[:0x100], w, h, bytearray(b[0x100:]), b


def lum(pal, i):
    r, g, b = pal[i]; return .3 * r + .59 * g + .11 * b


def text_mask(text, w, h, shear):
    font = BOLD if h >= 10 else SMALL if h >= 9 else TINY
    sizes = range(24, 6, -1) if font == BOLD else [10] if font == SMALL else [8]   # 갈무리는 설계 크기로만(다른 크기면 비트맵이 늘어나 깨진다)
    for px in sizes:
        f = ImageFont.truetype(font, px)
        l, t, r, b = f.getbbox(text)
        if b - t <= h and (r - l) + shear * (b - t) <= w:
            break
    m = Image.new('L', (w + 40, h + 20), 0)
    dr = ImageDraw.Draw(m)
    if font != BOLD:
        dr.fontmode = '1'                                           # 갈무리는 비트맵 그대로(안티앨리어싱하면 뭉갠다)
    dr.text((20 - l, 10 - t + (h - (b - t)) // 2), text, font=f, fill=255)
    if shear:
        m = m.transform(m.size, Image.AFFINE, (1, shear, -shear * m.height / 2, 0, 1, 0), Image.BICUBIC)
    bb = m.getbbox()
    m = m.crop((bb[0], 10, bb[2], 10 + h))
    return m, font != BOLD


def do_label(px, W, pal, rect, text, align, shear):
    x0, y0, x1, y1 = rect
    H = len(px) // W
    edge = {px[y * W + x] for y in (y0, y1) if 0 <= y < H for x in range(max(0, x0), x1 + 1)}   # 위아래 테두리 줄만(글자가 좌우 끝까지 닿는 띠가 있다)
    plain = collections.Counter(px[y * W + x] for y in range(y0, min(y1 + 1, H)) for x in range(max(0, x0), x1 + 1)).most_common(1)[0][0]
    if plain in FIXED:                                                              # 민바탕 띠: 바탕이 아닌 건 전부 글자
        tp = [(x, y) for y in range(y0 + 1, y1) for x in range(max(0, x0 + 1), x1) if px[y * W + x] != plain]
    else:
        tp = [(x, y) for y in range(y0 + 1, y1) for x in range(x0 + 1, x1) if px[y * W + x] not in edge]
    if not tp:
        raise SystemExit('글자 없음 %s %s' % (rect, text))
    tx0, tx1 = min(x for x, _ in tp), max(x for x, _ in tp)
    ty0, ty1 = min(y for _, y in tp), max(y for _, y in tp)
    tcol = collections.Counter(px[y * W + x] for x, y in tp)
    bgc = collections.Counter(px[y * W + x] for y in range(y0, min(y1 + 1, H)) for x in range(max(0, x0), x1 + 1) if px[y * W + x] in edge).most_common(1)[0][0]
    if plain in FIXED:
        bgc = plain; ramp = FIXED[plain]
    else:
        ramp = sorted(tcol, key=lambda c: abs(lum(pal, c) - lum(pal, bgc)))       # 바탕에 가까운 색 → 먼 색
    # 무늬 주기(같은 줄, 글자 상자 오른쪽 빈 곳)
    P = 1
    ys = (ty0 + ty1) // 2
    seg = [px[ys * W + x] for x in range(tx1 + 2, min(x1, tx1 + 34))]
    for p in range(1, 17):
        if len(seg) > p + 4 and all(seg[i] == seg[i + p] for i in range(len(seg) - p)):
            P = p; break
    tpset = set(tp)
    for x, y in tp:                                                   # 지우기
        if plain in FIXED:
            px[y * W + x] = plain; continue                           # 민바탕 띠는 바탕색(옆 복사는 띠 끝 테두리색을 끌고 온다)
        k = 1
        while (x + k * P, y) in tpset or x + k * P <= tx1:
            k += 1
        sx = x + k * P
        px[y * W + x] = px[y * W + sx] if sx <= x1 else bgc
    bw, bh = x1 - x0 - 3, ty1 - ty0 + 1
    m, small = text_mask(text, bw, bh, shear)
    ox = x0 + 2 + (bw - m.width) // 2 if align == 'c' else tx0
    for yy in range(m.height):
        for xx in range(m.width):
            v = m.getpixel((xx, yy)) / 255
            if small:
                if v > 0.5:
                    px[(ty0 + yy) * W + ox + xx] = ramp[-1]
            elif v > 0.1:
                px[(ty0 + yy) * W + ox + xx] = ramp[min(len(ramp) - 1, int(v * len(ramp)))]
    return (tx0, ty0, tx1, ty1), P, len(ramp)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    C = open(os.path.join(ROOT, 'work', 'mem', 'st3', 'CRAM.bin'), 'rb').read()
    pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', C[:512])]
    out = os.path.join(ROOT, 'work', 'gfx'); os.makedirs(out, exist_ok=True)
    for name, labels in SHEETS.items():
        head, W, H, px, raw = load(os.path.join(ROOT, 'work', 'disc', name))
        orig = bytes(px[:W * H])
        for rect, text, align, shear in labels:
            bb, P, nr = do_label(px, W, pal, rect, text, align, shear)
            print('%-18s %-12s 상자 %s 무늬주기 %d 색단계 %d' % (name, text, bb, P, nr))
        base = os.path.basename(name).split('.')[0]
        open(os.path.join(out, base + '.GS8'), 'wb').write(head + bytes(px))
        cmp_ = Image.new('RGB', (W, H * 2))
        for j, d in enumerate((orig, bytes(px[:W * H]))):
            im = Image.new('RGB', (W, H)); im.putdata([pal[v] for v in d]); cmp_.paste(im, (0, H * j))
        cmp_.resize((W * 3, H * 6), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_%s.png' % base))


if __name__ == '__main__':
    main()
