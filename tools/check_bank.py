#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
題庫 JSON の一括検査。

検査項目:
  1. opts が 4 択 / ans が 0..3 の整数
  2. id が重複していない（同じ冊の中／冊をまたいだ全体）
  3. lv が N5..N1、cat が CATS のいずれか
  4. bank/manifest.json の count と、実ファイルの題数が一致
  5. 聴解の問題は au.u があり、s < e になっている
  6. 文字化け・空文字の混入（opts / q / exp が空でない）

使い方:
  python3 tools/check_bank.py            # 全部
  python3 tools/check_bank.py -v         # 冊ごとの内訳も出す
終了コード: 0 = 問題なし, 1 = 不備あり
"""
import argparse, glob, json, os, sys

CATS = ["漢字読み", "語彙", "文法", "読解", "聴解"]
LVS = ["N5", "N4", "N3", "N2", "N1"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def items_of(bank):
    """冊の JSON から問題配列を取り出す（qs / questions / 素の配列に対応）"""
    if isinstance(bank, list):
        return bank
    for k in ("qs", "questions", "items", "q"):
        if isinstance(bank.get(k), list):
            return bank[k]
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    bad = []
    ids = {}
    per_book = {}

    files = sorted(glob.glob(os.path.join(ROOT, "bank", "*.json")))
    for p in files:
        name = os.path.relpath(p, ROOT)
        if os.path.basename(p) == "manifest.json":
            continue
        try:
            bank = load(p)
        except Exception as e:
            bad.append(f"{name}: JSON として読めない（{e}）")
            continue
        qs = items_of(bank)
        per_book[name] = len(qs)
        for i, q in enumerate(qs):
            tag = f"{name} #{i+1}"
            if not isinstance(q, dict):
                bad.append(f"{tag}: 問題がオブジェクトでない")
                continue
            qid = q.get("id")
            if not qid:
                bad.append(f"{tag}: id がない")
            elif qid in ids:
                bad.append(f"{tag}: id 重複 {qid}（{ids[qid]} と）")
            else:
                ids[qid] = name
            if q.get("lv") not in LVS:
                bad.append(f"{tag} {qid}: lv が不正（{q.get('lv')}）")
            if q.get("cat") not in CATS:
                bad.append(f"{tag} {qid}: cat が不正（{q.get('cat')}）")
            opts = q.get("opts")
            if not isinstance(opts, list) or len(opts) not in (3, 4):
                bad.append(f"{tag} {qid}: opts が 3〜4 択でない（{len(opts) if isinstance(opts,list) else type(opts).__name__}）")
            else:
                for j, o in enumerate(opts):
                    if not str(o).strip():
                        bad.append(f"{tag} {qid}: opts[{j}] が空")
            ans = q.get("ans")
            if not isinstance(ans, int) or ans < 0 or ans > 3:
                bad.append(f"{tag} {qid}: ans が 0..3 でない（{ans}）")
            if not str(q.get("q", "")).strip() and q.get("cat") != "聴解":
                bad.append(f"{tag} {qid}: q（設問）が空")
            if not str(q.get("exp", "")).strip():
                bad.append(f"{tag} {qid}: exp（解説）が空")
            if q.get("cat") == "聴解":
                au = q.get("au") or {}
                if not au.get("u"):
                    bad.append(f"{tag} {qid}: 聴解なのに au.u がない")
                s, e = au.get("s"), au.get("e")
                if s is None or e is None:
                    bad.append(f"{tag} {qid}: 聴解なのに s/e がない")
                elif not (0 <= float(s) < float(e)):
                    bad.append(f"{tag} {qid}: s<e になっていない（{s} / {e}）")

    # manifest の count 照合
    mp = os.path.join(ROOT, "bank", "manifest.json")
    if os.path.exists(mp):
        m = load(mp)
        for b in m.get("books", []):
            fn = b.get("file")
            if not fn:
                continue
            path = os.path.join(ROOT, "bank", fn)
            if not os.path.exists(path):
                bad.append(f"manifest: {fn} が存在しない")
                continue
            real = len(items_of(load(path)))
            if b.get("count") != real:
                bad.append(f"manifest: {fn} の count={b.get('count')} だが実際は {real} 問")
    else:
        bad.append("bank/manifest.json がない")

    print(f"検査した冊: {len(per_book)} / 問題: {len(ids)}")
    if a.verbose:
        for k, v in per_book.items():
            print(f"  {k:<36} {v:>4} 問")
    if bad:
        print(f"\n不備 {len(bad)} 件:")
        for x in bad[:80]:
            print("  - " + x)
        if len(bad) > 80:
            print(f"  … 他 {len(bad)-80} 件")
        sys.exit(1)
    print("\n問題なし")

if __name__ == "__main__":
    main()
