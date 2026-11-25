#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
題庫 JSON の一括検査。

検査項目:
  1. opts が 3〜4 択 / ans が選択肢の範囲内の整数
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
import argparse, glob, json, math, os, re, sys

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
    if not isinstance(bank, dict):
        return []
    for k in ("qs", "questions", "bank", "items", "q"):
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
        if not qs:
            bad.append(f"{name}: 問題がない")
        if isinstance(bank, dict) and "count" in bank and bank["count"] != len(qs):
            bad.append(f"{name}: count={bank['count']} だが実際は {len(qs)} 問")
        for i, q in enumerate(qs):
            tag = f"{name} #{i+1}"
            if not isinstance(q, dict):
                bad.append(f"{tag}: 問題がオブジェクトでない")
                continue
            qid = q.get("id")
            if not isinstance(qid, str) or not qid.strip():
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
                    if not isinstance(o, str) or not o.strip():
                        bad.append(f"{tag} {qid}: opts[{j}] が空")
            ans = q.get("ans")
            if type(ans) is not int or not isinstance(opts, list) or not 0 <= ans < len(opts):
                bad.append(f"{tag} {qid}: ans が opts の範囲外（{ans}）")
            if not str(q.get("q", "")).strip() and q.get("cat") != "聴解":
                bad.append(f"{tag} {qid}: q（設問）が空")
            if not str(q.get("exp", "")).strip():
                bad.append(f"{tag} {qid}: exp（解説）が空")
            if "pt" in q and (not isinstance(q.get("p"), list) or not isinstance(q["pt"], list) or len(q["p"]) != len(q["pt"])):
                bad.append(f"{tag} {qid}: pt の段落数が p と合わない")
            if "figure" in q:
                figure = q["figure"]
                src = figure.get("src", "") if isinstance(figure, dict) else ""
                alt = figure.get("alt", "") if isinstance(figure, dict) else ""
                if not (isinstance(src, str) and re.fullmatch(r"bank/figures/[a-z0-9-]+\.webp", src) and os.path.isfile(os.path.join(ROOT, src))):
                    bad.append(f"{tag} {qid}: 図版ファイルが見つからない（{src}）")
                if not isinstance(alt, str) or not alt.strip():
                    bad.append(f"{tag} {qid}: 図版の説明がない")
            if q.get("cat") == "聴解":
                au = q.get("au")
                if not isinstance(au, dict):
                    au = {}
                if not isinstance(au.get("u"), str) or not au["u"].strip():
                    bad.append(f"{tag} {qid}: 聴解なのに au.u がない")
                s, e = au.get("s"), au.get("e")
                if not (type(s) in (int, float) and type(e) in (int, float) and math.isfinite(s) and math.isfinite(e) and 0 <= s < e):
                    bad.append(f"{tag} {qid}: 0 <= s < e になっていない（{s} / {e}）")

    # manifest の count 照合
    mp = os.path.join(ROOT, "bank", "manifest.json")
    if os.path.exists(mp):
        try:
            manifest = load(mp)
        except (OSError, ValueError) as e:
            manifest = None
            bad.append(f"manifest.json: 読み込みに失敗（{e}）")
        entries = manifest.get("banks") if isinstance(manifest, dict) else None
        if not isinstance(entries, list) or not entries:
            bad.append("manifest.json: banks が空または形式が不正")
            entries = []
        files_declared = set()
        for b in entries:
            fn = b.get("file") if isinstance(b, dict) else None
            if not isinstance(fn, str) or not re.fullmatch(r"[A-Za-z0-9._-]+\.json", fn):
                bad.append(f"manifest: file が不正（{fn}）")
                continue
            if fn in files_declared:
                bad.append(f"manifest: file が重複（{fn}）")
            files_declared.add(fn)
            name = os.path.join("bank", fn)
            if name not in per_book:
                bad.append(f"manifest: {fn} が見つからないか、読み込めない")
                continue
            real = per_book[name]
            if type(b.get("count")) is not int or b["count"] != real:
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
