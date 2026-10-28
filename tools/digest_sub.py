# -*- coding: utf-8 -*-
r"""유나 3 타이틀 대기 «전작 줄거리(DIGEST)» 음성 자막 훅 (2026-10-28)
  ★DIGEST.BIN 안에서만 건다 — 이 파일은 줄거리 소개 때만 저메모리 0x00200000 에 올라오는 덮어쓰기 프로그램이라
    게임 다른 화면에는 코드도 자료도 없다(0.BIN·공용 함수는 한 바이트도 안 고침).
  · 훅 = DIGEST.BIN 자기 리터럴 표의 함수 주소만 바꿈:
      0x0601D1EC 음성 재생(r4 = "D0nn.ACM") → h_play : 그 음성의 자막 목록 고르고 프레임 0
      0x0601D404 음성 정지                    → h_stop : 자막 끔
      0x06006E6C 매 프레임(SGL slSynch 포함 — GBR+0x12 SynchConst 1 = 60fps) → h_frame : 프레임 +1, 자막 바뀌면 그림
      0x06035080 끝 정리(패턴 0xA2‥0x31F 해제) → h_clean : 자막 끔
  · 그림 = 게임 스프라이트 슬롯 그대로 0x06033BB4(SLOT, PAT, x, y, [1]) 로 띄움 / 끌 때 (SLOT, PAT, −500, −500, [0])(줄거리 소개가 그림 숨길 때와 같은 꼴).
      ★텍스처는 할당기를 안 거치고 VDP1 VRAM 0x6000‥0xBFFF(스테이트 13장 모두 전원 무늬 그대로 = 게임이 안 씀)에 8비트로 직접 그리고
      패턴 표 PAT 칸(w, h, SRCA, SIZE)을 손으로 채움. PAT 0x1F6 = 할당기가 훑는 개수(0x1F4) 밖. 끝 정리 전에 칸을 0 으로(해제 함수가 건드려도 빈 칸).
      슬롯 칸 PMOD 0x0428(RGB) → 0x0420(8비트 256색 뱅크) · COLR 0x6600 → 화면 값 0x66FD/0x66FE.
      (2026-10-28 RGB 모드에 팔레트 값 0x66FD 를 넣은 판은 VRAM·명령·우선순위가 다 맞는데 안 보임 — 게임 팔레트 스프라이트는 PMOD 0x04A0 8비트라 그 방식으로)
      슬롯 0x1F5(그림 0x1F3 뒤) — 줄거리 소개는 0x1F2·0x1F3 만 씀.
  · 글자 = 갈무리11 1비트(쓰는 글자만) → 런타임에 1비트 판에 찍고 1px 검은 테두리(팽창) → 8비트(0 투명 · 0xFD 검정 · 0xFE 흰색).
  · ★페이드 막 위로(2026-10-28 마지막 장면 «페이드인 동안 하나도 안 나옴»): 어두운 화면 = NBG3 검은 막(우선순위 7, PRINB 0x0707)이
      스프라이트(SPR0=4) 위를 덮고 투명도로 걷음. 자막 화면 값 0x66xx = 팔레트 형식 SPTYPE 3 PR 3 → SPR3, SGL 사본 PRISB 윗바이트(SPR3)를 7 로
      → 같은 우선순위면 스프라이트가 NBG 보다 앞. 색 = CRAM 1789(검정)·1790(흰색). 끝 정리(h_clean)에서 SPR3·CRAM 되돌림.
  · ★순서기(2026-10-28 «페이드인 때 자막 안 나옴»): 자막은 차례대로 하나도 안 건너뜀. (어두울 때 기다리기는 막 위로 띄우게 되며 뺌 — 2026-10-28)
      프레임이 밀려 늦게 띄운 줄도 최소 MINF 프레임 보이고 원래 시각을 따라잡는다.
  · ★앞뒤 순서 = 슬롯 위치 표(0x060AA320 + 슬롯×16) +8 값, 작을수록 앞(나중에 그림). 6033BB4 는 0xA2 로 넣는데 스크롤 장면(D006‥)은
      그림을 0xA0 으로 둬서 자막이 그림 뒤로 숨음(2026-10-28 스테이트 2) → 띄운 뒤 0x9F 로 고침.
  · 자리 = DIGEST.BIN 뒤 0x201E00‥(타이틀 BIN 크기 0x207EBC 안 — 줄거리 소개 중엔 타이틀 찌꺼기라 아무도 안 씀).
  자막 표 work/digest/digest_sub.tsv (음성 · 시작 · 끝 · 원문 · 번역 · 비고), 음성 디코더 tools/acm.py
  python tools/digest_sub.py [--png]   → 검산(흉내기로 전 자막 그려 파이썬 기준과 대조) · --png 면 work/digest/png/ 미리보기
"""
import os, re, struct, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sh2asm, sh2sim, ss1, bdf

TSV = os.path.join(ROOT, 'work', 'digest', 'digest_sub.tsv')
SRC = os.path.join(ROOT, 'work', 'disc', 'DIGEST.BIN')
GALMURI = r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'
LINE_H, MAXL = 14, 2
LOAD = 0x00200000; ORIG_LEN = 0x1D64
MYB = 0x00201E00; LIMIT = 0x00207EBC                 # 타이틀 BIN(32,444 B) 이 차지하던 자리 끝
SLOT = 0x1F5; PAT = 0x1F6                            # 슬롯은 그림(0x1F3) 뒤라 위에 그려짐 · 패턴은 할당기가 훑는 개수(0x1F4) 밖 — 칸을 손으로 채움
TEX = 0x25C06000                                     # VDP1 VRAM 0x6000‥0xBFFF(게임이 안 씀)
PTAB = 0x060AD840; STAB_P = 0x0609D458               # 패턴 표(8 B: w h SRCA SIZE) · 슬롯 표 주소가 든 변수(10 B 칸: 패턴 PMOD COLR …)
PMOD8, COLR = 0x0420, 0x6600
FPS = 60; DELAY = 0                                  # 음성 재생 호출 → 실제 소리 시작 차이(프레임) — 실기 보고 맞춤
MINF = 90                                            # 늦게 띄운 줄도 최소 1.5초
DARKB = 0x060FFDCA                                   # SGL 페이드 단계(밝음 0x1E — 스테이트 5장) · 16 미만이면 어두움 → 새 자막 기다림
DC_BLK, DC_WHT = 1789, 1790                          # CRAM 모드 1(2048색) 빈 칸(스테이트 11장 모두 0 — 1760‥1791)
BLACK, WHITE = DC_BLK & 0xFF, DC_WHT & 0xFF           # 8비트 화소(0xFD·0xFE) — 뱅크 0x66 붙어 0x66FD = 팔레트 형식 SPTYPE 3 PR 3 → SPR3, DC 1789/1790
assert (COLR | BLACK) & 0x7FF == DC_BLK and (COLR | WHITE) & 0x7FF == DC_WHT and (COLR >> 13) & 3 == 3
PRI_SH = 0x060FFDB2                                  # SGL VDP2 레지스터 사본 PRISB 윗바이트 = SPR3 우선순위(원래 5)
CRAM = 0x25F00000
STRIDE = 44                                          # 1비트 판 한 줄(320/8 + 여유)
MAXH = LINE_H * MAXL + 1
F_PLAY, F_STOP, F_FRAME, F_CLEAN = 0x0601D1EC, 0x0601D404, 0x06006E6C, 0x06035080
F_PUT = 0x06033BB4
PUNCT_SP = re.compile(r'([,.!?:;)\]}\'"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥]) (?! )')


def rows():
    out = []
    for ln in open(TSV, encoding='utf-8'):
        if ln.startswith('#') or not ln.strip():
            continue
        c = ln.rstrip('\n').split('\t')
        v = int(c[0][1:]); s, e = float(c[1]), float(c[2])
        lines = [PUNCT_SP.sub(r'\1', t) for t in c[4].split('\\n')]
        assert len(lines) <= MAXL, ('줄 수', c[0], c[4])
        out.append((v, s, e, lines))
    return out


def glyphs(chars):
    """갈무리11(1비트 BDF) — 잉크 윗줄이 3 이라 3 올려 16×16 칸에(2026-10-28 하스피 «깔끔하게 갈무리에 테두리»)"""
    F = bdf.Font(GALMURI)
    G = {}
    for ch in sorted(chars):
        assert ch == ' ' or ord(ch) in F.g, ('갈무리에 없는 글자', ch)
        pts, adv = F.draw(ch, 0, -3)
        rowsb = [0] * 16
        for x, y in pts:
            assert 0 <= x < 16 and 0 <= y < 16, ('16×16 넘침', ch, x, y)
            rowsb[y] |= 0x8000 >> x
        G[ch] = (adv, rowsb)
    return G


def layout(R, G):
    """자막마다 (w, h, [(x, [글자…])…])"""
    out = []
    for v, s, e, lines in R:
        ws = [sum(G[c][0] for c in t) for t in lines]
        w = (max(ws) + 2 + 7) // 8 * 8
        assert w <= 320, ('폭 넘침', lines, max(ws))
        h = LINE_H * len(lines) + 1
        out.append((w, h, [((w - lw) // 2, t) for lw, t in zip(ws, lines)]))
    return out


# ---------------- 파이썬 기준 그림(훅과 같은 셈법) ----------------
def ref_bitmap(w, h, lines, G):
    T = [[0] * (w + 24) for _ in range(h + 2)]          # T[y+1][x]
    for i, (x, t) in enumerate(lines):
        y0 = 1 + LINE_H * i
        for ch in t:
            adv, rb = G[ch]
            for r in range(16):
                for k in range(16):
                    if rb[r] & (0x8000 >> k):
                        T[y0 + r + 1][x + k] = 1
            x += adv
    px = []
    for y in range(h):
        for x in range(w):
            if T[y + 1][x]:
                px.append(WHITE)
            elif any(T[y + 1 + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1) if 0 <= x + dx):
                px.append(BLACK)
            else:
                px.append(0)
    return bytes(px)


# ---------------- 자료 ----------------
def data_blob(R, G, L):
    chars = sorted(G); gid = {c: i for i, c in enumerate(chars)}
    by_v = {}
    for (v, s, e, lines), lay in zip(R, L):
        by_v.setdefault(v, []).append((s, e, lay))
    lab = {}; blob = bytearray()
    def at(): return MYB + len(blob)
    def align(n):
        blob.extend(bytes(-len(blob) % n))
    lab['V_LIST'] = at(); blob += bytes(4)
    lab['V_FRAME'] = at(); blob += bytes(4)
    lab['V_CUR'] = at(); blob += bytes(4)
    lab['V_SHOWN'] = at(); blob += bytes(4)
    lab['V_SPR3'] = at(); blob += b'\xff\xff\xff\xff'
    lab['VOICES'] = at(); voices_off = len(blob); blob += bytes(4 * 17)
    recs = {}; texts = []
    for v in sorted(by_v):
        recs[v] = at()
        for s, e, (w, h, lines) in by_v[v]:
            sf = max(0, int(round(s * FPS)) + DELAY); ef = int(round(e * FPS)) + DELAY
            texts.append((len(blob) + 8, w, h, lines))
            blob += struct.pack('>4HI', sf, ef, w, h, 0)
        blob += struct.pack('>4HI', 0xFFFF, 0xFFFF, 0, 0, 0)
    for v, a in recs.items():
        struct.pack_into('>I', blob, voices_off + 4 * v, a)
    for off, w, h, lines in texts:
        align(2); struct.pack_into('>I', blob, off, at())
        blob += struct.pack('>H', len(lines))
        for x, t in lines:
            blob += struct.pack('>HH', x, len(t)) + b''.join(struct.pack('>H', gid[c]) for c in t)
        assert w * h <= 0x6000, ('텍스처 자리', w, h)
    align(2); lab['GLY'] = at()
    for c in chars:
        adv, rb = G[c]
        blob += struct.pack('>BB16H', adv, 0, *rb)
    align(4); lab['TALL'] = at(); blob += bytes(STRIDE * (MAXH + 2))
    lab['DBUF'] = at(); blob += bytes(48)
    return bytes(blob), lab


CODE = r'''
h_play:
  sts.l pr,@-r15
  mov.l r4,@-r15
  mov.l r5,@-r15
  mov.l r6,@-r15
  mov.l r7,@-r15
  bsr hide
  nop
  mov.l @(12,r15),r4
  mov #0,r3
  mov.b @r4,r0
  cmp/eq #0x44,r0
  bf p_set
  mov.b @(2,r4),r0
  add #-48,r0
  mov r0,r1
  shll2 r1
  add r0,r1
  shll r1
  mov.b @(3,r4),r0
  add #-48,r0
  add r0,r1
  mov #1,r2
  cmp/ge r2,r1
  bf p_set
  mov #16,r2
  cmp/gt r2,r1
  bt p_set
  shll2 r1
  mov.l #VOICES,r2
  add r2,r1
  mov.l @r1,r3
p_set:
  mov.l #V_LIST,r1
  mov.l r3,@r1
  mov #0,r0
  mov.l #V_FRAME,r1
  mov.l r0,@r1
  mov.l @r15+,r7
  mov.l @r15+,r6
  mov.l @r15+,r5
  mov.l @r15+,r4
  lds.l @r15+,pr
  mov.l #F_PLAY,r0
  jmp @r0
  nop

h_stop:
  sts.l pr,@-r15
  mov.l r4,@-r15
  mov.l r5,@-r15
  mov.l r6,@-r15
  mov.l r7,@-r15
  mov #0,r0
  mov.l #V_LIST,r1
  mov.l r0,@r1
  bsr hide
  nop
  mov.l @r15+,r7
  mov.l @r15+,r6
  mov.l @r15+,r5
  mov.l @r15+,r4
  lds.l @r15+,pr
  mov.l #F_STOP,r0
  jmp @r0
  nop

h_clean:
  sts.l pr,@-r15
  mov.l r4,@-r15
  mov.l r5,@-r15
  mov.l r6,@-r15
  mov.l r7,@-r15
  mov #0,r0
  mov.l #V_LIST,r1
  mov.l r0,@r1
  bsr hide
  nop
  mov.l #PENT,r1
  mov #0,r0
  mov.l r0,@r1
  mov.l r0,@(4,r1)
  mov.l #V_SPR3,r1
  mov.l @r1,r0
  tst #0x80,r0
  bf c_nopri
  mov.l #PRI_SH,r2
  mov.b r0,@r2
  mov #-1,r0
  mov.l r0,@r1
  mov.l #CRAM_W,r1
  mov #0,r0
  mov.w r0,@r1
c_nopri:
  mov.l @r15+,r7
  mov.l @r15+,r6
  mov.l @r15+,r5
  mov.l @r15+,r4
  lds.l @r15+,pr
  mov.l #F_CLEAN,r0
  jmp @r0
  nop

h_frame:
  sts.l pr,@-r15
  mov.l #F_FRAME,r0
  jsr @r0
  nop
  mov.l r0,@-r15
  bsr update
  nop
  mov.l @r15+,r0
  lds.l @r15+,pr
  rts
  nop

update:
  sts.l pr,@-r15
  mov.l #V_LIST,r1
  mov.l @r1,r2
  tst r2,r2
  bt u_none
  mov.l #V_FRAME,r1
  mov.l @r1,r3
  add #1,r3
  mov.l r3,@r1
u_lp:
  mov.w @r2,r0
  extu.w r0,r0
  mov.l #0xFFFF,r1
  cmp/eq r1,r0
  bt u_none
  mov.l #V_CUR,r1
  mov.l @r1,r4
  cmp/eq r2,r4
  bf u_wait
  mov.w @(2,r2),r0
  extu.w r0,r0
  cmp/hi r3,r0
  bt u_have
  mov.l #V_SHOWN,r1
  mov.l @r1,r0
  mov.l #MINF,r1
  add r1,r0
  cmp/hi r3,r0
  bt u_have
  add #12,r2
  mov.l #V_LIST,r1
  mov.l r2,@r1
  bra u_lp
  nop
u_wait:
  cmp/hi r3,r0
  bf u_have
u_none:
  mov #0,r2
u_have:
  mov.l #V_CUR,r1
  mov.l @r1,r0
  cmp/eq r2,r0
  bt u_ret
  mov.l r2,@-r15
  bsr hide
  nop
  mov.l @r15+,r4
  tst r4,r4
  bt u_ret
  mov.l #V_CUR,r1
  mov.l r4,@r1
  mov.l #V_FRAME,r1
  mov.l @r1,r0
  mov.l #V_SHOWN,r1
  mov.l r0,@r1
  bsr show
  nop
u_ret:
  lds.l @r15+,pr
  rts
  nop

hide:
  sts.l pr,@-r15
  mov.l #V_CUR,r1
  mov.l @r1,r0
  tst r0,r0
  bt h_ret
  mov #0,r0
  mov.l r0,@r1
  mov.l r0,@-r15
  mov.l #SLOT,r4
  mov.l #PAT,r5
  mov.l #-500,r6
  mov r6,r7
  mov.l #F_PUT,r0
  jsr @r0
  nop
  add #4,r15
h_ret:
  lds.l @r15+,pr
  rts
  nop

show:
  sts.l pr,@-r15
  mov.l r8,@-r15
  mov.l r9,@-r15
  mov.l r10,@-r15
  mov.l r11,@-r15
  mov.l r12,@-r15
  mov.l r13,@-r15
  mov.l r14,@-r15
  mov r4,r14
  bsr render
  nop
  mov.l #PENT,r1
  mov.w @(4,r14),r0
  mov.w r0,@r1
  extu.w r0,r2
  mov.w @(6,r14),r0
  mov.w r0,@(2,r1)
  extu.w r0,r3
  mov.l #SRCA,r0
  mov.w r0,@(4,r1)
  shlr2 r2
  shlr r2
  shll8 r2
  or r3,r2
  mov r2,r0
  mov.w r0,@(6,r1)
  mov #1,r1
  mov.l r1,@-r15
  mov.w @(4,r14),r0
  extu.w r0,r1
  mov.l #320,r6
  sub r1,r6
  shlr r6
  mov.w @(6,r14),r0
  extu.w r0,r1
  mov.l #216,r7
  sub r1,r7
  mov.l #SLOT,r4
  mov.l #PAT,r5
  mov.l #F_PUT,r0
  jsr @r0
  nop
  add #4,r15
  mov.l #ZPOS,r1
  mov.l #0x009F0000,r0
  mov.l r0,@r1
  mov.l #STAB_P,r1
  mov.l @r1,r1
  mov.l #SOFF,r0
  add r0,r1
  mov.l #PMOD8,r0
  mov.w r0,@(2,r1)
  mov.l #COLR,r0
  mov.w r0,@(4,r1)
  mov.l #V_SPR3,r1
  mov.l @r1,r0
  tst #0x80,r0
  bt w_pri
  mov.l #PRI_SH,r2
  mov.b @r2,r0
  extu.b r0,r0
  mov.l r0,@r1
w_pri:
  mov.l #PRI_SH,r2
  mov #7,r0
  mov.b r0,@r2
  mov.l #CRAM_B,r1
  mov #0,r0
  mov.w r0,@r1
  mov.l #CRAM_W,r1
  mov.l #0x7FFF,r0
  mov.w r0,@r1
  mov.l @r15+,r14
  mov.l @r15+,r13
  mov.l @r15+,r12
  mov.l @r15+,r11
  mov.l @r15+,r10
  mov.l @r15+,r9
  mov.l @r15+,r8
  lds.l @r15+,pr
  rts
  nop

; ---- render(r14 = 자막 기록) → VDP1 VRAM TEX 에 8비트 그림 ----
render:
  sts.l pr,@-r15
  mov.w @(4,r14),r0
  extu.w r0,r13
  mov.w @(6,r14),r0
  extu.w r0,r12
  mov r12,r1
  add #2,r1
  mov r1,r3
  shll2 r3
  shll r3
  add r1,r3
  add r1,r3
  add r1,r3
  mov.l #TALL,r2
  mov #0,r0
c_lp:
  mov.l r0,@r2
  add #4,r2
  dt r3
  bf c_lp
  mov.l @(8,r14),r11
  mov.w @r11+,r0
  extu.w r0,r10
  mov.l #LINE0,r9
s_line:
  mov.w @r11+,r0
  extu.w r0,r8
  mov.w @r11+,r0
  extu.w r0,r7
  tst r7,r7
  bt s_lend
s_glyph:
  mov.w @r11+,r0
  extu.w r0,r1
  mov r1,r2
  shll2 r2
  shll2 r2
  add r1,r2
  shll r2
  mov.l #GLY,r6
  add r2,r6
  mov.b @r6,r0
  extu.b r0,r5
  add #2,r6
  mov r8,r0
  shlr2 r0
  shlr r0
  mov r9,r4
  add r0,r4
  mov r8,r0
  and #7,r0
  mov r0,r3
  mov #16,r2
s_row:
  mov.w @r6+,r0
  extu.w r0,r1
  tst r1,r1
  bt s_next
  shll8 r1
  mov r3,r0
  tst r0,r0
  bt s_put
s_sh:
  shlr r1
  dt r0
  bf s_sh
s_put:
  mov.b @(2,r4),r0
  or r1,r0
  mov.b r0,@(2,r4)
  mov r1,r0
  shlr8 r0
  mov r0,r1
  mov.b @(1,r4),r0
  or r1,r0
  mov.b r0,@(1,r4)
  shlr8 r1
  mov.b @r4,r0
  or r1,r0
  mov.b r0,@r4
s_next:
  add #44,r4
  dt r2
  bf s_row
  add r5,r8
  dt r7
  bf s_glyph
s_lend:
  mov.l #LSTEP,r1
  add r1,r9
  dt r10
  bf s_line
; ---- 8비트 텍스처 직접(VRAM TEX, 줄 = w 바이트, 두 화소씩 16비트로 씀) ----
  mov.l #TEX,r11
  shlr2 r13
  shlr r13
  mov.l #ROW0,r8
e_row:
  mov.l #DBUF,r6
  mov #0,r0
  mov.b r0,@r6
  add #1,r6
  mov r8,r5
  mov r13,r7
  add #1,r7
a_lp:
  mov r5,r1
  add #-44,r1
  mov.b @r1,r0
  extu.b r0,r2
  mov.b @r5,r0
  extu.b r0,r0
  or r0,r2
  mov r5,r1
  add #44,r1
  mov.b @r1,r0
  extu.b r0,r0
  or r0,r2
  mov r2,r0
  mov.b r0,@r6
  add #1,r6
  add #1,r5
  dt r7
  bf a_lp
  mov #0,r0
  mov.b r0,@r6
  mov.l #DBUF,r6
  mov r8,r5
  mov r13,r7
b_lp:
  mov.b @r5+,r0
  extu.b r0,r1
  shll16 r1
  shll8 r1
  mov.b @(1,r6),r0
  extu.b r0,r2
  mov r2,r4
  shll r4
  or r4,r2
  mov.b @(1,r6),r0
  extu.b r0,r4
  shlr r4
  or r4,r2
  mov.b @r6,r0
  and #1,r0
  shll2 r0
  shll2 r0
  shll2 r0
  shll r0
  or r0,r2
  mov.b @(2,r6),r0
  extu.b r0,r0
  shlr2 r0
  shlr2 r0
  shlr2 r0
  shlr r0
  or r0,r2
  shll16 r2
  shll8 r2
  add #1,r6
  mov #4,r3
p_pair:
  bsr pix
  nop
  shll8 r0
  mov r0,r10
  bsr pix
  nop
  or r10,r0
  mov.w r0,@r11
  add #2,r11
  dt r3
  bf p_pair
  dt r7
  bf b_lp
  add #44,r8
  dt r12
  bf e_row
  lds.l @r15+,pr
  rts
  nop

; pix: r1 = 글자 비트(맨 위), r2 = 테두리 비트 → r0 = 0 / 0xFD / 0xFE (r1·r2 한 칸 밂, r4 씀)
pix:
  shll r1
  bf x_no
  shll r2
  mov.l #0xFE,r0
  rts
  nop
x_no:
  shll r2
  movt r0
  tst r0,r0
  bt x_ret
  mov.l #0xFD,r0
x_ret:
  rts
  nop
'''


def assemble(lab, base):
    syms = dict(lab, F_PLAY=F_PLAY, F_STOP=F_STOP, F_FRAME=F_FRAME, F_CLEAN=F_CLEAN, F_PUT=F_PUT,
                SLOT=SLOT, PAT=PAT, TEX=TEX, SRCA=(TEX & 0x7FFFF) // 8, PENT=PTAB + PAT * 8, STAB_P=STAB_P, SOFF=SLOT * 10, PMOD8=PMOD8, COLR=COLR, ZPOS=0x060AA320 + SLOT * 16 + 8, LSTEP=LINE_H * STRIDE, MINF=MINF, DARKB=DARKB, PRI_SH=PRI_SH, CRAM_B=CRAM + 2 * DC_BLK, CRAM_W=CRAM + 2 * DC_WHT, LINE0=lab['TALL'] + STRIDE * 2, ROW0=lab['TALL'] + STRIDE)
    text = CODE
    for k in sorted(syms, key=len, reverse=True):
        text = re.sub(r'#%s\b' % k, '#0x%X' % syms[k], text)
    code = sh2asm.assemble(text, base)
    labels = {}
    pc = base
    for raw in text.split('\n'):                       # 라벨 주소 다시 셈(어셈블러와 같은 규칙: 라벨 0바이트, 명령 2바이트)
        s = raw.split(';')[0].strip()
        if not s:
            continue
        m = re.match(r'^(\w+):$', s)
        if m:
            labels[m.group(1)] = pc; continue
        pc += 2
    return code, labels


LITS = (F_PLAY, F_STOP, F_FRAME, F_CLEAN)


def literal_sites(exe):
    """DIGEST 코드의 mov.l @(disp,pc) 가 읽는 리터럴 중 LITS 값인 자리"""
    sites = {}
    for o in range(0, ORIG_LEN, 2):
        w = struct.unpack_from('>H', exe, o)[0]
        if w >> 12 == 0xD:
            a = ((LOAD + o) & ~3) + 4 + (w & 0xFF) * 4 - LOAD
            if a + 4 <= ORIG_LEN:
                v = struct.unpack_from('>I', exe, a)[0]
                if v in LITS:
                    sites.setdefault(v, set()).add(a)
    return sites


def build():
    R = rows()
    G = glyphs(set(c for _, _, _, ls in R for t in ls for c in t))
    L = layout(R, G)
    blob, lab = data_blob(R, G, L)
    base = MYB + len(blob); base += -base % 4
    code, clab = assemble(lab, base)
    exe = bytearray(open(SRC, 'rb').read()); assert len(exe) == ORIG_LEN
    sites = literal_sites(exe)
    want = {F_PLAY: 'h_play', F_STOP: 'h_stop', F_FRAME: 'h_frame', F_CLEAN: 'h_clean'}
    for v, nm in want.items():
        assert v in sites, ('리터럴 없음', hex(v))
        for a in sites[v]:
            struct.pack_into('>I', exe, a, clab[nm])
    out = bytes(exe) + bytes(MYB - LOAD - ORIG_LEN) + blob + bytes(base - MYB - len(blob)) + code
    assert LOAD + len(out) <= LIMIT, ('자리 넘침', hex(LOAD + len(out)), hex(LIMIT))
    info = dict(R=R, G=G, L=L, lab=lab, clab=clab, sites={hex(k): sorted(hex(LOAD + a) for a in v) for k, v in sites.items()},
                size=len(out))
    return out, info


# ---------------- 검산: 흉내기로 음성마다 프레임을 돌려 그린 SS1 을 파이썬 기준과 대조 ----------------
def check(out, info, png=False):
    R, G, L, lab, clab = info['R'], info['G'], info['L'], info['lab'], info['clab']
    STAB = 0x0024C760
    mem = sh2sim.Mem()
    mem.add(LOAD, 0x8000, out)
    mem.add(0x060F0000, 0x10000)                      # 스택 · SGL 사본(PRI_SH)
    zt = mem.add(0x060AA000, 0x8000)                  # 슬롯 위치 표(앞뒤 순서 값 +8) + 패턴 표 0x060AD840
    mem.add(0x0609D000, 0x1000); mem.w32(STAB_P, STAB)
    mem.add(STAB, 0x2000)
    mem.add(CRAM, 0x1000)
    vram = mem.add(TEX & 0xFFFF0000, 0x10000)
    names = mem.add(0x00290000, 0x100)
    log = []; got = []
    def put(r, m):
        assert r[4] == SLOT and r[5] == PAT
        z = m.r32(r[15])
        if z == 1:
            w, h, srca, size = m.r16(PTAB + PAT * 8), m.r16(PTAB + PAT * 8 + 2), m.r16(PTAB + PAT * 8 + 4), m.r16(PTAB + PAT * 8 + 6)
            assert srca == (TEX & 0x7FFFF) // 8 and size == (w // 8) << 8 | h, (hex(srca), hex(size))
            o = TEX & 0xFFFF
            got.append((w, h, bytes(vram[o:o + w * h])))
        log.append(('put', r[4], r[5], sh2sim.s32(r[6]), sh2sim.s32(r[7]), z)); r[0] = 0
    def nop(r, m): r[0] = 0x1234
    calls = {F_PUT: put, F_PLAY: nop, F_STOP: nop, F_FRAME: nop, F_CLEAN: nop}
    def call(fn, r4=0):
        regs = [0] * 16; regs[4] = r4; regs[8:15] = [0x88880000 + i for i in range(8, 15)]; regs[15] = 0x060FF000
        rr, n = sh2sim.run(mem, clab[fn], regs, calls=calls)
        assert rr[8:15] == [0x88880000 + i for i in range(8, 15)] and rr[15] == 0x060FF000, ('레지스터 보존', fn)
        return n
    k = 0; worst = 0
    mem.w8(DARKB, 0x1E)
    mem.w8(PRI_SH, 5)
    by_v = {}
    for i, (v, s, e, lines) in enumerate(R):
        by_v.setdefault(v, []).append(i)
    for v in sorted(by_v):
        nm = b'D%03d.ACM\0' % v
        for j, b in enumerate(nm):
            names[j] = b
        call('h_play', 0x00290000)
        last = max(int(round(R[i][2] * FPS)) + DELAY for i in by_v[v])
        for f in range(last + 30 + MINF * len(by_v[v])):
            worst = max(worst, call('h_frame'))
        call('h_stop')
        for i in by_v[v]:
            w, h, lines = L[i]
            exp = ref_bitmap(w, h, lines, G)
            assert got[k] == (w, h, exp), ('그림 다름', R[i][3], got[k][:2], (w, h))
            if png:
                os.makedirs(os.path.join(ROOT, 'work', 'digest', 'png'), exist_ok=True)
                im = Image.new('RGB', (w, h), (60, 90, 140))
                im.putdata([(255, 255, 255) if p == WHITE else (0, 0, 0) if p == BLACK else (60, 90, 140) for p in exp])
                im.resize((w * 2, h * 2), Image.NEAREST).save(os.path.join(ROOT, 'work', 'digest', 'png', 'D%03d_%02d.png' % (v, by_v[v].index(i))))
            k += 1
    assert mem.r16(STAB + SLOT * 10 + 2) == PMOD8 and mem.r16(STAB + SLOT * 10 + 4) == COLR, '슬롯 PMOD·COLR'
    assert mem.r8(PRI_SH) == 7 and mem.r16(CRAM + 2 * DC_WHT) == 0x7FFF, '우선순위·흰색'
    assert struct.unpack_from('>I', zt, 0x320 + SLOT * 16 + 8)[0] == 0x009F0000, '앞뒤 순서 값'
    call('h_clean')
    assert mem.r8(PRI_SH) == 5 and mem.r16(CRAM + 2 * DC_WHT) == 0, '끝 정리 되돌림'
    assert mem.r32(PTAB + PAT * 8) == 0 and mem.r32(PTAB + PAT * 8 + 4) == 0, '끝 정리 전 패턴 칸 0'
    assert k == len(got) == len(R), (k, len(got), len(R))
    shows = [x for x in log if x[0] == 'put' and x[5] == 1]
    hides = [x for x in log if x[0] == 'put' and x[5] == 0]
    assert len(shows) == len(R) and len(hides) == len(R), (len(shows), len(hides))
    return worst


def main():
    out, info = build()
    print('DIGEST.BIN %d → %d B (끝 0x%X / 한계 0x%X) · 글자 %d · 자막 %d' % (
        ORIG_LEN, info['size'], LOAD + info['size'], LIMIT, len(info['G']), len(info['R'])))
    print('리터럴 교체', info['sites'])
    worst = check(out, info, '--png' in sys.argv)
    print('✅흉내기 검산: 자막 %d개 그림 = 파이썬 기준과 같음 · 그리는 프레임 최대 %d 명령' % (len(info['R']), worst))


if __name__ == '__main__':
    main()
