# 把 skill 迁到服务器

skill-runner 用服务用户（zxw）的 `~/.claude/skills` 里的 skill，每次运行的工作目录是
`$SKILL_RUNNER_HOME/runs/<run_id>/`，Claude 的 Bash 在沙箱里跑：只能写运行目录和
`SKILL_RUNNER_EXTRA_WRITE` 里的路径，网络只放行 `SKILL_RUNNER_ALLOWED_DOMAINS`。
下面是三个 skill 里绑死在 Windows 本机上的地方，以及在服务器上的改法。

## 共同准备

```bash
sudo apt-get install -y bubblewrap socat ffmpeg fonts-noto-cjk
# Ubuntu 24.04 若 `sysctl kernel.apparmor_restrict_unprivileged_userns` 为 1，给 bwrap 加 AppArmor 配置：
sudo tee /etc/apparmor.d/bwrap >/dev/null <<'PROFILE'
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
  include if exists <local/bwrap>
}
PROFILE
sudo systemctl reload apparmor
mkdir -p ~/.claude/skills
```

skill 从本机同步过去（`.env.local` 不用带：两个 skill 都优先读环境变量，密钥写进 skill-runner 的 env 文件）。

各 skill 的 Python 依赖装进 `~/skill-runner/tools` 这个 venv：服务把它排在 PATH 最前面，
沙箱里执行的 `python` 就是它（Ubuntu 24.04 的系统 Python 不允许直接 pip install）。

## four-step-translate

| 本机写死的地方 | 服务器上的处理 |
| --- | --- |
| `output_root: C:/Users/DELL/Documents/semiAnalysis` | 写 `~/.four-step-translate/EXTEND.md`，把 `output_root` 设为 `.`，产出落在运行目录里，页面上可下载。不用改 SKILL.md |
| `~/Desktop/translation_agent/glossary/...`、`~/Desktop/translation_agent/scripts/sync_glossary_to_skill.py` | `mkdir -p ~/Desktop && ln -s /home/zxw/translation-agent ~/Desktop/translation_agent`（指向生产词表所在的目录，以服务器实际为准） |
| 术语沉淀会写全局词表、重新生成 `references/glossary-en-zh.md` | 两处的**真实路径**都加进 `SKILL_RUNNER_EXTRA_WRITE` |
| `scripts/html2md.py` 依赖 | `~/skill-runner/tools/bin/pip install beautifulsoup4 markdownify` |

## video-bilingual-subber

这个 skill 要求「工作目录固定为 `C:\Users\DELL\Desktop\semi-video`」，和「每次运行一个目录」冲突，**必须改 SKILL.md**：

- 第 26–29 行：工作目录改为「当前目录（本次运行目录）」；`subs/`、`output/`、`final_videos/`、`downloads/` 都建在当前目录下，成品留在当前目录的 `final_videos/`。
- 所有 `python scripts/xxx.py` 改为 `python ${CLAUDE_SKILL_DIR}/scripts/xxx.py`（脚本在 skill 目录里，不在工作目录里）。
- `.env` 一条删掉：`GEMINI_API_KEY` 由 skill-runner 的 env 文件提供，命令会继承。
- 依赖：`~/skill-runner/tools/bin/pip install -r ~/.claude/skills/video-bilingual-subber/requirements.txt`；`yt-dlp` 要能从服务器访问 YouTube。
- 压字幕很吃 CPU、耗时长；如果单条命令超过 Bash 工具的时限，让 Claude 用后台命令执行（Claude Code 自带）。

## podcast-cn-dubber

- 第 19 行 `WORK=C:\Users\DELL\Desktop\podcast_en\<集数slug>` 改为「当前目录」；跨集共享的 `glossary.json` 放到 `~/podcast_en/glossary.json`，并把 `~/podcast_en` 加进 `SKILL_RUNNER_EXTRA_WRITE`。
- 密钥：`DASHSCOPE_API_KEY`、`DASHSCOPE_WS_URL` 可以继续放在 skill 目录的 `.env.local`，也可以写进 skill-runner 的 env 文件。
- `scripts/synth.py` 用 websocket 连 TTS 网关。沙箱只通过 HTTP(S) 代理放行网络，websocket 客户端如果不读代理环境变量就连不上：先跑一集试试，连不上再把它加进 `SKILL_RUNNER_UNSANDBOXED_COMMANDS`（见 `deploy/env.example`），同时把网关域名加进 `SKILL_RUNNER_ALLOWED_DOMAINS`。
- 依赖：`~/skill-runner/tools/bin/pip install dashscope imageio-ffmpeg requests`。

## 验证

每个 skill 迁完先在页面上跑一个最小样本（短文章、一分钟视频、一小段播客），看三件事：
沙箱有没有拦截（页面上会出现「已拦截」提示）、产出是否落在运行目录（右栏能下载）、关卡是否停下来等你。
