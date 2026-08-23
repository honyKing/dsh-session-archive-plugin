# -*- coding: utf-8 -*-
"""DSH 会话存档脚本：把当前会话的 zstd 日志解码为明文 jsonl + 可读摘要，保存到工作空间 session_archives/。

DSH 会话日志：~/.dsh/sessions/<工作空间键>/<session-id>/session.jsonl.zstd
- 多帧 zstandard 压缩（帧头无内容大小，必须逐帧解码）
- 日志永不清除：压缩只替换对话投影，原始事件流一直保留

用法：
  python archive_session.py                  # 定位当前工作空间最新会话并存档
  python archive_session.py --session-id <id> # 指定会话
  python archive_session.py --status          # 查看当前会话大小与估算占用（不存档）
  python archive_session.py --reason <x>      # 兼容 hooks 调用（忽略原因）
"""
import os, sys, json, glob, time, zstandard

SESSIONS_ROOT = os.path.expanduser(r"~\.dsh\sessions")
REARCHIVE_GAP_MB = 0.5   # 距上次存档新增 ≥0.5MB 才再次存档
# 80% ≈ 800k tokens，按约 6.5 字节/token 标定（deepseek 1M 端点，含开销）
WARN_BYTES = int(800000 * 6.5)
MAGIC = b"\x28\xb5\x2f\xfd"


def _utf8(text):
    return text.encode("utf-8", errors="replace").decode("utf-8")


def decode_zstd(path):
    """逐帧解码 DSH 会话日志（多帧 zstd），返回明文文本。"""
    with open(path, "rb") as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    out = b""
    off = 0
    while off < len(data):
        if data[off:off + 4] != MAGIC:
            break
        dobj = dctx.decompressobj()
        chunk = dobj.decompress(data[off:])
        out += chunk
        off += len(data[off:]) - len(dobj.unused_data)
        if not dobj.unused_data:
            break
    return out.decode("utf-8", errors="replace")


def parse_events(text):
    events = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        events.append(obj)
    return events


def session_header(events):
    """取 session 头（cwd / id / createdAt）。"""
    for ev in events:
        if ev.get("type") == "session":
            return ev
    return {}


def find_workdir(sid):
    """按 session-id 或最新 mtime 在 ~/.dsh/sessions 下定位日志文件，返回 (path, cwd, sid)。"""
    candidates = []
    if sid:
        for root, _, files in os.walk(SESSIONS_ROOT):
            for fn in files:
                if fn == "session.jsonl.zstd" and sid in os.path.basename(root):
                    candidates.append(os.path.join(root, fn))
    if not candidates:
        for root, _, files in os.walk(SESSIONS_ROOT):
            for fn in files:
                if fn == "session.jsonl.zstd":
                    candidates.append(os.path.join(root, fn))
    if not candidates:
        return None, None, None
    path = max(candidates, key=os.path.getmtime)
    sid = os.path.basename(os.path.dirname(path))
    cwd = None
    try:
        events = parse_events(decode_zstd(path))
        hdr = session_header(events)
        cwd = hdr.get("cwd")
    except Exception:
        pass
    return path, cwd, sid


def extract_summary(events):
    """提取 user/assistant 真实对话文本（跳过系统注入与推理块）。"""
    parts = []
    for ev in events:
        t = ev.get("type")
        if t == "user/message":
            role = "USER"
        elif t == "assistant/message":
            role = "ASSISTANT"
        else:
            continue
        content = ev.get("data", {}).get("content")
        src = ev.get("data", {}).get("source", {})
        # 跳过系统注入消息（system-prompt / skill-catalog / runtime context 等）
        if isinstance(src, dict) and src.get("kind") in ("plugin", "system"):
            if isinstance(src, dict) and src.get("plugin") in (
                "@deepseek-ai/dsh-system-prompt", "@deepseek-ai/dsh-skill-catalog",
                "skill-catalog", "system-prompt",
            ):
                continue
            if src.get("kind") == "plugin" and src.get("form") in ("snapshot", "catalog"):
                continue
        texts = []
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
        for tx in texts:
            tx = tx.strip()
            if tx:
                parts.append("### %s ###\n%s" % (role, tx))
    return "\n\n".join(parts)


def workspace_archive_dir(cwd):
    """按会话所属工作空间返回存档目录；cwd 未知时退回脚本同级的 session_archives。"""
    if cwd and os.path.isdir(cwd):
        return os.path.join(cwd, "session_archives")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "session_archives")


def load_state(archive_dir, sid):
    p = os.path.join(archive_dir, ".state", sid + ".json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(archive_dir, sid, size):
    state_dir = os.path.join(archive_dir, ".state")
    os.makedirs(state_dir, exist_ok=True)
    p = os.path.join(state_dir, sid + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"last_size": size, "time": time.strftime("%Y-%m-%d %H:%M:%S")}, f,
                  ensure_ascii=False, indent=2)


def archive(src_path, cwd, sid):
    archive_dir = workspace_archive_dir(cwd)
    os.makedirs(archive_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base = "%s_%s" % (stamp, sid[:36])
    json_dst = os.path.join(archive_dir, base + ".jsonl")
    md_dst = os.path.join(archive_dir, base + ".md")

    text = decode_zstd(src_path)
    with open(json_dst, "w", encoding="utf-8") as f:
        f.write(text)

    events = parse_events(text)
    summary = extract_summary(events)
    with open(md_dst, "w", encoding="utf-8") as f:
        f.write("# 会话存档 %s (会话 %s · 工作空间 %s)\n\n" % (stamp, sid[:8], cwd or "未知"))
        f.write("> 完整对话记录: %s\n\n" % os.path.basename(json_dst))
        f.write(summary if summary else "（无文本对话）")

    size_mb = os.path.getsize(src_path) / 1048576
    idx = os.path.join(archive_dir, "index.md")
    first_line = ""
    for seg in summary.split("\n\n"):
        if "### " in seg and "\n" in seg:
            first_line = seg.split("\n", 1)[1].strip().replace("|", "/")
            if first_line:
                break
    idx_row = "| %s | %s | %s | %.1fMB | %s |" % (
        stamp[:8] + " " + stamp[9:], cwd or "?", sid[:8], size_mb, first_line[:50])
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as f:
            f.write("# 会话存档索引\n\n| 时间 | 工作空间 | 会话 | 大小 | 摘要 |\n|------|------|------|------|------|\n" + idx_row + "\n")
    else:
        with open(idx, "a", encoding="utf-8") as f:
            f.write(idx_row + "\n")

    save_state(archive_dir, sid, os.path.getsize(src_path))
    return json_dst, md_dst, size_mb


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    sid = None
    if "--session-id" in args:
        i = args.index("--session-id")
        if i + 1 < len(args):
            sid = args[i + 1]

    src_path, cwd, found_sid = find_workdir(sid)
    if not src_path:
        print("未找到会话日志（%s）" % SESSIONS_ROOT)
        return 1
    sid = found_sid

    if "--status" in args:
        size = os.path.getsize(src_path)
        pct = min(100.0, size / WARN_BYTES * 100)
        print("当前会话: %s" % sid)
        print("工作空间: %s" % (cwd or "未知"))
        print("日志大小 : %.1f MB" % (size / 1048576))
        print("估算占用: %.0f%% (按 80%% ≈ %.1f MB 标定)" % (pct, WARN_BYTES / 1048576))
        print("自动压缩 : DSH compaction-basic 在 80%% 自动触发，无需人为操作")
        return 0

    size = os.path.getsize(src_path)
    archive_dir = workspace_archive_dir(cwd)
    last = load_state(archive_dir, sid).get("last_size", 0)
    if size - last < REARCHIVE_GAP_MB * 1048576 and last > 0:
        print("会话 %s 距上次存档新增不足 %.1fMB，跳过（幂等）" % (sid, REARCHIVE_GAP_MB))
        return 0

    print("存档当前会话 %s (%s)..." % (sid, src_path))
    json_dst, md_dst, size_mb = archive(src_path, cwd, sid)
    print("已完成存档:")
    print("  jsonl: %s (%.1fMB)" % (json_dst, size_mb))
    print("  摘要 : %s" % md_dst)
    print("  说明: 之后问题若在压缩上下文找不到答案，运行 search_archive.py \"关键词\" 从历史找回")
    return 0


if __name__ == "__main__":
    sys.exit(main())
