# dsh-session-archive-plugin

DSH 插件：**上下文存档 + 历史检索**。把 `session-archive` 技能打包成正式 DSH bundle 插件——安装插件即同时获得**两个模型工具**和**打包技能**，无需手动配置 `~/.agents/skills`。

## 功能

- **`archive_session`**：把当前 DSH 会话的完整日志（`~/.dsh/sessions/**/session.jsonl.zstd`，多帧 zstd）解码为可读存档：明文 `jsonl` + Markdown 摘要，保存到工作空间 `session_archives/`；幂等（新增不足阈值自动跳过）；`statusOnly` 可只查上下文占用百分比。
- **`search_archive`**：历史全文检索——先搜各工作空间 `session_archives/*.md`，无命中自动解码最近会话日志直扫（DSH 日志永不清除，历史一定找得到）。多词 AND、`limit`、`deep` 参数。
- **打包技能**：`skills/session-archive` 通过 `skill-filesystem` provider 注册，模型按技能描述在压缩后主动回退检索。

## 与 DSH 原生机制的关系

DSH 的 `compaction-basic`（liangshen preset）已原生实现 1M 上下文 80% 自动压缩（`thresholdRatio: 0.8`），无需配置。本插件补上"可读存档 + 事后检索"层，压缩前后信息永不丢失。

## 安装

```sh
# 本地目录（开发）
dsh plugin --profile web add E:/path/to/dsh-session-archive-plugin

# 打包发布（npm）
npm run pack            # 产出 .tgz
dsh plugin --profile web add ./dsh-session-archive-plugin-0.2.0.tgz
```

安装后**重启 `dsh web`**，模型即可调用 `archive_session` / `search_archive`。

## 配置

插件行 `config` 支持（schemastery schema，`src/config.ts`）：

| 键 | 默认 | 说明 |
|---|---|---|
| `scriptsDir` | 打包内 `skills/session-archive/scripts` | 脚本目录覆盖 |
| `pythonBin` | `python` | Python 可执行名 |
| `timeoutMs` | `120000` | 单次脚本调用超时 |
| `reArchiveGapMb` | `0.5` | 距上次存档新增阈值（幂等） |

在 profile 的 `cordis.patch.yml` 中覆盖：

```yaml
- id: session-archive
  config:
    pythonBin: py
    timeoutMs: 60000
```

## 开发

```sh
npm run build     # esbuild → lib/index.js
npm run pack      # build + pnpm pack
```

## 结构

```
src/index.ts        host 插件（Config + 工具注册）
src/config.ts       schemastery 配置 schema
scripts/build.mjs   esbuild 构建（@deepseek-ai/* 与 schemastery 走 peer 解析）
skills/session-archive/   打包技能（SKILL.md + Python 脚本）
cordis.patch.yml    bundle 补丁（host 行 + skill-filesystem 行）
```

## 许可

MIT
