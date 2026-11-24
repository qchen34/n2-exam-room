#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聴解音声のキュー（区間）抽出手補助。

JLPT の聴解音声は「1 試験＝1 本の連続トラック」なので、問題ごとに
「何秒から何秒まで」を決めておけば、1 ファイルを共有したまま各問題を再生できる。

このスクリプトは ffmpeg の silencedetect で無音区間を拾い、
「長い無音（>= --gap 秒）」を問題の切れ目とみなして区間候補を出す。

使い方:
  python3 tools/cho_cues.py --mp3 "path/to/2026年7月N2.mp3" \
      --label n2-2026-07 --gap 4.5 --out bank/_cues/n2-2026-07.cues.json

出力:
  - 標準出力: 区間表（番号 / 開始 / 終了 / 長さ）
  - JSON: 区間候補（あとで問題文・選択肢・スクリプトと突き合わせて bank を作る）

注意: 無音検出は「問題の切れ目」の候補であって正解ではない。
      最初と最後の数問を実際に聴いて、--gap と開始位置を調整する。
"""
import argparse, json, os, re, subprocess, sys

def detect(mp3, noise, mind):
    cmd = ["ffmpeg", "-hide_banner", "-i", mp3,
           "-af", f"silencedetect=noise={noise}dB:d={mind}", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True)
    log = p.stderr.decode("utf-8", "replace")
    starts = [float(m) for m in re.findall(r"silence_start: (\d+\.?\d*)", log)]
    ends = [float(m) for m in re.findall(r"silence_end: (\d+\.?\d*)", log)]
    n = min(len(starts), len(ends))
    return list(zip(starts[:n], ends[:n]))

def duration(mp3):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", mp3], capture_output=True)
    try:
        return float(p.stdout.decode("utf-8","replace").strip().splitlines()[0])
    except Exception:
        return 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp3", required=True)
    ap.add_argument("--label", default="", help="例: n2-2026-07")
    ap.add_argument("--gap", type=float, default=4.5, help="問題の切れ目とみなす無音の長さ（秒）")
    ap.add_argument("--noise", type=str, default="-32")
    ap.add_argument("--mind", type=float, default=1.5, help="silencedetect の最短無音")
    ap.add_argument("--lead", type=float, default=0.5, help="区間の開始を何秒前からにするか")
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    if not os.path.exists(a.mp3):
        sys.exit(f"ファイルがない: {a.mp3}")
    total = duration(a.mp3)
    sil = [s for s in detect(a.mp3, a.noise, a.mind) if (s[1] - s[0]) >= a.gap]

    segs = []
    prev = 0.0
    for st, en in sil:
        if st - prev >= 8:                      # 短すぎる断片は捨てる
            segs.append((max(0.0, prev - a.lead), st + 0.2))
        prev = en
    if total - prev >= 8:
        segs.append((max(0.0, prev - a.lead), total))

    out = []
    for i, (s, e) in enumerate(segs, 1):
        out.append({"no": i, "s": round(s, 2), "e": round(e, 2), "dur": round(e - s, 1)})

    print(f"{a.mp3}\n  全長 {total:.0f} 秒 / 無音 {len(sil)} か所（>= {a.gap}s）/ 区間 {len(out)} 本")
    print(f"{'#':>3} {'開始':>8} {'終了':>8} {'長さ':>6}")
    for r in out:
        print(f"{r['no']:>3} {r['s']:>8.1f} {r['e']:>8.1f} {r['dur']:>6.1f}")

    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"label": a.label, "mp3": os.path.basename(a.mp3),
                       "total": round(total, 1), "gap": a.gap, "segments": out},
                      f, ensure_ascii=False, indent=1)
        print(f"\n書き出し: {a.out}")

if __name__ == "__main__":
    main()
