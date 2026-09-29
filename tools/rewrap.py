# -*- coding: utf-8 -*-
r"""줄 폭 넘친 대사 다시 접기 (2026-09-29) — 넘친 줄 끝 낱말을 다음 줄 앞으로 민다(앞 줄 그대로).
  그래도 줄 수가 넘치면 전체를 탐욕 접기. 낱말(공백 단위)은 쪼개지 않는다. 안 되면 «손질 필요»로 남김.
  python tools/rewrap.py 번역폴더 ID목록.txt 결과.tsv   → 결과를 tools/applyfix.py 로 반영"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build, dat, applyfix

sys.stdout.reconfigure(encoding='utf-8')


def width(s):
    tk, _ = build.parse(s)
    return max(len(l) for l in build.lines_of(tk))


def limits(i):
    ol = applyfix.ids[i][0].split(b'\n')
    ow = max(len(dat.text_of(l.lstrip(b'\t'))) for l in ol)
    return max(build.LINE_W, min(ow, 24)), max(build.LINES, len(ol))


def cascade(lines, W):
    lines = list(lines); k = 0
    while k < len(lines):
        while width(lines[k]) > W:
            ws = lines[k].split(' ')
            if len(ws) < 2:
                return None
            lines[k] = ' '.join(ws[:-1])
            if k + 1 < len(lines):
                lines[k + 1] = ws[-1] + ' ' + lines[k + 1]
            else:
                lines.append(ws[-1])
        k += 1
    return lines


def greedy(text, W):
    out = []
    for w in text.split(' '):
        if out and width(out[-1] + ' ' + w) <= W:
            out[-1] += ' ' + w
        else:
            if width(w) > W:
                return None
            out.append(w)
    return out


PUNCT = tuple('…!?！？~～、。,.」』)♥') + ('}',)
BOUND = ('님', '씨', '짱', '거', '것', '수', '건', '걸', '게', '줄', '데', '뿐', '때', '적', '돼', '되', '해', '했', '할', '한', '하', '있', '없', '않', '못', '주', '줘', '봐', '버', '말')


def brk_cost(prev, nxt, orig):
    c = 0 if prev.endswith(PUNCT) else 3
    if orig:
        c -= 1
    if nxt.startswith(BOUND) and not prev.endswith(PUNCT):
        c += 8
    if len(prev) == 1:                                     # 「안 / 나 / 할」 따위 한 글자 낱말 뒤
        c += 8
    return c


def best(words, obrk, W, ML):
    n = len(words); INF = 1e9
    dp = [[INF] * (ML + 1) for _ in range(n + 1)]; bk = [[None] * (ML + 1) for _ in range(n + 1)]
    dp[0][0] = 0
    for j in range(1, n + 1):
        for i in range(j):
            w = width(' '.join(words[i:j]))
            if w > W:
                continue
            for k in range(ML):
                if dp[i][k] >= INF:
                    continue
                c = dp[i][k]
                if j < n:
                    c += brk_cost(words[j - 1], words[j], j in obrk) + 0.02 * (W - w) ** 2
                if c < dp[j][k + 1]:
                    dp[j][k + 1] = c; bk[j][k + 1] = i
    k = min(range(1, ML + 1), key=lambda k: dp[n][k])
    if dp[n][k] >= INF:
        return None
    out = []; j = n
    while j:
        i = bk[j][k]; out.append(' '.join(words[i:j])); j = i; k -= 1
    return out[::-1]


def fix(i, t):
    W, ML = limits(i)
    words = []; obrk = set()
    for x in t.split('\\n'):
        if words:
            obrk.add(len(words))
        words += [w for w in x.strip().split(' ') if w]
    if any(width(w) > W for w in words):
        return None
    r = best(words, obrk, W, ML)
    return '\\n'.join(r) if r else None


if __name__ == '__main__':
    import glob
    want = set(open(sys.argv[2], encoding='utf-8').read().split())
    cur = {}
    for p in glob.glob(os.path.join(sys.argv[1], 'yuna3_*.tsv')):
        for ln in open(p, encoding='utf-8').read().split('\n'):
            c = ln.split('\t')
            if len(c) >= 6 and c[0] in want:
                cur[c[0]] = c[5]
    ok = bad = 0
    with open(sys.argv[3], 'w', encoding='utf-8') as f:
        for i in sorted(cur):
            r = fix(i, cur[i])
            if r:
                f.write('%s\t%s\n' % (i, r)); ok += 1
            else:
                print('손질 필요', i, cur[i], limits(i)); bad += 1
    print('다시 접음 %d · 손질 필요 %d' % (ok, bad))
