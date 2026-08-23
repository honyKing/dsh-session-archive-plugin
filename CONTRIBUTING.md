# Contributing / 贡献指南

感谢参与！本插件虽小，但遵循 DSH 社区插件规范开发，欢迎改进。

## 开发环境

- Node.js ≥ 22.19（DSH 要求的版本）
- pnpm（`packageManager` 见 `package.json` 或仓库根 `pnpm-workspace.yaml`）
- Python 3 + `zstandard`（技能脚本运行/测试用）

## 常规流程

```sh
# 1. 安装依赖（仅 devDependencies；@deepseek-ai/* 运行时从 DSH profile 共享 node_modules 解析）
pnpm install

# 2. 开发期类型链接（指向本机 DSH profile 的共享包）
node scripts/link-deps.mjs

# 3. 改代码（src/ 为 TS 源码；skills/session-archive/scripts/ 为 Python 脚本）

# 4. 校验
npm run typecheck          # tsc --noEmit
npm run build              # tsc → lib/
python -m unittest skills/session-archive/scripts/test_session_archive.py -v

# 5. 提交前确认 lib/ 已更新（git 安装依赖仓库内构建产物）
git status                 # lib/*.js 与 lib/types/*.d.ts 应随 src 变更一起提交
```

## 提交规范

- 提交信息用 Conventional Commits 风格：`feat:` / `fix:` / `docs:` / `test:` / `ci:` / `refactor:`。
- 任何 `src/` 变更必须同时提交更新的 `lib/` 产物（`npm run build` 后 `git add lib`）。
- Python 脚本变更必须通过冒烟测试。
- 更新 `CHANGELOG.md`（新功能 / 破坏性变更 / 明显修复）。

## 结构速览

```
src/index.ts        host 插件（Config + archive_session / search_archive 工具注册）
src/config.ts       schemastery 配置 schema
skills/session-archive/   打包技能：SKILL.md + archive/search/test 脚本
scripts/link-deps.mjs     开发期类型链接（junction → DSH profile 共享 @deepseek-ai/*）
lib/                构建产物（入库；git 安装开箱即用）
cordis.patch.yml    bundle 补丁：host 行 + skill-filesystem 行（!!js 必须单行）
```

## 发布检查清单

- [ ] `npm run typecheck` 通过
- [ ] `npm run build` 通过且 `lib/` 已提交
- [ ] Python 冒烟测试通过
- [ ] `pnpm pack` 产物包含 `lib/`、`skills/`、`cordis.patch.yml`、`README.md`
- [ ] CHANGELOG 已更新
- [ ] `dsh plugin add <git-url>` 在新 profile 实测可安装、可加载
