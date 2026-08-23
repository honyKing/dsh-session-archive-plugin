/**
 * dsh-session-archive — host plugin.
 *
 * Registers the `archive_session` and `search_archive` model-facing tools over
 * the packaged session-archive skill scripts (Python: zstd frame decode of the
 * durable DSH session log, readable archive + full-text retrieval).
 *
 * The plugin ships its own `skills/session-archive` tree; the bundle patch also
 * mounts a `skill-filesystem` provider exposing that tree, so installing the
 * plugin provides the skill AND the tools — no manual `~/.agents/skills` step.
 *
 * @module dsh-session-archive-plugin
 */
import { execFile } from 'node:child_process';
import { dirname, isAbsolute, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineTool } from '@deepseek-ai/dsh-tools';
export { Config } from "./config.js";
export const name = 'dsh-session-archive-plugin';
export const inject = ['tools'];
/** Package root (…/node_modules/dsh-session-archive-plugin). */
const PACKAGE_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
/** Resolve the packaged skill scripts directory (override via config.scriptsDir). */
function resolveScriptsDir(scriptsDir) {
    if (scriptsDir !== undefined) {
        return isAbsolute(scriptsDir) ? scriptsDir : join(process.cwd(), scriptsDir);
    }
    return join(PACKAGE_ROOT, 'skills', 'session-archive', 'scripts');
}
/** Run one python script, capture stdout; resolve {ok, stdout, stderr}. */
function runPython(script, args, config) {
    return new Promise((resolve) => {
        execFile(config.pythonBin, [script, ...args], {
            timeout: config.timeoutMs,
            maxBuffer: 8 * 1024 * 1024,
            windowsHide: true,
            encoding: 'utf8',
        }, (error, stdout, stderr) => {
            if (error)
                resolve({ ok: false, stdout, stderr: String(stderr || error.message) });
            else
                resolve({ ok: true, stdout, stderr });
        });
    });
}
/** Plugin apply: register the two model-facing tools. */
export function apply(ctx, config) {
    const scriptsDir = resolveScriptsDir(config.scriptsDir);
    const archiveScript = join(scriptsDir, 'archive_session.py');
    const searchScript = join(scriptsDir, 'search_archive.py');
    ctx.tools.register(defineTool({
        name: 'archive_session',
        description: 'Archive the current DSH conversation to the workspace session_archives/ directory: decode '
            + 'the durable session log (zstd) into readable plaintext jsonl + markdown summary, with an '
            + 'idempotency guard. Use when the user asks to save/archive the context, or context is large.',
        parameters: {
            sessionId: {
                type: 'string',
                description: 'Optional session id; defaults to the most recent session in the current workspace.',
            },
            statusOnly: {
                type: 'boolean',
                description: 'Only report session size / estimated context usage (%), do not archive.',
            },
        },
        output: {
            schema: {
                type: 'object',
                additionalProperties: false,
                properties: {
                    ok: { type: 'boolean', required: true },
                    output: { type: 'string', required: true },
                    stderr: { type: 'string' },
                },
            },
            render: (_args, value) => [{ type: 'text', text: value.output }],
        },
        async execute(args) {
            const argv = [];
            if (args.sessionId)
                argv.push('--session-id', String(args.sessionId));
            if (args.statusOnly)
                argv.push('--status');
            const r = await runPython(archiveScript, argv, config);
            return { ok: r.ok, output: r.stdout, ...(r.stderr ? { stderr: r.stderr } : {}) };
        },
    }));
    ctx.tools.register(defineTool({
        name: 'search_archive',
        description: 'Full-text search over archived DSH conversations (workspace session_archives/*.md, falling '
            + 'back to decoding the durable session logs under ~/.dsh/sessions). Use when the user asks '
            + 'about something not in the current context ("did we discuss X before?", historical recall).',
        parameters: {
            keywords: {
                type: 'array',
                required: true,
                description: 'Search keywords; all must match (AND).',
                items: { type: 'string' },
            },
            limit: {
                type: 'integer',
                description: 'Max results (default 10).',
            },
            deep: {
                type: 'boolean',
                description: 'Force full scan of recent session logs even when archive summaries match.',
            },
        },
        output: {
            schema: {
                type: 'object',
                additionalProperties: false,
                properties: {
                    ok: { type: 'boolean', required: true },
                    output: { type: 'string', required: true },
                    stderr: { type: 'string' },
                },
            },
            render: (_args, value) => [{ type: 'text', text: value.output }],
        },
        async execute(args) {
            const argv = [...(args.keywords ?? []).map(String)];
            if (args.limit != null)
                argv.push('--limit', String(args.limit));
            if (args.deep)
                argv.push('--deep');
            const r = await runPython(searchScript, argv, config);
            return { ok: r.ok, output: r.stdout, ...(r.stderr ? { stderr: r.stderr } : {}) };
        },
    }));
}
//# sourceMappingURL=index.js.map