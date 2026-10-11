# -*- coding: utf-8 -*-
r"""육화전·사천기 이름을 공식 읽기로 바꾸기(2026-10-11, 하스피 «gemanizm 엔니미 데이터 참고해서 유나 이름들 수정»)
  출처: https://gemanizm.main.jp/retrogamejaxx/game_yuna2.html (work/ref/game_yuna2.html, Shift_JIS)
    菊花 ジェイ・ファー · 桜花 イン・ファー · 蘭花 ラン・ファー · 椿花 チュン・ファー · 桃花 タウ・ファー · 紫陽花 ツー・ヤン・ファー
    劉麗 リオ・リー · 項翔 シャン・シャン · 美鬼 メイ・クイ · 鈴魔 リン・マオ   (幻夢・狂花 는 읽기 없음 → 그대로)
  바꾸는 줄 = 원문에 그 한자 이름이 있는 줄만(«미키»는 銀幕のミキ 와 겹치므로) · 받침 바뀌는 이름(코쇼→샨샨)은 뒤 조사도 맞춤.
  python tools/rename_bosses.py [--write]   (my files/tsv/yuna3_*.tsv · work/test_tsv/names_map.tsv, 백업 work/trans/tsv_before_rename)
"""
import glob, os, re, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MAP = [('紫陽花', '아지사이', '츠얀파'), ('菊花', '킷카', '제이파'), ('桜花', '오우카', '인파'), ('蘭花', '란카', '란파'),
       ('椿花', '친카', '춘파'), ('桃花', '토우카', '타우파'),
       ('劉麗', '류레이', '리오리'), ('項翔', '코쇼', '샨샨'), ('美鬼', '미키', '메이쿠이'), ('鈴魔', '린마', '린마오')]
JOSA = [('는', '은'), ('가', '이'), ('를', '을'), ('와', '과'), ('로', '으로'), ('야', '아'), ('여', '이여'), ('랑', '이랑'), ('나', '이나'), ('라고', '이라고'), ('라는', '이라는')]


def has_batchim(s): return (ord(s[-1]) - 0xAC00) % 28 != 0


def sub(text, old, new):
    if has_batchim(old) == has_batchim(new):
        return text.replace(old, new)
    def f(m):
        j = m.group(1) or ''
        for a, b in JOSA:
            if j == a: return new + b
        return new + j
    alt = '|'.join(re.escape(a) for a, _ in sorted(JOSA, key=lambda x: -len(x[0])))
    return re.sub(re.escape(old) + r'(%s)?(?![가-힣])' % alt if False else re.escape(old) + r'(%s)?' % alt, f, text)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    files = sorted(glob.glob(os.path.join(ROOT, 'my files', 'tsv', 'yuna3_*.tsv'))) + [os.path.join(ROOT, 'work', 'test_tsv', 'names_map.tsv')]
    n = 0; warn = []
    out = {}
    for p in files:
        lines = open(p, encoding='utf-8').read().split('\n'); new = []
        for ln in lines:
            c = ln.split('\t')
            if len(c) >= 2:
                src, ko = (c[4], c[5]) if len(c) >= 6 else (c[0], c[1])
                ko2 = ko
                for kj, old, nw in MAP:
                    if kj in src and old in ko2:
                        ko2 = sub(ko2, old, nw)
                    elif old in ko2 and kj not in src and old != '미키':
                        warn.append('%s: 원문에 %s 없음 «%s»' % (os.path.basename(p), kj, ko))
                if ko2 != ko:
                    n += 1; print('%s\n  %s\n→ %s' % (src[:40], ko, ko2))
                    if len(c) >= 6: c[5] = ko2
                    else: c[1] = ko2
                    ln = '\t'.join(c)
            new.append(ln)
        out[p] = '\n'.join(new)
    print('바뀐 줄', n)
    for w in warn: print('⚠', w)
    if '--write' in sys.argv:
        bk = os.path.join(ROOT, 'work', 'trans', 'tsv_before_rename'); os.makedirs(bk, exist_ok=True)
        for p, s in out.items():
            shutil.copy(p, os.path.join(bk, os.path.basename(p)))
            open(p, 'w', encoding='utf-8', newline='').write(s)
        print('썼음 · 백업', bk)


if __name__ == '__main__':
    main()
