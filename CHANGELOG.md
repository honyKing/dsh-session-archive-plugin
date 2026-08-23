# Changelog

## [0.2.0] - 2026-08-23

正式插件化版本：从纯技能升级为 DSH bundle 插件，安装即得工具 + 技能。

### Added

- **`archive_session` 工具**：把当前会话完整日志（多帧 zstd）解码为可读存档（明文 jsonl + Markdown 摘要），保存到工作空间 `session_archives/`；幂等（新增不足阈值自动跳过）；`statusOnly` 可只查上下文占用估算。
- **`search_archive` 工具**：历史全文检索——先搜 `session_archives/*.md`，无命中自动解码最近会话日志直扫；多词 AND、`limit`、`deep` 参数。
- **打包技能**：`skills/session-archive` 随插件分发，通过 `skill-filesystem` provider 注册，无需手动配置 `~/.agents/skills`。
- **Config schema**（schemastery）：`scriptsDir` / `pythonBin` / `timeoutMs` / `reArchiveGapMb`。
- **构建链**：tsc（含 `.d.ts`）、`link-deps.mjs` 开发期类型链接、`pnpm pack` 打包。

### Fixed

- `!!js` 表达式跨多行导致 profile YAML 校验失败 → 改为单行（与 archify-dsh 同款写法）。
- `reArchiveGapMb` 默认值 `0.5` 不符 schemastery `step(1)` 校验 → 改为 `1`。
- peerDependencies 声明与实际 import（`@deepseek-ai/schemastery`）不一致 → 修正为 rc 兼容范围。
- `lib/` 构建产物入库：git 安装开箱即用，无需目标机器构建。

### Changed

- 依赖全部 optional peer（运行时从 DSH profile 共享 node_modules 解析，不重复安装）。
- 一键安装命令 GitHub 优先，Gitee 作为国内镜像。

## [0.1.0] - 2026-08-23

技能原型（`~/.agents/skills/session-archive`）：zstd 会话日志解码、可读存档、全文检索脚本。
