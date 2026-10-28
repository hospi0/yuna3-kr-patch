# -*- coding: utf-8 -*-
r"""유나 3 음성 ACM → wav (2026-10-28)
  ACM = AIFF 머리(FORM/AIFF·COMM 1채널·4비트·18,900Hz) + 'APCM' 덩어리, 파일 +0x36 부터 CD-XA 식 ADPCM 128 B 묶음
  (2,324 B 섹터마다 묶음 18개 + 빈 20 B · 묶음 머리 16 B: 단위 0‥7 의 [필터<<4 | 시프트] 는 +4‥+11, 데이터 112 B = 28줄 × 4 B, 단위 u 는 줄마다 바이트 u//2 의 낮은/높은 니블, 단위 순서대로 재생)
  python tools/acm.py <ACM…> [--out 폴더]   (기본 work/digest/wav)
"""
import os, struct, sys, wave
K0 = (0, 60, 115, 98, 122)
K1 = (0, 0, -52, -55, -60)


def decode(b):
    assert b[:4] == b'FORM' and b[8:12] == b'AIFF', 'AIFF 아님'
    i = b.find(b'APCM')
    n = struct.unpack_from('>I', b, i + 4)[0]
    data = b[i + 16:i + 8 + n]                     # 'APCM' 크기 칸은 오프셋·블록 크기(8 B) 포함
    out = []; s1 = s2 = 0
    grps = [data[s + k * 128:s + k * 128 + 128] for s in range(0, len(data), 2324) for k in range(18)]   # XA 섹터 = 묶음 18개 + 빈 20 B
    for grp in grps:
        if len(grp) < 128:
            break
        for u in range(8):
            prm = grp[4 + u]; sh = prm & 15; f = min(prm >> 4, 4)
            for j in range(28):
                v = grp[16 + j * 4 + u // 2]
                nb = (v >> 4) if u & 1 else (v & 15)
                if nb >= 8:
                    nb -= 16
                t = (nb << 12) >> sh
                s = t + ((s1 * K0[f] + s2 * K1[f] + 32) >> 6)
                s = max(-32768, min(32767, s))
                out.append(s); s2, s1 = s1, s
    return struct.pack('<%dh' % len(out), *out)


def main():
    args = [a for a in sys.argv[1:] if a != '--out']
    od = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work', 'digest', 'wav')
    if '--out' in sys.argv:
        args.remove(od)
    os.makedirs(od, exist_ok=True)
    for p in args:
        pcm = decode(open(p, 'rb').read())
        w = wave.open(os.path.join(od, os.path.splitext(os.path.basename(p))[0] + '.wav'), 'wb')
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(18900); w.writeframes(pcm); w.close()
        print(os.path.basename(p), '%.2f초' % (len(pcm) / 2 / 18900))


if __name__ == '__main__':
    main()
