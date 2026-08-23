# Changelog

## [0.3.0] - 2026-08-23

### Added

- **冒烟测试**：`skills/session-archive/scripts/test_session_archive.py`（6 个用例：多帧 zstd 往返、会话头解析、摘要过滤系统/推理事件、检索正文过滤、工作空间存档目录定位）。
- **CI 工作流**：`.github/workflows/build.yml`——typecheck + build + 产物校验 + Python 语法与冒烟测试。
- **CONTRIBUTING.md**：开发/提交/发布规范（Conventional Commits、lib 同步提交、发布清单）。
- **docs/architecture.md**：插件架构说明（host 工具 + skill-filesystem 分发 + peer 依赖策略 + 数据流）。
- **examples/cordis.patch.yml**：配置覆盖示例。
- README 增加 build 徽章、测试运行说明；`files` 发布清单纳入 `examples/`、`docs/`、`CHANGELOG.md`。

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
