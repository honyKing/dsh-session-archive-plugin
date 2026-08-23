# dsh-session-archive-plugin

[![GitHub](https://img.shields.io/badge/GitHub-honyKing%2Fdsh--session--archive--plugin-181717?logo=github)](https://github.com/honyKing/dsh-session-archive-plugin)
[![Gitee](https://img.shields.io/badge/Gitee-xiyoudada%2Fdsh--session--archive--plugin-C71D23?logo=gitee)](https://gitee.com/xiyoudada/dsh-session-archive-plugin)
[![build](https://github.com/honyKing/dsh-session-archive-plugin/actions/workflows/build.yml/badge.svg)](https://github.com/honyKing/dsh-session-archive-plugin/actions/workflows/build.yml)

DSH 插件：**上下文存档 + 历史检索**。把 `session-archive` 技能打包成正式 DSH bundle 插件——安装插件即同时获得**两个模型工具**和**打包技能**，无需手动配置 `~/.agents/skills`。

## 功能

- **`archive_session`**：把当前 DSH 会话的完整日志（`~/.dsh/sessions/**/session.jsonl.zstd`，多帧 zstd）解码为可读存档：明文 `jsonl` + Markdown 摘要，保存到工作空间 `session_archives/`；幂等（新增不足阈值自动跳过）；`statusOnly` 可只查上下文占用百分比。
- **`search_archive`**：历史全文检索——先搜各工作空间 `session_archives/*.md`，无命中自动解码最近会话日志直扫（DSH 日志永不清除，历史一定找得到）。多词 AND、`limit`、`deep` 参数。
- **打包技能**：`skills/session-archive` 通过 `skill-filesystem` provider 注册，模型按技能描述在压缩后主动回退检索。

## 与 DSH 原生机制的关系

DSH 的 `compaction-basic`（liangshen preset）已原生实现 1M 上下文 80% 自动压缩（`thresholdRatio: 0.8`），无需配置。本插件补上"可读存档 + 事后检索"层，压缩前后信息永不丢失。

## 安装

### 一键安装

```sh
# GitHub（推荐）
dsh plugin --profile web add git+https://github.com/honyKing/dsh-session-archive-plugin.git

# Gitee（国内镜像）
dsh plugin --profile web add git+https://gitee.com/xiyoudada/dsh-session-archive-plugin.git

# npm（发布后可用）
dsh plugin --profile web add dsh-session-archive-plugin
```

> 注意：`github:` / `gitee:` 简写不被 pnpm 支持，必须用完整的 `git+https://...` URL。

### 其他方式

```sh
# 本地目录（开发）
dsh plugin --profile web add E:/path/to/dsh-session-archive-plugin

# 打包安装（.tgz）
pnpm pack
dsh plugin --profile web add ./dsh-session-archive-plugin-<version>.tgz
```

安装后**重启 `dsh web`**，模型即可调用 `archive_session` / `search_archive`，技能同时进入会话技能目录。

## 配置

插件行 `config` 支持（schemastery schema，`src/config.ts`）：

| 键 | 默认 | 说明 |
|---|---|---|
| `scriptsDir` | 打包内 `skills/session-archive/scripts` | 脚本目录覆盖 |
| `pythonBin` | `python` | Python 可执行名 |
| `timeoutMs` | `120000` | 单次脚本调用超时 |
| `reArchiveGapMb` | `1` | 距上次存档新增阈值（MB，幂等） |

在 profile 的 `cordis.patch.yml` 中覆盖：

```yaml
- id: session-archive
  config:
    pythonBin: py
    timeoutMs: 60000
```

## 开发

```sh
node scripts/link-deps.mjs   # 开发期类型链接（@deepseek-ai/* → profile 共享 node_modules）
npm run build                # tsc → lib/（含 .d.ts）
npm run pack                 # build + pnpm pack
python -m unittest skills/session-archive/scripts/test_session_archive.py -v   # 技能脚本冒烟测试
```

> `@deepseek-ai/*` 为 optional peer 依赖，运行时从 DSH profile 的共享 node_modules 解析，不重复安装。

## 结构

```
src/index.ts        host 插件（Config + 工具注册）
src/config.ts       schemastery 配置 schema
scripts/link-deps.mjs  开发期类型链接脚本
skills/session-archive/   打包技能（SKILL.md + Python 脚本 + 冒烟测试）
lib/                构建产物（已入库，git 安装无需构建）
cordis.patch.yml    bundle 补丁（host 行 + skill-filesystem 行）
examples/           配置示例
docs/architecture.md    架构说明
```

> `lib/` 提交进仓库：`dsh plugin add <git-url>` 安装后开箱即用，无需在目标机器上构建。
> 完整开发与发布规范见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可

MIT
