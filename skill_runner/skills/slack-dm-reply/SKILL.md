---
name: slack-dm-reply
description: Reads a Slack direct-message conversation exported by momo (slack-dm.md plus slack-history.json with me/them roles), explains in Chinese what the other person wants, and recommends three English replies (casual / standard / formal) using momo's slack-reply pipeline; then revises them from the user's Chinese instructions. Writes result.json for the momo Slack page. Never sends anything to Slack. Use when momo's Slack page hands over a DM, or the user says 帮我回这条私信、推荐 Slack 回复.
---

# Slack 私信回复助手

momo 的 Slack 页给每个私信配一个你。用户在右栏看你的建议、用中文跟你说怎么改，选好后自己复制到 Slack 发送。
**你从不往 Slack 发任何东西**，也不要编造用户没说过的承诺、日期、进度。

输入：附件 `slack-dm.md`（最近 30 条，按时间正序，作者带「（我）」的是用户本人）和 `slack-history.json`
（`[{"role": "me"|"them", "content": "..."}]`，同样的顺序）。

`MOMO=/home/zxw/releases/translation-agent-current`（线上 momo 的 CLI，服务在 `http://127.0.0.1:54321`）。
运行目录里的环境带着给外网用的 HTTP(S)_PROXY，连本机服务前先：

```bash
export MOMO=/home/zxw/releases/translation-agent-current NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
```

## 1. 找出待回复的内容

- 取最后一条「我」的消息之后、对方发来的所有消息，合起来就是待回复内容。
- 最后一条就是我发的（没有待回复）：用 2–3 句中文概括最近在聊什么，写进 result.json（`pending` 为 false，
  `replies` 为空），告诉用户目前不需要回复；用户之后说想主动发什么，就按下面「之后」的方式写。

## 2. 生成建议回复

```bash
python3 - <<'PY'
import json
h = json.load(open("slack-history.json"))
last_me = max((i for i, m in enumerate(h) if m["role"] == "me"), default=-1)
json.dump(h[:last_me + 1][-20:], open("history-before.json", "w"), ensure_ascii=False)
open("pending.txt", "w").write("\n\n".join(m["content"] for m in h[last_me + 1:]))
PY
$MOMO/slack-reply --mode incoming --json --history history-before.json -f pending.txt > reply.json
```

返回 JSON：`translation` 是对方消息的中文理解，`suggested_replies` 是 A/B/C 三版（`english`、`chinese`）。
失败就把错误原样告诉用户，不要自己凭空编。

## 3. 写 result.json（momo 页面读这个文件显示结果卡片，每次修改后都要重写）

```json
{
  "type": "dm_reply",
  "pending": true,
  "understanding": "对方在说什么、要我做什么（中文，1–3 句）",
  "replies": [
    {"version": "A", "label": "随意", "english": "...", "chinese": "..."},
    {"version": "B", "label": "标准", "english": "...", "chinese": "..."},
    {"version": "C", "label": "正式", "english": "...", "chinese": "..."}
  ]
}
```

## 4. 回复用户

简短中文：先一句对方要什么，再列三版英文（每版下面一行中文意思）。最后提示可以直接用中文告诉你想怎么回。

## 之后用户用中文提要求时

- 用户给了自己的意思（「告诉他周五前给」「委婉拒绝」「问一下具体要哪几张图」）：
  把意思写进 `draft.txt`，跑 `$MOMO/slack-reply --mode compose --json --history slack-history.json -f draft.txt > reply.json`，
  用返回的 `versions` 重写 result.json 的 `replies`。
- 「再短一点」「别那么正式」这类只改措辞的要求：直接改三版英文和对应中文，不改意思、不加承诺。
- 每次都重写 result.json，再简短说改了什么。
