# -*- coding: utf-8 -*-
r"""유나 3 — 전투 승리·패배 조건 그림(CH0N/MST###.CSA 44개) 한글 (2026-09-28)
  CSA = [조각 목록] TCO 팔레트 +0x40 · GS8 +0x340(ACE 머리 0x100 → 8bpp 256×128 @+0x440) · TAN +0x8440.
  시트는 16px 줄 8개: 줄 0 = «勝利条件»(x 0‥79)·«敗北条件»(x 80‥159) 머리, 그 밖의 줄 = 조건 문장(가운데 정렬).
  색: 승리 0xC1‥0xCA · 패배 0xD5‥0xDE 10단계, 세로 그러데이션(위 밝음) — 원본의 «줄마다 평균 단계» × 한글 마스크 농도로 칠함.
  문장은 서로 다른 줄(58)마다 한 번 번역(LINES: 원본 줄 바이트 → 한글, 번호는 work/mst_lines.png 순서), 그 줄을 가진 모든 파일에 넣음.
  글꼴 = 나눔고딕 ExtraBold, 기울임 0.25. 이름은 일본어 읽기·성만 우리식 한자음(사용자 2026-09-28).
  python tools/gfx_mst.py → work/gfx/MST/<CH0N>_<MST###>.CSA + my files/그래픽/비교_MST.png
"""
import collections, os, pickle, struct, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import disc

FONT = r'C:\claude\utils\font\nanum-gothic\NanumGothicExtraBold.ttf'
SHEAR = 0.25
HEAD = ('승리 조건', '패배 조건')
LINES = [   # work/mst_lines.png 순서(서로 다른 줄 58)
    '적병사를 쓰러뜨려라！', '아군 전원 전투불능！', '유나의 전투불능！', '에리카와 마이를 구출하라！',
    '유나, 마이, 에리카 중', '누군가 전투불능！', '육화전・킷카를 쓰러뜨려라！', '아빠와 엄마를 구출하라！',
    '리코리스2 대파', '또는 유나의 전투불능！', '육화전・오우카를 쓰러뜨려라！', '유나 또는',
    '유리의 전투불능！', '육화전・란카를 쓰러뜨려라！', '엘리먼트 페어리호 대파', '또는 유나의 전투불능！',
    '수수께끼 소녀를 도와라！', '유나, 에리카, 아코, 마코,', '…？ 중 누군가 전투불능！', '사천기・류레이를 쓰러뜨려라！',
    '유나 또는 세리카의 전투불능！', '우주선 도크에 도착하라！', '아군 중 누군가 전투불능！', '침입구를 확보하라！',
    '폴리리나 또는', '아군 3명 이상 전투불능！', '카피 로봇을 쓰러뜨려라！', '요기 세 자매를 쓰러뜨려라！',
    '사천기・코쇼를 쓰러뜨려라！', '폴리리나의 전투불능！', '스위치를 눌러라！', '육화전・친카를 쓰러뜨려라！',
    '육화전・토우카를 쓰러뜨려라！', '토우카의 워프 포인트 도달', '또는 유나의 전투불능！', '육화전・아지사이를 쓰러뜨려라！',
    '폭탄을 제거하고,', '육화전・아지사이를 쓰러뜨려라！', '폭탄 폭발 또는', '유나의 전투불능！',
    '요기 세 자매', '겐무와 쿄카를 쓰러뜨려라！', '유나 또는', '폴리리나의 전투불능！',
    '사천기・미키를 쓰러뜨려라！', '승리 조건', '보안 장치의 수수께끼를 풀어라！', '사천기・린마를 쓰러뜨려라！',
    '기계화 황제를 쓰러뜨려라！', '재생 사천기를 쓰러뜨려라！', '엘라인의 전투불능！', '폴리리나의 전투불능！',
    '미사키의 전투불능！', '모두를 구출하라！', '아야코의 전투불능！', '에리카의 전투불능！',
    '재생 육화전을 쓰러뜨려라！', '적의 출현 장치를 파괴하라！',
]
W = 256


def mask(text, w, h=16):
    for px in range(16, 8, -1):
        f = ImageFont.truetype(FONT, px)
        l, t, r, b = f.getbbox(text)
        if b - t <= h - 1 and (r - l) + SHEAR * (b - t) + 4 <= w:
            break
    m = Image.new('L', (w + 40, h + 10), 0)
    ImageDraw.Draw(m).text((20 - l + (w - (r - l)) // 2, 5 - t + (h - (b - t)) // 2), text, font=f, fill=255)
    m = m.transform(m.size, Image.AFFINE, (1, SHEAR, -SHEAR * m.height / 2, 0, 1, 0), Image.BICUBIC)
    return m.crop((20, 5, 20 + w, 5 + h))


def paint(g, x0, y0, w, text, orig):
    """g 의 (x0,y0) w×16 칸을 한글로. 색 단계·세로 밝기는 orig 칸에서 잰다"""
    nz = [orig[(y0 + y) * W + x0 + x] for y in range(16) for x in range(w) if orig[(y0 + y) * W + x0 + x]]
    # 단계 묶음은 승리 0xC1‥CA / 패배 0xD5‥DE — 떠돌이 점(0xC1·0xCB·0x7F…)이 섞이니 많은 쪽으로
    base = 0xC0 if sum(0xC1 <= v <= 0xCA for v in nz) >= sum(0xD5 <= v <= 0xDE for v in nz) else 0xD4
    rowl = []
    for y in range(16):
        v = [orig[(y0 + y) * W + x0 + x] - base for x in range(w) if 1 <= orig[(y0 + y) * W + x0 + x] - base <= 10]
        rowl.append(sorted(v)[len(v) * 3 // 4] if v else None)
    known = [(y, l) for y, l in enumerate(rowl) if l]
    for y in range(16):
        if rowl[y] is None:
            rowl[y] = min(known, key=lambda k: abs(k[0] - y))[1]
    m = mask(text, w)
    for y in range(16):
        for x in range(w):
            v = m.getpixel((x, y)) / 255
            i = (y0 + y) * W + x0 + x
            g[i] = 0 if v < 0.15 else base + max(1, min(10, round(rowl[y] * (0.45 + 0.55 * v))))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dsk = disc.Disc(); files = {n: (l, s) for n, l, s in dsk.walk() if '/MST' in n and n.endswith('.CSA')}
    rows = pickle.load(open(os.path.join(ROOT, 'work', '_mst.pkl'), 'rb'))                 # [(번호, 줄, [파일…])]
    assert len(rows) == len(LINES), (len(rows), len(LINES))
    line_of = {}
    for (i, band, fs), text in zip(rows, LINES):
        for f in fs:
            line_of[(f, band)] = text
    out = os.path.join(ROOT, 'work', 'gfx', 'MST'); os.makedirs(out, exist_ok=True)
    pal = None; cmp_rows = []
    for n in sorted(files):
        raw = bytearray(dsk.read(*files[n]))
        g = raw[0x440:0x440 + W * 128]; orig = bytes(g)
        if pal is None:
            pal = [((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3) for v in struct.unpack('>256H', raw[0x40:0x240])]
        for band in range(8):
            reg = orig[band * 16 * W:(band + 1) * 16 * W]
            if not any(reg):
                continue
            if band == 0 and (n, 0) not in line_of:
                for k, (x0, text) in enumerate(((0, HEAD[0]), (80, HEAD[1]))):
                    for y in range(16):
                        for x in range(80):
                            g[y * W + x0 + x] = 0
                    paint(g, x0, 0, 80, text, orig)
            else:
                text = line_of[(n, band)]
                for i in range(band * 16 * W, (band + 1) * 16 * W):
                    g[i] = 0
                paint(g, 0, band * 16, W, text, orig)
        raw[0x440:0x440 + W * 128] = g
        open(os.path.join(out, n.replace('/', '_')), 'wb').write(bytes(raw))
        if n in ('CH01/MST000.CSA', 'CH01/MST002.CSA', 'CH02/MST011.CSA', 'CH04/MST022.CSA', 'CH04/MST079.CSA'):
            cmp_rows.append((orig, bytes(g)))
    im = Image.new('RGB', (W * 2 + 8, 80 * len(cmp_rows)), (30, 30, 30))
    for k, (a, b) in enumerate(cmp_rows):
        for j, d in enumerate((a, b)):
            t = Image.new('RGB', (W, 80)); t.putdata([pal[v] if v else (30, 30, 30) for v in d[:W * 80]])
            im.paste(t, (j * (W + 8), k * 80))
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(ROOT, 'my files', '그래픽', '비교_MST.png'))
    print('MST %d개 → %s' % (len(files), out))


if __name__ == '__main__':
    main()
