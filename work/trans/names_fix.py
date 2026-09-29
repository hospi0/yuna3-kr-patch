# -*- coding: utf-8 -*-
"""받은 번역 이름 통일 (2026-09-29) — 이름표 work/test_tsv/names_map.tsv(사용자 확인 2026-09-28)
 ① 화자 머리 «이름「»: 원문 화자 → 이름표 이름, 「 앞 공백 삭제
 ② 본문: 흔한 낱말과 안 겹치는 번역자 변형만 바꿈. 흔한 낱말과 겹치는 것(항상·국화·동백꽃·광화·환몽)은
    원문에 그 한자 이름이 있는 줄에서만 바꾼다.
 python work/trans/names_fix.py"""
import csv, glob, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPK = {'ポリリーナ': '폴리리나', '亜耶乎': '아야코', '鏡明': '쿄메이', '玉華': '굣카', '白香': '뱌카', '剣鳳': '켄포', '剣凰': '켄포',
       '狂花': '쿄카', '幻夢': '겐무', '菊花': '킷카', '美鬼': '미키', '項翔': '코쇼', '鈴魔': '린마', '桃花': '토우카',
       '沙雪華': '사유카', '椿花': '친카', '麗美': '레이미', 'アレフチーナ': '알레프치나', 'ユーリィ': '유리', '姫': '히메',
       'ロックの姫': '히메', '桜花': '오우카', '蘭花': '란카', '紫陽花': '아지사이', '劉麗': '류레이'}
BODY = [('포리리나', '폴리리나'), ('아야오', '아야코'), ('경명', '쿄메이'), ('백향', '뱌카'), ('시라카', '뱌카'),
        ('켄호우', '켄포'), ('켄호', '켄포'), ('켄오', '켄포'), ('쿄우카', '쿄카'), ('키쿠카', '킷카'), ('미오니', '미키'),
        ('코우쇼우', '코쇼'), ('스즈마', '린마'), ('모모카', '토우카'), ('사유키카', '사유카'), ('레이메이', '레이미'),
        ('알레프티나', '알레프치나'), ('유리이', '유리'), ('교카', '굣카')]
RISKY = [('項翔', '항상', '코쇼'), ('菊花', '국화', '킷카'), ('椿花', '동백꽃', '친카'), ('狂花', '광화', '쿄카'), ('幻夢', '환몽', '겐무')]
pat = re.compile('^([^「\\\\]{1,14})「')
n = {'화자': 0, '공백': 0}
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'trans', 'recv', 'yuna3_*.tsv'))):
    L = open(p, encoding='utf-8').read().split('\n'); ch = False
    for k, ln in enumerate(L):
        c = ln.split('\t')
        if len(c) < 6:
            continue
        t = c[5]
        mo = pat.match(c[4]); mk = pat.match(t)
        if c[0].startswith('D') and mo and mk:
            want = SPK.get(mo.group(1))
            cur = mk.group(1)
            new = want if want else cur.rstrip(' 　')
            if new != cur:
                n['화자' if want and cur.strip() != want else '공백'] += 1
                t = new + t[len(cur):]
        for a, b in BODY:
            if a in t:
                n[a] = n.get(a, 0) + t.count(a); t = t.replace(a, b)
        for jp, a, b in RISKY:
            if jp in c[4] and a in t:
                n[a] = n.get(a, 0) + t.count(a); t = t.replace(a, b)
        if t != c[5]:
            c[5] = t; L[k] = '\t'.join(c); ch = True
    if ch:
        open(p, 'w', encoding='utf-8').write('\n'.join(L))
print(n)
