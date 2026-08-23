/**
 * dsh-session-archive — host plugin configuration.
 *
 * Serializable configuration and defaults. The Loader validates this schema
 * against the `config` block of the plugin row in cordis.patch.yml (or the
 * profile's own patch layer).
 *
 * @module dsh-session-archive/config
 */
import z from '@deepseek-ai/schemastery';
export const Config = z.object({
    scriptsDir: z.string(),
    pythonBin: z.string().default('python'),
    timeoutMs: z.number().step(1).min(1000).default(120000),
    reArchiveGapMb: z.number().step(1).min(0).default(1),
});
//# sourceMappingURL=config.js.map