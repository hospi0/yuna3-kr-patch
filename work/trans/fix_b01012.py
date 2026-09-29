# -*- coding: utf-8 -*-
"""B01012 원문 칸에 실개행이 들어간 줄 바로잡기 (2026-09-29) + B01009 지면 칸 맞춤 공백"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = os.path.join(ROOT, 'my files', 'tsv', 'yuna3_010.tsv')
s = open(p, encoding='utf-8', newline='').read()
a = s.index('B01012\t'); b = s.index('\nB01013\t')
row = s[a:b].replace('\r', '').replace('\n', '\\n')
s = s[:a] + row + s[b:]
L = s.split('\n')
for k, ln in enumerate(L):
    c = ln.split('\t')
    if c[0] == 'B01009':
        c[5] = '지면　　　　'; L[k] = '\t'.join(c)
open(p, 'w', encoding='utf-8', newline='').write('\n'.join(L))
print(row)
