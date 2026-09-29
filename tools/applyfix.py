# -*- coding: utf-8 -*-
r"""손질 번역(ID \t 새 번역) 검사 → 통과분만 번역 폴더에 반영 (2026-09-29)
  대사(D): 줄 수 ≤ max(3, 원문) · 줄 폭 ≤ max(18, 원문 최장, 상한 24) · 글자. BIN(B): 바이트 ≤ 원래 자리.
  python tools/applyfix.py 번역폴더 손질.tsv [--write]"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build, dat

sys.stdout.reconfigure(encoding='utf-8')
folder = os.path.abspath(sys.argv[1])
ids = build.load_ids()


def check(i, t):
    tk, e = build.parse(t)
    errs = list(e)
    raw = ids[i][0]
    if i[0] == 'D':
        ol = raw.split(b'\n'); nl = build.lines_of(tk)
        ow = max(len(dat.text_of(l.lstrip(b'\t'))) for l in ol)
        maxw = max(build.LINE_W, min(ow, 24)); maxl = max(build.LINES, len(ol))
        if len(nl) > maxl:
            errs.append('줄 %d > %d' % (len(nl), maxl))
        errs += ['%d번 줄 %d칸 > %d' % (k, len(l), maxw) for k, l in enumerate(nl) if len(l) > maxw]
    else:
        L = int(ids[i][1][0].split(':')[2]); n = sum(2 if x[0] == 'g' else len(x[1]) if x[0] == 'c' else 1 for x in tk)
        if n > L:
            errs.append('%dB > 자리 %dB' % (n, L))
    return errs


if __name__ == '__main__':
    new = {}
    for ln in open(sys.argv[2], encoding='utf-8').read().split('\n'):
        if '\t' in ln:
            i, t = ln.split('\t', 1); new[i.strip()] = t.rstrip('\r')
    good = {}
    for i, t in new.items():
        e = check(i, t)
        if e:
            print('✗', i, t, '; '.join(e))
        else:
            good[i] = t
    print('통과 %d · 실패 %d' % (len(good), len(new) - len(good)))
    if '--write' in sys.argv:
        n = 0
        for p in sorted(glob.glob(os.path.join(folder, 'yuna3_*.tsv'))):
            L = open(p, encoding='utf-8').read().split('\n'); ch = False
            for k, ln in enumerate(L):
                c = ln.split('\t')
                if len(c) >= 6 and c[0] in good and c[5] != good[c[0]]:
                    c[5] = good[c[0]]; L[k] = '\t'.join(c); ch = True; n += 1
            if ch:
                open(p, 'w', encoding='utf-8').write('\n'.join(L))
        print('반영 %d줄' % n)
