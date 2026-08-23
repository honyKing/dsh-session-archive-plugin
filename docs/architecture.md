# 架构说明

本插件是一个标准 DSH **bundle 插件**：一个 npm 包同时提供 host 面（Node 工具）与打包技能，经 `dsh plugin add` 安装后由 profile 组合树挂载。

## 全景

```
┌───────────────────────────── dsh-session-archive-plugin ─────────────────────────────┐
│                                                                                      │
│  package.json  dsh.bundle.patch → cordis.patch.yml（bundle 声明）                    │
│                                                                                      │
│  ┌── host 面（lib/index.js，tsc 产物）─────────────────────────────┐                │
│  │  name: 'dsh-session-archive-plugin'                             │                │
│  │  inject: ['tools']                                              │                │
│  │  apply(ctx, config):                                            │                │
│  │    ctx.tools.register(defineTool({ archive_session }))          │                │
│  │    ctx.tools.register(defineTool({ search_archive }))           │                │
│  │    每个工具 execute → execFile(python, [脚本, args...])          │                │
│  └─────────────────────────────────────────────────────────────────┘                │
│                                                                                      │
│  ┌── 打包技能（skills/session-archive/）───────────────────────────┐                │
│  │  SKILL.md              技能定义（触发场景/用法）                │                │
│  │  scripts/archive_session.py   存档（zstd 逐帧解码→jsonl+md）    │                │
│  │  scripts/search_archive.py    检索（存档→日志直扫）             │                │
│  │  scripts/test_session_archive.py  冒烟测试（unittest）          │                │
│  └─────────────────────────────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## 关键设计

### 1. 工具如何注册

`src/index.ts` 导出 DSH 函数插件四要素：`name`（与 cordis.patch.yml 的 `id` 一致）、
`inject`（声明依赖的 `tools` 服务）、`Config`（schemastery schema，Loader 负责默认值）、
`apply(ctx, config)`。工具经 `ctx.tools.register(defineTool({...}))` 注册，模型即可调用。

工具执行体是**薄封装**：`execFile(python, [脚本, args])` 委托给打包的 Python 脚本。
选择 Python 的原因：zstd 多帧解码 + 大文件全文检索在 Python 里实现直观、易测试，
且不增加 Node 侧依赖（zstandard 是脚本运行环境的事）。

### 2. 技能如何随插件分发

`cordis.patch.yml` 插入两行：

```yaml
- insert:
    - id: session-archive                  # host 插件行
      name: 'dsh-session-archive-plugin'
    - id: session-archive-skill-filesystem # 技能 provider 行
      name: '@deepseek-ai/dsh-skill-filesystem'
      config:
        providerName: session-archive-plugin
        includeDefaultRoots: false
        bundledSkillDir: !!js process.getBuiltinModule('node:path').join(process.getBuiltinModule('node:path').dirname(process.getBuiltinModule('node:module').createRequire(baseUrl).resolve('dsh-session-archive-plugin/package.json')), 'skills')
```

`bundledSkillDir` 用 `!!js` 表达式从 profile 的 Loader `baseUrl` 解析安装后的包根，再拼接
`skills` 目录——与 archify-dsh 同款写法。**`!!js` 必须单行**：多行折叠会被 YAML 解析成
带换行的字符串，profile boot 校验失败。

### 3. 依赖策略：全 peer，零安装

`@deepseek-ai/cordis`、`@deepseek-ai/dsh-tools`、`@deepseek-ai/schemastery` 声明为
**optional peerDependencies**（范围用 rc 兼容写法，如 `>=0.0.1-rc.1`）。运行时由 DSH
profile 的共享 node_modules（`healProfilesModuleFallback` 扁平目录）解析，不重复安装；
npm 上这些包的 `latest` 标签与运行实例版本可能错位，peer + optional 可避免安装期拉错版本。
`pnpm-workspace.yaml` 关闭 `autoInstallPeers`，防止 pnpm 为未发布的内部 peer
（`@deepseek-ai/dsh-type-meta`）硬失败。

开发期类型解析用 `scripts/link-deps.mjs`：在本地 node_modules 建 junction 指向本机 DSH
profile 共享目录，tsc 即可解析类型（源码 import 用 `.ts` 后缀 + `rewriteRelativeImportExtensions`）。

### 4. 构建产物入库

`lib/`（tsc 产物 + `.d.ts`）提交进仓库，`package.json` 的 `main`/`exports` 指向它。
这样 `dsh plugin add <git-url>` 克隆后开箱即用，无需在目标机器上跑构建。
代价是每次 `src/` 变更需同步 `npm run build` 并一起提交（CONTRIBUTING 已要求）。

### 5. 会话数据流

```
DSH 会话日志（~/.dsh/sessions/<ws>/<sid>/session.jsonl.zstd，多帧 zstd，永不清除）
   │  archive_session（工具/技能触发）
   ▼
工作空间 session_archives/  YYYYMMDD_HHMMSS_<sid>.jsonl（明文全量）+ .md（摘要）+ index.md
   │  search_archive（压缩后回退查询）
   ▼
命中片段（时间戳 + 上下文）→ 模型带给用户
```

DSH 原生 `compaction-basic` 在上下文达 80% 时自动压缩（投影替换），但日志文件不删——
本插件补的是**可读存档 + 按需检索**层。
