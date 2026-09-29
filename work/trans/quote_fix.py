# -*- coding: utf-8 -*-
"""받은 번역의 반각 '…' 쌍 → 원문 『…』 (2026-09-29). 원문에 『 가 있고 ' 가 짝수인 줄만. 나머지는 목록만 찍는다.
 python work/trans/quote_fix.py [--write]"""
import glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'trans', 'recv', 'yuna3_*.tsv'))):
    L = open(p, encoding='utf-8').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 6 or "'" not in c[5]:
            continue
        t = c[5]
        if '『' in c[4] and t.count("'") % 2 == 0:
            t = re.sub(r"'([^']*)'", r'『\1』', t)
            print('고침', c[0], t); n += 1
            c[5] = t; L[k] = '\t'.join(c); ch = True
        else:
            print('그대로', c[0], c[4], '|', t)
    if ch and '--write' in sys.argv:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
print(n)
