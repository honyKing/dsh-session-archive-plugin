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
/** Serializable configuration and defaults for the archive host half. */
export interface Config {
    /**
     * Scripts directory override. When unset, the plugin resolves the packaged
     * `skills/session-archive/scripts` directory from its own package root.
     */
    scriptsDir?: string;
    /** Python executable used to run the archive/search scripts. */
    pythonBin: string;
    /** Timeout (ms) for one archive/search script invocation. */
    timeoutMs: number;
    /** Re-archive gap (MB): skip archiving when the session grew less than this since the last run. */
    reArchiveGapMb: number;
}
export declare const Config: z<Config>;
