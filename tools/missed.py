# -*- coding: utf-8 -*-
r"""추출에서 빠진 BIN 문자열 찾기 (2026-09-29) — 앞이 NUL 이 아니라 포인터(0x06……)인 문자열을 extract.py 가 놓쳤다
  (실기: 저장 장치 선택 화면 윗줄 «バックアップを選択してください» 가 옛 한자 코드 그대로 → 엉뚱한 한글).
  각 BIN 에서 NUL 로 끝나는 SJIS 문자열(2바이트 글자 + \n \t %d 따위)을 찾아 ids.tsv 에 없는 것만 찍는다.
  python tools/missed.py        → work/trans/missed.tsv (파일 오프셋 길이 원문)"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.stdout.reconfigure(encoding='utf-8')
W = os.path.join(ROOT, 'work', 'disc')
KANA = re.compile('[\u3040-\u30ff]')
KANJI = re.compile('[\u4e00-\u9fff]')


def covered():
    cov = {}
    for ln in open(os.path.join(ROOT, 'work', 'trans', 'ids.tsv'), encoding='utf-8'):
        x = ln.rstrip('\n').split('\t')
        if x[0].startswith('B'):
            for loc in x[2].split(';'):
                f, o, L = loc.split(':'); cov.setdefault(f, []).append((int(o, 16), int(o, 16) + int(L)))
    return cov


def parse(d, s):
    """s 부터 NUL 까지 — 2바이트 글자·\n·\t·%d 만. 성공하면 (끝, 글자열)"""
    i = s; out = []
    while i < len(d) and d[i]:
        b = d[i]
        if (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF) and i + 1 < len(d) and 0x40 <= d[i + 1] <= 0xFC and d[i + 1] != 0x7F:
            try:
                out.append(d[i:i + 2].decode('cp932'))
            except UnicodeDecodeError:
                return None
            i += 2
        elif b in (0x0A, 0x09):
            out.append(chr(b)); i += 1
        elif b == 0x25 and i + 1 < len(d) and d[i + 1] in b'dsx':
            out.append(chr(b) + chr(d[i + 1])); i += 2
        else:
            return None
    return i, ''.join(out)


def main():
    cov = covered(); res = []
    for f in sorted(os.listdir(W)):
        if not f.upper().endswith('.BIN'):
            continue
        d = open(os.path.join(W, f), 'rb').read(); c = cov.get(f, []); s = 0
        while s < len(d) - 1:
            b = d[s]
            if not (0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF):
                s += 1; continue
            r = parse(d, s)
            if not r:
                s += 1; continue
            e, t = r
            core = t.replace('\n', '').replace('\t', '')
            nk = len(KANA.findall(core)); nj = len(KANJI.findall(core))
            if (nk >= 2 or (nk >= 1 and nj >= 1) or nj >= 3) and not any(x < e and s < y for x, y in c) \
                    and not re.search(r'[\uff61-\uff9f]', t) and len(core) >= 2:
                res.append((f, s, e - s, t))
                s = e + 1; continue
            s += 1
    with open(os.path.join(ROOT, 'work', 'trans', 'missed.tsv'), 'w', encoding='utf-8') as fo:
        for f, s, L, t in res:
            fo.write('%s\t%X\t%d\t%s\n' % (f, s, L, t.replace('\n', '\\n').replace('\t', '\\t')))
    print(len(res))


if __name__ == '__main__':
    main()
