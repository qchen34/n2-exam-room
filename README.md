# N2 Exam Room — 日语 N2 刷题台

目标：2027-07-04 N2。自评起点 N4。单文件 HTML + 外置 JSON 题库，可本地双击打开，也可部署到 Vercel 随时随地访问。

## 目录

```
index.html            主程序（单文件：CSS / JS / 内嵌兜底题库）
bank/                 题库（manifest.json 索引 + 各册 JSON）
  manifest.json       索引：按顺序列出所有册子
  n4.json n3.json n2.json        自建模拟册（各 22 题）
  n2-2026-07.json     N2 2026年7月 真题・言語知識（46 题）
  n3-2026-07.json     N3 2026年7月 真题・文字語彙（35 题）
bank.json             旧版一体题库（legacy，HTML 仍可读）
题库制作计划.md        剩余年份的制作流程与排期
source-pdf/           原始真题 PDF 与听力音频（不进 git，见 .gitignore）
_backup/              历史版本（不进 git）
```

## 本地使用

双击 `index.html` 即可。`file://` 下浏览器不允许 fetch 本地 JSON，此时页面使用**内嵌题库**（147 题）；
要在本地用 `bank/` 的最新数据，进「設定 → 題庫データベース → 選んだ冊子で差し替え」手动选 `bank/manifest.json`。

## 部署后（Vercel）

线上是 `https://`，页面启动时会自动 `fetch('bank/manifest.json')` 并按索引加载各册，
失败则回退到内嵌题库。所以：**改题库只需改 `bank/*.json` 并 push，不必重新打包 HTML**。

手动载入过的册子（`S.banks` 无 `src:'server'` 标记）会被尊重，不会被线上数据覆盖；
想回到线上版本，在设置里点「内蔵題庫に戻す」后刷新。

## 题库格式

册子（`bank/xxx.json`）：

```json
{ "id": "jlpt-n2-2026-07", "name": "N2 2026年7月 真题", "level": "N2",
  "updated": "2026-11-20", "count": 46, "questions": [ ... ] }
```

一道题必需 `id / lv / cat / q / opts(4 项) / ans(0–3)`，题干用 `b`（单句）或 `p`（段落数组）之一，
讲解用 `tr`（整题中文译）、`exp`（为什么选它），可选 `notes`（词汇注音）、`g`/`gm`（文法点）、
`qt`/`pt`（设问与段落译）、`ex`（用例）。加册后记得同步 `manifest.json` 的 `count`。

## 进度与记录

答题进度、逐题记录（回数 / 正误 / 连续正解档位 / 下次复习期日）存在浏览器 localStorage，**按设备独立**。
分析页可导出 CSV（逐题记录）与整份 JSON 备份；换设备时用 JSON 备份导入迁移。

## 跨设备同步（Supabase，可选）

不开同步也能用，只是电脑和手机各记各的。开了之后两台设备用**同一个同步码**共享同一份进度。

设置三步：

1. 建一个 Supabase 项目（免费版够用），在 SQL Editor 里执行 `supabase/schema.sql` 全文。
2. 在 Project Settings → API 里复制 **Project URL** 和 **anon public** key。
3. 编辑 `index.html` 顶部的

   ```js
   const SYNC_CFG={url:'',anon:''};
   ```

   填入这两项，提交并重新部署。之后打开网页 → 设置 → 「端末同期」→ 点「同期を有効にする」，页面会给出 8 位代码和 40 位键，记下来（点「コードと鍵をコピー」可直接复制）。

手机端：打开同一个网址 → 设置 → 「他の端末のコードで接続」→ 输入代码 + 键 → 自动把已有记录合并进来。之后每次开始都会自动拉取，答题 6 秒后自动上传。

合并规则（按题、不是按整份文件覆盖）：同一题取「解答回数多的一方」，回数相同取「最后作答时间新的一方」；收藏取并集；逐题记录按（时间, 题号）去重；设置项保持本机。

同步的安全模型：表开启 RLS 且不给任何策略，直连表格一律被拒；只有 `state_get` / `state_put` 两个函数可用，且必须代码 + 键同时匹配。所以 anon key 写在前端也无所谓——没有键就读不到别人的行。

注意免费版 Supabase 约一周无请求会自动暂停，需要进面板恢复；同步失败会 toast 提示，记录本身不会丢在本地。

## 部署步骤

```bash
git init -b main && git add -A && git commit -m "init"
git remote add origin git@github.com:<user>/n2-exam-room.git
git push -u origin main
```

Vercel → Add New Project → Import 该仓库 → Framework Preset: Other，Build Command 留空，Output Directory 留空 → Deploy。

## 注意

`source-pdf/` 为真题原卷扫描件与听力音频（3.3G），**不要提交到公开仓库**；仓库建议设为 private。

## 聴解（听力）的结构

聴解和其他分野的差别只有两点：**题目文本不印在卷面上**，以及**要放音频**。所以数据上多了三个字段，其余（选项、正解、讲解、栞、错题重出、分析）完全复用。

```json
{
  "id": "N2S2607-CH01",
  "lv": "N2",
  "cat": "聴解",
  "au": { "u": "n2-2026-07.mp3", "s": 268.2, "e": 355.7 },
  "q": "女の人はこの後まず何をしますか。",
  "opts": ["…", "…", "…", "…"],
  "ans": 2,
  "sc": "女：…\n男：…",
  "sct": "女：……（中文译文）",
  "exp": "…"
}
```

- `au.u`：音频文件名（相对 `AUDIO_BASE`，也可以直接写完整 URL）；`s` / `e`：这段音频在整条轨道里的起止秒数。**一条考试音频只放一份**，每道题靠 `s`/`e` 切出自己那一段，不用把 45 分钟拆成 30 个文件。
- 播放行为：未作答时按「本番どおり 1 回」只给听一次（设置了可改），播到 `e` 自动停；作答后可以随意重听。
- 未作答时不显示 `q`（设问本来就是念出来的），答完才把设问和 `sc` 一起摊开，`sc` 里的汉字和其余题目一样支持 hover 读音。
- 分析页的「分野」表会自动多出「聴解」一行，和文字·词汇·文法·读解并列；`AUDIO` 属于独立 60 点区分，不影响另两科的百分比含义。

### 音频放哪里

`index.html` 顶部：

```js
const AUDIO_BASE='https://<project>.supabase.co/storage/v1/object/public/audio/';
```

即 Supabase Storage 建一个 **public** 桶 `audio`，把压缩后的考试音频放进去。仓库里不放音频（体积与版权）。

压缩（45MB → 约 11MB，听力练习完全够）：

```bash
ffmpeg -i "2026年7月日语能力考N2-音频.mp3" -ac 1 -b:a 64k -af loudnorm "n2-2026-07.mp3"
```

### 音频切段（生成 s/e）

```bash
python3 tools/cho_cues.py --mp3 "…/2026年7月日语能力考N2-音频.mp3" \
  --label n2-2026-07 --gap 4.5 --out bank/_cues/n2-2026-07.cues.json
```

它用 `silencedetect` 找长于 `--gap` 的静默，把每段「非静默」当作一个候选区间输出（编号 / 开始 / 结束 / 时长）。这些是**候选**，还要和听力原文对一遍：JLPT 结构里有「問題N」的引入句和示例，会混进候选里，需要剔除并把编号对齐到题号。

### 制作顺序（每套 1 次，之后复用）

1. 压缩 + 上传到 `audio` 桶 → 拿到文件名。
2. `cho_cues.py` 出候选区间。
3. 听力原文 PDF（`答案解析和听力原文/`）OCR → 得到每题的原文与选择肢。
4. 把 3 和 2 对齐，写 `bank/{level}-{yyyy}-{mm}-cho.json`，在 `manifest.json` 加一册。
5. 试听前 2 题与最后 1 题，校准 `s`/`e`。
