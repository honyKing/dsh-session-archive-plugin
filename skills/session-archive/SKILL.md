---
name: session-archive
description: |
  上下文存档与历史回退检索技能（DeepSeek Harness 版）。DSH 使用 deepseek 1M 端点（contextWindow=1000000），上下文占用达到 80%（800k tokens）时 compaction-basic 会自动压缩。本技能负责"压缩前完整存档 + 压缩后从历史找回"的规则化机制：
  1. 存档：把当前会话完整对话（明文 jsonl）+ 可读摘要（md）解码保存到工作空间 session_archives\（DSH 的原始日志 session.jsonl.zstd 本身永不清除，本技能生成可读副本供检索）
  2. 自动压缩：DSH 原生 compaction 在 80% 自动触发（thresholdRatio 0.8），无需人为操作
  3. 回退检索：压缩后若用户问的事在当前上下文/记忆里找不到答案，从历史存档（或直接解码 DSH 会话日志）全文检索找回

  触发场景：用户说"保存上下文"、"存档会话"、"上下文满了"、"压缩整理"、"整理上下文"、"上下文健康"、"检查上下文"、"永久记忆"、"之前说过X吗"、"查历史记录"、"从历史找X"、"我们上次说了什么"、"这个之前讨论过吗"、"上次怎么处理的"、"找出之前关于X的对话"。
  不触发：与历史上下文无关的普通问答、单只股票分析、选股、盯盘（那些用对应技能）。
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
metadata:
  author: DSH
  version: "2.0"
  last_updated: "2026-08-23"
---

# 上下文存档技能（DeepSeek Harness 版）

你负责管理"上下文存档 → 自动压缩 → 历史回退检索"的完整链路，保证用户在任何时候问起**之前会话里说过/做过的事**，都能从历史存档找回，即使当前上下文已被压缩。

## 背景机制（DSH 原生已自动化）

- **容量限制**：对话模型为 deepseek 1M 端点，`contextWindow = 1000000` tokens。
- **自动压缩（无需人为操作）**：`compaction-basic` 在每次 step 前自动检查压力，占用达到 **80%**（`thresholdRatio: 0.8`，约 800k tokens）时自动压缩，保留最近 16% 尾部；触发 context-overflow 时也会强制压缩。`/compact` 可手动触发。
- **原始日志永不清除**：每次会话的完整事件日志持久化在 `~/.dsh/sessions/<工作空间键>/<session-id>/session.jsonl.zstd`（多帧 zstd 压缩），压缩只替换对话投影，日志文件不删除——所以"完整对话"在 DSH 里永远可找回。
- **本技能的价值**：把 zstd 日志解码为**可读存档**（明文 jsonl + md 摘要），并提供**全文检索**入口，让压缩后回退查询又快又直观。

## 存档（手动触发 / 用户要求时）

用户明确要求或上下文偏大时，运行：

```bash
python <技能目录>/scripts/archive_session.py [--session-id <id>]
```

- 不带参数：自动定位**当前工作空间最新**会话的 `session.jsonl.zstd`。
- 存档输出到当前工作空间根目录的 `session_archives\`：
  - `YYYYMMDD_HHMMSS_<session-id>.jsonl` — 完整明文对话记录
  - 同名 `.md` — 可读摘要（user/assistant 文本）
  - `index.md` — 存档索引
- 幂等：同一会话新增内容不足阈值时跳过，避免重复存档。

## 自动压缩（DSH 原生，技能只负责告知用户）

- 上下文占用达 80% 时 compaction-basic 自动触发，**无需任何人为操作**。
- 若用户问"上下文多少了"：运行 `python <技能目录>/scripts/archive_session.py --status` 查看当前会话大小与估算占用。
- 压缩后当前上下文只保留摘要，完整信息在 `session_archives\` 与 `~/.dsh/sessions\`。

## 回退检索（核心）

当用户问的事在当前上下文/记忆里找不到答案时，**主动**运行：

```bash
python <技能目录>/scripts/search_archive.py "关键词1" "关键词2"
```

- 先搜各工作空间 `session_archives\*.md` 摘要；无命中时自动解码 `~/.dsh/sessions\` 下最近若干会话的 zstd 日志全文检索（DSH 日志永不清除，所以历史一定找得到）。
- 多词自动 AND；可加 `--limit N` 控制条数、`--json` 取结构化结果、`--deep` 强制全量扫日志。
- 命中即返回时间戳 + 上下文片段，把命中的对话带给用户。

## 关键约定

- 脚本用 Python 3 + `zstandard` 库逐帧解码（DSH 日志是多帧 zstd，帧头无内容大小，必须逐帧解）。
- 会话定位：默认取 `~/.dsh/sessions\` 下 mtime 最新的 `.jsonl.zstd`；`--session-id` 精确指定。
- 检索跳过系统注入消息（system-prompt / skill-catalog / runtime context）与纯推理块，只搜真实对话文本。
- 重要结论还应同步写入工作空间的 `CLAUDE.md` / `AGENTS.md` 或记忆文件，双保险。
