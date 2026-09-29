# -*- coding: utf-8 -*-
r"""유나 3 — 번역용 원문 추출 (2026-09-28)
  ① 대사: YUNA3.DAT 텍스트 자리 전부(tools/dat.py) — 같은 문장(탭 들여쓰기 빼고 같은 바이트)은 한 줄로, «공유» = 쓰인 곳 수
     표기: 줄바꿈 \n(뒤따르는 탭 들여쓰기는 뺀다 — 빌더가 화자 이름 폭에 맞춰 다시 넣음) · 외자 {!!} {!?} {♥} {怒} {汗} · 그 밖의 비표준 2바이트 {XXXX}
  ② 실행 파일·BIN 문자열: 0.BIN·TITLE.BIN·LONGMAP.BIN·OMAKE.BIN·GAME.BIN — NUL 앞이 NUL, 모든 2바이트 글자가 게임 글꼴에 있고(코드→TBL 연결) 가나·한자 2자 이상
     → 제자리(원래 바이트 이하), 구분 «최대 NB»
  출력: my files/tsv/yuna3_NNN.tsv (ID·위치·구분·공유·원문·번역, 29KB 단위, 자투리는 앞 파일에 합침)
        work/trans/ids.tsv (ID → 원문 바이트 hex · 위치 목록 «블록:오프셋» 또는 «파일:오프셋:길이»)
"""
import collections, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dat

W = os.path.join(ROOT, 'work', 'disc')
TSV = os.path.join(ROOT, 'my files', 'tsv')
GAIJI = {'{9873}': '{!!}', '{9874}': '{!?}', '{9876}': '{♥}', '{987A}': '{怒}', '{987B}': '{汗}'}
BINS = ['0.BIN', 'TITLE.BIN', 'LONGMAP.BIN', 'OMAKE.BIN', 'GAME.BIN']
SPECIAL = {0x9FCC: 0xE66, 0x9980: 0xE67, 0x98A5: 0xE68, 0x9D98: 0xE69, 0xE34A: 0xE6A, 0xE2A4: 0xE6B, 0xE3C4: 0xE6C, 0xE587: 0xE6D}
JPC = re.compile('[぀-ヿ一-鿿]')
LIMIT = 29 * 1024


def show(raw):
    """원문 바이트 → TSV 표기(탭 들여쓰기 뺌, 외자 이름)"""
    t = dat.text_of(re.sub(rb'\n\t+', b'\n', raw))
    for k, v in GAIJI.items():
        t = t.replace(k, v)
    return t


def glyph_ok(exe, tbl):
    def ok(c):
        if 0x8100 <= c <= 0x987E:
            i = struct.unpack_from('>H', exe, 0x0609A560 - 0x06004000 + 2 * (((c >> 8) - 0x81) * 0xC0 + (c & 0xFF)))[0] - 256
        elif c in SPECIAL:
            i = SPECIAL[c] - 256
        else:
            return False
        return 0 <= i < 6000 and tbl[i] != 0xFFFF
    return ok


def bin_strings(b, ok):
    out = []
    for m in re.finditer(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x09\x0a\x20-\x7e])+\x00', b):
        s = m.group()[:-1]; a = m.start()
        if a > 0 and b[a - 1] != 0:
            continue
        good = True; nj = 0; i = 0
        while i < len(s):
            if s[i] >= 0x81:
                c = s[i] << 8 | s[i + 1]
                if not ok(c):
                    good = False; break
                nj += JPC.match(dat.text_of(s[i:i + 2])) is not None; i += 2
            else:
                i += 1
        if good and nj >= 2:
            out.append((a, s))
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    exe = open(os.path.join(W, '0.BIN'), 'rb').read()
    tbl = struct.unpack('<6000H', open(os.path.join(W, 'YUNA3.TBL'), 'rb').read())
    rows = []; ids = []
    # ① 대사
    groups = collections.OrderedDict(); kinds = collections.defaultdict(set)
    KIND = {0x5002: '대사', 0x50B7: '전투대사', 0x2013: '메뉴', 0x1017: '디버그'}     # 그 밖의 텍스트 자리 = «글»(선택지 등)
    for b in dat.blocks():
        opat = {}
        for p, op, fl, a in b.ins:
            for q in range(p, p + 4 + 2 * len(a)):
                opat[q] = op
        refs = collections.Counter(o for _, o in b.text_refs())
        byoff = collections.defaultdict(set)
        for pos, o in b.text_refs():
            byoff[o].add('디버그' if b.b0 == 0 else KIND.get(opat[pos], '글'))     # 블록 0 = 디버그 메뉴
        for o, x in b.strings.items():
            if b.is_jp(o) and refs[o]:
                key = re.sub(rb'\n\t+', b'\n', x)
                groups.setdefault(key, []).append(('%X:%X' % (b.b0, o), x)); kinds[key] |= byoff[o]
    for k, (key, locs) in enumerate(groups.items(), 1):
        i = 'D%05d' % k
        kd = kinds[key] - {'디버그'} or {'디버그'}
        rows.append((i, locs[0][0], '·'.join(sorted(kd)), str(len(locs)), show(key)))
        ids.append((i, key.hex(), ' '.join('%s=%s' % (l, x.hex()) if x != key else l for l, x in locs)))
    # ② BIN
    ok = glyph_ok(exe, tbl); n = 0
    for f in BINS:
        b = open(os.path.join(W, f), 'rb').read()
        for a, s in bin_strings(b, ok):
            n += 1; i = 'B%05d' % n
            rows.append((i, '%s:%X' % (f, a), '%s 최대%dB' % ('실행파일' if f == '0.BIN' else f, len(s)), '1', show(s)))
            ids.append((i, s.hex(), '%s:%X:%d' % (f, a, len(s))))
    os.makedirs(TSV, exist_ok=True); os.makedirs(os.path.join(ROOT, 'work', 'trans'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('ID\t원문hex\t위치\n' + ''.join('\t'.join(r) + '\n' for r in ids))
    head = 'ID\t위치\t구분\t공유\t원문\t번역\n'
    parts = [[]]; size = 0
    for r in rows:
        ln = '\t'.join(r) + '\t\n'; nb = len(ln.encode('utf-8'))
        if size + nb > LIMIT and parts[-1]:
            parts.append([]); size = 0
        parts[-1].append(ln); size += nb
    if len(parts) > 1 and sum(len(x.encode('utf-8')) for x in parts[-1]) < LIMIT // 3:
        parts[-2] += parts.pop()
    for k, p in enumerate(parts, 1):
        with open(os.path.join(TSV, 'yuna3_%03d.tsv' % k), 'w', encoding='utf-8', newline='\n') as f:
            f.write(head + ''.join(p))
    nd = sum(1 for r in rows if r[0][0] == 'D')
    print('대사 %d줄(쓰인 곳 %d) · BIN %d줄 · 글자 %d · 파일 %d개 → %s' % (
        nd, sum(int(r[3]) for r in rows if r[0][0] == 'D'), n, sum(len(r[4]) for r in rows), len(parts), TSV))


if __name__ == '__main__':
    main()
