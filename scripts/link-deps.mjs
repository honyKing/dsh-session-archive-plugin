/**
 * Development-time type linking for DSH checkouts outside the harness repo.
 * DSH packages are pre-release and not (fully) published on npm; the runtime
 * resolves @deepseek-ai/* from the DSH profile's shared node_modules
 * (healProfilesModuleFallback flat dir). This script creates junctions in the
 * plugin's node_modules pointing at that shared dir so tsc can resolve types.
 *
 * Source: NanmiCoder/dsh-agent-teams docs/developing-dsh-plugins.md §4.2
 * Usage: node scripts/link-deps.mjs
 */
import { existsSync, mkdirSync, symlinkSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')
const SHARED = join(homedir(), '.dsh', 'profiles', 'node_modules', '@deepseek-ai')
const TARGET = join(ROOT, 'node_modules', '@deepseek-ai')

const DEPS = ['cordis', 'dsh-tools', 'schemastery', 'dsh-llm', 'dsh-session']

mkdirSync(TARGET, { recursive: true })
for (const dep of DEPS) {
  const src = join(SHARED, dep)
  const dst = join(TARGET, dep)
  if (!existsSync(src)) {
    console.warn(`skip ${dep}: not in shared dir ${src}`)
    continue
  }
  if (existsSync(dst)) {
    console.log(`exists ${dep}`)
    continue
  }
  try {
    symlinkSync(src, dst, 'junction')
    console.log(`linked ${dep}`)
  } catch (error) {
    console.warn(`link ${dep} failed: ${error.message}`)
  }
}
