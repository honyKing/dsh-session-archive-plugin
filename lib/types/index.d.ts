import { Config } from './config.ts';
export { Config } from './config.ts';
export declare const name = "dsh-session-archive-plugin";
export declare const inject: string[];
/** Plugin apply: register the two model-facing tools. */
export declare function apply(ctx: import('@deepseek-ai/cordis').Context, config: Config): void;
