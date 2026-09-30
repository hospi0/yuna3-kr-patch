# -*- coding: utf-8 -*-
r"""유나 3 한글 빌더 (2026-09-28)
  번역: my files/tsv/yuna3_*.tsv (시험은 환경변수 YN_TSV=폴더 — ⛔my files 에 가짜 번역 쓰지 말 것) · 원문 대응 work/trans/ids.tsv
  ① 글꼴: 번역에 쓰인 한글 음절 → 1수준 한자 SJIS(KS X 1001 순번, tools/poc.sjis_of) → 0.BIN 색인표 → TBL[색인] = 글리프 칸.
          칸은 원래 가나·한자 칸(1,232개)을 차례로 다시 씀(FON 크기 그대로, 넘치면 빌드 중단). 글리프 = poc.glyph(맑은 고딕 12px, 회색 0‥14)
  ② 대사(D…): 블록마다 번역문을 사용 끝 뒤에 덧붙이고 텍스트 자리(dat.text_refs)의 오프셋만 바꿈, B 갱신. 원문은 그대로 둔다.
          줄바꿈 뒤 탭 들여쓰기 = 원문 그 줄의 탭 수(줄이 늘면 마지막 값) — 탭은 창 종류별 고정(대사 6·지문 4·전투 11‥16)
  ③ BIN 문자열(B…): 제자리, 원래 바이트 이하, 뒤는 NUL
  ④ 그림 work/gfx(tools/gfx_*.py) · ⑤ 동영상 자막 work/kr/*.CPK(tools/moviesub.py) — 둘 다 원래 섹터 안 제자리
  검사(하나라도 걸리면 빌드 중단): 줄 수 ≤ max(3, 원문) · 줄 폭 ≤ max(18, 원문 최장) 칸 · 글꼴 밖 글자 · 외자·{XXXX}·코드 모양 ·
       KS X 1001 밖 한글 · 블록 32KB·u16 넘침 · BIN 바이트 초과. 부호 뒤 공백 1칸은 뺀다(2칸 이상은 둔다). 반각 영숫자·부호는 전각으로.
  python tools/build.py            → 검사·통계
  python tools/build.py --write    → work/out/ 트랙 1 (YUNA3.DAT·FON·TBL + 바뀐 BIN 제자리)
"""
import collections, csv, glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dat, disc, iso, poc

W = os.path.join(ROOT, 'work', 'disc')
OUT = os.path.join(ROOT, 'work', 'out')
TSV = os.environ.get('YN_TSV') or os.path.join(ROOT, 'my files', 'tsv')
LINE_W, LINES = 18, 3
GAIJI = {'!!': 0x9873, '!?': 0x9874, '♥': 0x9876, '怒': 0x987A, '汗': 0x987B}
PUNCT = '！？。．、，…‥』」）!?.,~～' + ':;)]\'"' + '：；］｝】〉》”’・·〜♪♥'
TOK = re.compile(r'\\n|\\\\|\\\{|\{([0-9A-F]{4}|!!|!\?|♥|怒|汗)\}')
KS = set(poc.HANGUL)
GFX = {**{'CHAP%d.SS1' % n: 'CH0%d/CHAP%d.SS1' % (n, n) for n in range(1, 6)},       # work/gfx 이름 → 디스크 경로
       'OMAKE.SS1': 'OMAKE.SS1', 'BTCOM.GS8': 'BTCOM.GS8', 'IDO.GS8': 'MAP/IDO.GS8', 'KAI.GS8': 'MAP/KAI.GS8',
       'SENHYO.GS8': 'BATTLE/SENHYO.GS8', 'SYUKEI.GS8': 'BATTLE/SYUKEI.GS8', 'FUIN.GS8': 'CH05/FUIN.GS8', 'STAT.GB8': 'STAT.GB8',
       'OPT.CSA': 'OPT.CSA'}                                                             # 타이틀 옵션(tools/gfx_opt.py)


def squeeze(t):
    """부호 뒤 공백 «1칸»만 뺀다(2칸 이상은 칸 맞춤이라 둔다)"""
    return re.sub(r'([%s])[ 　](?![ 　])' % re.escape(PUNCT), r'\1', t)


def load_translations():
    tr = {}
    for p in sorted(glob.glob(os.path.join(TSV, 'yuna3_*.tsv'))):
        for r in list(csv.reader(open(p, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
            if len(r) > 5 and r[5].strip():
                if r[0] in tr and tr[r[0]] != r[5]:
                    sys.exit('⛔%s: 같은 ID 에 다른 번역' % r[0])
                tr[r[0]] = r[5]
    return tr


def load_ids():
    ids = {}
    for ln in list(open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), encoding='utf-8'))[1:]:
        i, h, locs = ln.rstrip('\n').split('\t')
        ids[i] = (bytes.fromhex(h), locs.split(' '))
    return ids


def parse(t):
    """번역 글 → [('c', 바이트) | ('n',) | ('g', 한글)] , 오류 목록"""
    out = []; err = []; p = 0
    t = squeeze(t)
    while p < len(t):
        m = TOK.match(t, p)
        if m:
            g = m.group()
            if g == '\\n':
                out.append(('n',))
            elif g in ('\\\\', '\\{'):
                out.append(('c', g[1].encode()))
            elif m.group(1) in GAIJI:
                out.append(('c', struct.pack('>H', GAIJI[m.group(1)])))
            else:
                out.append(('c', bytes.fromhex(m.group(1))))
            p = m.end(); continue
        ch = t[p]; p += 1
        if '가' <= ch <= '힣':
            if ch not in KS:
                err.append('KS X 1001 밖 한글 %r' % ch); continue
            out.append(('g', ch)); continue
        if ch == ' ':
            ch = '　'
        elif 0x21 <= ord(ch) <= 0x7E:
            ch = chr(ord(ch) + 0xFEE0)
        ch = {'＇': '’', '＂': '”', '－': '―'}.get(ch, ch)
        try:
            b = ch.encode('cp932')
        except UnicodeEncodeError:
            err.append('인코딩 안 되는 글자 %r' % ch); continue
        if len(b) != 2:
            err.append('반각 글자 %r' % ch); continue
        out.append(('c', b))
    return out, err


def lines_of(toks):
    ls = [[]]
    for t in toks:
        if t[0] == 'n':
            ls.append([])
        else:
            ls[-1].append(t)
    return ls


BST_TSV = os.path.join(ROOT, 'my files', 'tsv', 'bst_지형.tsv')
BST_RE = re.compile(rb'(GND|OBS)\(([^()\r\n]*?)"([^"\r\n]*)"\)([ \t]*)')


def load_bst():
    """전투 맵 스크립트(*.BST, 원문 텍스트를 실행 중에 읽음) 지형 GND·장애물 OBS 이름 번역 {(명령, 원문): 번역}
       (2026-09-30 실기 «道路» 한자 — 예전 조사에서 BST 의 SJIS 를 그림 잡음으로 보고 빠뜨렸다)"""
    out = {}
    for r in list(csv.reader(open(BST_TSV, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))[1:]:
        if len(r) >= 3 and r[2].strip():
            out[(r[0], r[1])] = r[2].strip()
    return out


def bst_patch(enc_bst):
    """디스크의 *.BST → 주석 아닌 GND/OBS 따옴표 안만 바꿈. 길이 차는 그 줄 «)» 뒤 공백으로 흡수(파일 크기 그대로)"""
    D = disc.Disc(); out = {}; errs = []; n = 0; seen = set()
    for name, l, s in D.walk():
        if not name.upper().endswith('.BST'):
            continue
        b = D.read(l, s); nb = bytearray(); p = 0
        for m in BST_RE.finditer(b):
            ls = b.rfind(b'\n', 0, m.start()) + 1
            if b[ls:m.start()].strip().startswith(b';'):
                continue
            try:
                jp = m.group(3).decode('cp932')
            except UnicodeDecodeError:
                continue
            key = (m.group(1).decode(), jp)
            if key not in enc_bst:
                if re.search(r'[぀-鿿]', jp):
                    errs.append('BST %s 번역 없음 %s' % (name, key))
                continue
            new = enc_bst[key]; sp = len(m.group(4)); d = len(new) - len(m.group(3))
            follow = b[m.end():m.end() + 1]
            need = 0 if follow in (b'\r', b'\n', b'') else 1
            if sp - d < need:
                errs.append('BST %s %s «%s» %dB > 원래 %dB + 공백 %d' % (name, key[0], jp, len(new), len(m.group(3)), sp - need)); continue
            nb += b[p:m.start(3)] + new + b'")' + b' ' * (sp - d); p = m.end(); n += 1; seen.add(key)
        if p:
            nb += b[p:]
            assert len(nb) == len(b), name
            if bytes(nb) != b:
                out[name] = bytes(nb)
    return out, errs, n, len(seen)


def patch_name_skip(exe):
    """★유닛 창·파티 목록 이름 = 0x0602772C 가 캐릭터 ID 별로 이름 앞 별칭을 «글자 수 하드코딩»으로 건너뛴다
       (ID 5·7 = 5자 «おっとりの», 0x0D = 3, 0x19‥0x29 = 4, 0x0C·0x1C·0x1E·0x1F = 6, 0x0B·0x10·0x11 = 7,
        0x43‥0x45 = «Ｃ»+이름+8B, 0x4D = «Ｅ»+이름+10B). 번역 이름표는 이미 이름만(names_map) → 건너뛰면 빈칸
       (2026-09-30 실기 «시오리 이름 안 나옴»). 건너뛰기 0 + 접두 갈래 끔."""
    g = bytearray(exe); L = 0x06004000
    fix = {0x06027758: (0xE903, 0xE900), 0x06027772: (0xE904, 0xE900), 0x06027780: (0xE905, 0xE900),
           0x0602779A: (0xE906, 0xE900), 0x060277AE: (0xE907, 0xE900),
           0x06027856: (0x8D42, 0xA042),        # BT/S 0x060278DE → BRA (0x43‥0x45 «Ｃ» 갈래 안 탐, 지연 슬롯 그대로)
           0x060278E0: (0x884D, 0x0008)}        # CMP/EQ #0x4D → CLRT (0x4D «Ｅ» 갈래 안 탐)
    for a, (old, new) in fix.items():
        assert struct.unpack_from('>H', g, a - L)[0] == old, hex(a)
        struct.pack_into('>H', g, a - L, new)
    return g


def literal_keep(x, off):
    """★BIN 문자열이 4바이트 정렬 안 된 자리에서 시작하고 그 정렬 워드가 포인터(0x060xxxxx·0x002xxxxx)면
       앞 몇 바이트는 코드 리터럴(함수 주소)의 아래 절반 — 추출기가 «nlライン攻撃» 처럼 글로 잘못 붙였다.
       그 바이트는 절대 바꾸면 안 된다(2026-09-30 실기: «nl»→전각 ｎｌ 로 리터럴 0x06006E6C 가 깨져 전투 뒤 크래시)"""
    if off % 4 == 0:
        return 0
    v = struct.unpack_from('>I', x, off & ~3)[0]
    return 4 - off % 4 if (0x06000000 <= v < 0x06100000 or 0x00200000 <= v < 0x00300000) else 0


def glyph_index(exe, code):
    return struct.unpack_from('>H', exe, 0x0609A560 - 0x06004000 + 2 * (((code >> 8) - 0x81) * 0xC0 + (code & 0xFF)))[0] - 256


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    exe = open(os.path.join(W, '0.BIN'), 'rb').read()
    T = bytearray(open(os.path.join(W, 'YUNA3.TBL'), 'rb').read())
    F = bytearray(open(os.path.join(W, 'YUNA3.FON'), 'rb').read())
    tbl0 = struct.unpack('<6000H', bytes(T))
    tr = load_translations(); ids = load_ids()
    print('번역: 대사 %d/%d · BIN %d/%d (%s)' % (
        sum(1 for i in tr if i[0] == 'D'), sum(1 for i in ids if i[0] == 'D'),
        sum(1 for i in tr if i[0] == 'B'), sum(1 for i in ids if i[0] == 'B'), TSV))
    errs = []; toks = {}; keep = {}
    for i in list(tr):
        if i[0] == 'B' and i in ids:
            f, off, L = ids[i][1][0].split(':')
            k = literal_keep(open(os.path.join(W, f), 'rb').read(), int(off, 16))
            if k:
                pre = ids[i][0][:k].decode('latin1')
                keep[i] = k
                if tr[i].startswith(pre):
                    tr[i] = tr[i][k:]              # 번역자가 원문 앞 «nl»·«v(» 를 그대로 둔 것 → 떼고 뒤부터 쓴다
    for i, t in tr.items():
        if i not in ids:
            errs.append('%s 원문 ID 없음' % i); continue
        tk, e = parse(t)
        errs += ['%s %s' % (i, x) for x in e]
        raw = ids[i][0]
        ol = raw.split(b'\n')
        nl = lines_of(tk)
        if i[0] == 'D':
            ow = max(len(dat.text_of(l.lstrip(b'\t'))) for l in ol)             # 대략(외자 {XXXX} 는 길게 잡힘 → 넉넉)
            maxw = max(LINE_W, min(ow, 24)); maxl = max(LINES, len(ol))
            if len(nl) > maxl:
                errs.append('%s 줄 수 %d > %d' % (i, len(nl), maxl))
            over = [(k, len(l)) for k, l in enumerate(nl) if len(l) > maxw]
            if over:
                errs.append('%s 줄 폭 초과 %s (최대 %d칸)' % (i, over, maxw))
        toks[i] = tk
    # ⓪' BST 지형·장애물 이름(최대 6자)
    bst = load_bst(); btoks = {}
    for k, t in bst.items():
        tk, e = parse(t)
        errs += ['BST %s %s' % (k, x) for x in e]
        if len(tk) > 6:
            errs.append('BST %s «%s» %d자 > 6' % (k, t, len(tk)))
        btoks[k] = tk
    # ① 글꼴
    used = sorted({t[1] for tk in list(toks.values()) + list(btoks.values()) for t in tk if t[0] == 'g'}, key=poc.HANGUL.index)
    pool = []
    for hi in range(0x81, 0x99):
        for lo in range(0x40, 0x100):
            c = hi << 8 | lo
            if c > 0x987E or not (0x829F <= c):                               # 히라가나(829F~)부터 = 가나·한자
                continue
            i = glyph_index(exe, c)
            if 0 <= i < 6000 and tbl0[i] != 0xFFFF and tbl0[i] not in pool and tbl0[i] < 1301:
                pool.append(tbl0[i])
    if len(used) > len(pool):
        errs.append('글리프 칸 부족: 한글 %d자 > 칸 %d' % (len(used), len(pool)))
    code_of = {}
    for ch, slot in zip(used, pool):
        c = poc.sjis_of(ch); i = glyph_index(exe, c)
        struct.pack_into('<H', T, 2 * i, slot); F[slot * 128:(slot + 1) * 128] = poc.glyph(ch)
        code_of[ch] = struct.pack('>H', c)
    enc = {i: b''.join(code_of.get(t[1], b'??') if t[0] == 'g' else t[1] if t[0] == 'c' else b'\n' for t in tk) for i, tk in toks.items()}
    enc_bst = {k: b''.join(code_of.get(t[1], b'??') if t[0] == 'g' else t[1] for t in tk) for k, tk in btoks.items()}
    bst_files, e, nbst, nkind = bst_patch(enc_bst)
    errs += e
    # ② 대사
    D = bytearray(open(os.path.join(W, 'YUNA3.DAT'), 'rb').read())
    newtext = collections.defaultdict(dict)                                     # 블록 → {옛 오프셋: 새 바이트}
    for i, b in enc.items():
        if i[0] != 'D':
            continue
        for loc in ids[i][1]:
            bl, rest = loc.split(':', 1)
            off = rest.split('=')[0]
            newtext[int(bl, 16)][int(off, 16)] = b
    nb = 0
    for blk in dat.blocks():
        if blk.b0 not in newtext:
            continue
        d = bytearray(blk.d); A = blk.A; S = blk.S
        end = max(k for k in range(len(d)) if d[k]) + 1
        pos = end + 1; placed = {}
        for off, nbyt in newtext[blk.b0].items():
            orig = blk.strings[off]
            tabs = [len(m) for m in re.findall(rb'\n(\t*)', orig)] or [0]
            parts = nbyt.split(b'\n'); out = parts[0]
            for k, pt in enumerate(parts[1:]):
                out += b'\n' + b'\t' * tabs[min(k, len(tabs) - 1)] + pt
            out += b'\0'
            if out not in placed:
                if pos + len(out) > 0x8000 or pos - S > 0xFFFF:
                    errs.append('블록 %X 넘침(%d B)' % (blk.b0, pos + len(out))); break
                d[pos:pos + len(out)] = out; placed[out] = pos - S; pos += len(out)
            newtext[blk.b0][off] = placed[out]
        for p, o in blk.text_refs():
            if o in newtext[blk.b0]:
                struct.pack_into('<H', d, p, newtext[blk.b0][o])
        struct.pack_into('<H', d, 2, pos - A)
        D[blk.b0:blk.b0 + 0x8000] = d; nb += 1
    # ③ BIN
    bins = {}
    for i, b in enc.items():
        if i[0] != 'B':
            continue
        f, off, L = ids[i][1][0].split(':'); off, L = int(off, 16), int(L)
        k = keep.get(i, 0); off += k; L -= k                    # 리터럴 조각은 원본 그대로
        if len(b) > L:
            errs.append('%s %s 자리 %dB < 번역 %dB' % (i, f, L, len(b))); continue
        if f not in bins:
            bins[f] = bytearray(open(os.path.join(W, f), 'rb').read())
        bins[f][off:off + L] = b + bytes(L - len(b))
    bins['0.BIN'] = patch_name_skip(bins.setdefault('0.BIN', bytearray(exe)))
    # ★장 이동 화면 «白丘台女子校へ» 의 «へ» = LONGMAP.BIN 0x29B8 한 글자 문자열(포인터 0x2B90 한 곳, 0x002029B8)
    #   → 가나 칸이 한글로 덮여 «굣» 으로 찍힘. 사용자: 번역하지 말고 아예 안 나오게(장소 이름만) → 빈 문자열
    lm = bins.setdefault('LONGMAP.BIN', bytearray(open(os.path.join(W, 'LONGMAP.BIN'), 'rb').read()))
    assert bytes(lm[0x29B8:0x29BB]) == b'\x82\xd6\x00', 'LONGMAP «へ» 자리 다름'
    lm[0x29B8:0x29BA] = b'\0\0'
    print('한글 %d자 / 칸 %d · 바꾼 블록 %d · BIN %s · BST 지형·장애물 %d곳(%d종) %d파일' % (len(used), len(pool), nb, sorted(bins), nbst, nkind, len(bst_files)))
    if errs:
        print('⛔검사 오류 %d건 (전체 목록 work/trans/errors.txt)' % len(errs))
        open(os.path.join(ROOT, 'work', 'trans', 'errors.txt'), 'w', encoding='utf-8').write('\n'.join(errs) + '\n')
        for e in errs[:60]:
            print('  ' + e)
        sys.exit(1)
    # 되읽기 검사: 고친 DAT 를 다시 풀어 번역한 참조가 새 글을 가리키는지(탭 들여쓰기 포함)
    back = {}
    for b0 in newtext:
        blk = dat.Block(bytes(D[b0:b0 + 0x8000]), b0)
        for p, o in blk.text_refs():
            back.setdefault((b0, o), blk.strings[o])
    bad = [(hex(b0), o) for b0, m in newtext.items() for o in m.values() if (b0, o) not in back]
    if bad:
        sys.exit('⛔되읽기: 새 오프셋을 가리키는 참조 없음 %s' % bad[:5])
    if '--check' in sys.argv:
        for (b0, o), x in list(back.items())[:8]:
            print('  %X:%X %s' % (b0, o, dat.text_of(x)))
    if '--write' not in sys.argv:
        print('검사 끝 — 쓰려면 --write'); return
    files = {'YUNA3.DAT': bytes(D), 'YUNA3.FON': bytes(F), 'YUNA3.TBL': bytes(T)}
    files.update({f: bytes(b) for f, b in bins.items()})
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, os.path.basename(disc.ROM))
    iso.patch(disc.ROM, dst, files); iso.verify(dst, files)
    # ④ 그림(work/gfx — tools/gfx_*.py 가 만듦): 하위 폴더 포함 제자리.
    #    도구를 고치고 다시 안 돌려 옛 그림이 들어간 적이 있다(2026-09-28 «0%» 깨짐) → 빌드 때 항상 전부 다시 만든다
    import subprocess
    for t in ('gfx_chap', 'gfx_btcom', 'gfx_sheet', 'gfx_fuin', 'gfx_omake', 'gfx_stat', 'gfx_mst', 'gfx_opt'):
        subprocess.run([sys.executable, os.path.join(HERE, t + '.py')], check=True, stdout=subprocess.DEVNULL)
    gfx = {p: open(os.path.join(ROOT, 'work', 'gfx', f), 'rb').read() for f, p in GFX.items()
           if os.path.exists(os.path.join(ROOT, 'work', 'gfx', f))}
    mst = sorted(glob.glob(os.path.join(ROOT, 'work', 'gfx', 'MST', '*.CSA')))            # 승리·패배 조건(tools/gfx_mst.py) CH0N_MST###.CSA
    gfx.update({os.path.basename(p).replace('_', '/', 1): open(p, 'rb').read() for p in mst})
    print('그림 %d/%d + 조건 %d' % (len(gfx) - len(mst), len(GFX), len(mst)))
    # ⑤ 동영상 자막(tools/moviesub.py 가 구운 work/kr/<영상>.CPK, 원본 크기 그대로 — 느려서 빌드 때 다시 굽지 않음)
    import moviesub
    mov = {moviesub.disc_path(os.path.basename(p)[:-4]): open(p, 'rb').read()
           for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'kr', '*.CPK')))}
    print('동영상 %d개 %s' % (len(mov), sorted(mov)))
    gfx.update(mov)
    gfx.update(bst_files)                   # ⑥ 전투 맵 스크립트 지형·장애물 이름(파일 크기 그대로)
    iso.patch_sub(dst, gfx)
    print('→', dst)


if __name__ == '__main__':
    main()
