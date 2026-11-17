---
name: slack-post-translate
description: Reads one Slack thread exported by momo (slack-thread.md), works out which content in it is meant to be translated (the root post, a quoted X/Twitter post in a link card, or numbered 1/N…N/N parts, taking the latest re-edited version), translates it with momo's post-translation pipeline (glossary, hashtags) and generates Chinese title candidates. Writes result.json for the momo Slack page. Use when momo's Slack page hands over a channel thread, or the user says 翻译这个 thread、翻译 Slack 帖子、slack 帖子翻译.
---

# Slack 帖子翻译助手

momo 的 Slack 页给每个频道 thread 配一个你。用户在右栏看你的结果、用中文跟你说怎么改。**你从不往 Slack 发任何东西。**

输入：附件 `slack-thread.md`（momo 导出的 thread：第一条是根消息，之后是回复；作者带「（我）」的是用户本人；
链接卡片里是被引用帖子的原文；每条都有原文链接）。

`MOMO=/home/zxw/releases/translation-agent-current`（线上 momo 的 CLI，服务在 `http://127.0.0.1:54321`）。
运行目录里的环境带着给外网用的 HTTP(S)_PROXY，连本机服务前先：

```bash
export MOMO=/home/zxw/releases/translation-agent-current NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
```

## 1. 找出要翻译的内容

按顺序判断，**只翻要发出去的内容，不翻讨论**：

1. 根消息是转发 / 发帖请求（「plz RT this」「can u RT」「post this」「QRT」，或只 @ 了用户组再贴链接），
   且带 X / Twitter 等链接卡片 → 要翻的是**链接卡片里的帖子原文**；根消息里请求之外还有自己的正文时一并翻。
2. 根消息本身就是一篇帖子（成段的观点、数据、标题行）→ 翻根消息正文。
3. 根消息或回复里有 `1/N … N/N`、`(1/3)`、`*1/*` 这类编号分段 → 按编号拼成一篇。同一编号出现多次
   （「let me reedit it」「done, i re-edited it」之后又贴了一遍）时，每个编号取**最新**的那一版。
4. 其余回复（「will post, thanks」「lol」、改动意见）只用来判断上面几条，不翻。

清理：去掉 Slack 的 @提及、@用户组、转发请求用语、链接里的跟踪参数（`?s=46`、`&t=…`），保留数字、单位、专有名词原样。

拿不准时（同时有两段都像要发的、链接卡片被截断只剩半句等）用 AskUserQuestion 让用户选，推荐项放第一个，
每个选项的说明里放候选内容的前 80 个字符。

整个 thread 都只是聊天、没有要翻的内容：用 2–3 句中文概括这个 thread 在说什么，写进 result.json 的 `summary`，
`translation` 留空，结束。

## 2. 翻译

```bash
cat > source.txt <<'EOF'
<要翻译的英文>
EOF
$MOMO/translate-post -f source.txt --json > translation.json
```

用返回 JSON 的 `translation`（已带术语库和话题标签处理）。失败就把错误原样告诉用户，不要自己凭空翻。

## 3. 标题候选

```bash
python3 - <<'PY'
import json, urllib.request
zh = json.load(open("translation.json"))["translation"]
req = urllib.request.Request("http://127.0.0.1:54321/api/generate/title",
    data=json.dumps({"content": zh}).encode(), headers={"Content-Type": "application/json"})
titles = [t.strip() for t in json.load(urllib.request.urlopen(req, timeout=190))["title"].splitlines() if t.strip()]
json.dump(titles, open("titles.json", "w"), ensure_ascii=False)
PY
```

## 4. 写 result.json（momo 页面读这个文件显示结果卡片，每次修改后都要重写）

```json
{
  "type": "post_translation",
  "summary": "一句话说明翻的是什么，例如：翻译了根消息转发的 vLLM 的 X 帖（2 段）",
  "source_text": "实际送去翻译的英文",
  "translation": "中文译文",
  "titles": ["标题候选 1", "标题候选 2"],
  "permalink": "根消息的原文链接"
}
```

## 5. 回复用户

简短中文：第一行说翻了什么（和 summary 一致），然后给出译文和标题候选。不要复述流程。

## 之后用户用中文提要求时

- 「这段不用翻」「把第三段也加上」「只翻 X 帖」→ 改 source.txt，重跑第 2、3 步。
- 「语气口语一点」「这句不通顺」「标题再短点」→ 直接改译文或标题（术语保持不变），不用重跑接口。
- 每次都重写 result.json，再简短说改了什么。
