# -*- coding: utf-8 -*-
"""历史会话存档全文检索脚本（DeepSeek Harness 版）
先搜各工作空间 session_archives/*.md 摘要；无命中时自动解码 ~/.dsh/sessions 下最近的
zstd 会话日志全文检索（DSH 日志永不清除，历史一定找得到）。

用法：
  python search_archive.py 关键词1 [关键词2 ...]   # 多词 AND
  python search_archive.py 关键词 --limit 20        # 限制条数
  python search_archive.py 关键词 --json            # JSON 输出（供技能解析）
  python search_archive.py 关键词 --deep            # 强制全量扫 DSH 会话日志
"""
import os, sys, json, glob, zstandard

SESSIONS_ROOT = os.path.expanduser(r"~\.dsh\sessions")
CTX = 120  # 命中片段前后文长度
MAGIC = b"\x28\xb5\x2f\xfd"
DEEP_SCAN_DEFAULT = 20  # --deep 时扫描最近多少个会话日志


def decode_zstd(path):
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


def is_system_message(obj):
    """跳过系统注入消息与纯推理辅助事件。"""
    src = obj.get("data", {}).get("source") if isinstance(obj, dict) else None
    if isinstance(src, dict):
        kind = src.get("kind")
        plugin = src.get("plugin")
        form = src.get("form")
        if kind in ("plugin", "system") and form in ("snapshot", "catalog"):
            return True
        if plugin in ("@deepseek-ai/dsh-system-prompt", "skill-catalog",
                      "@deepseek-ai/dsh-skill-catalog", "system-prompt"):
            return True
    return False


def conversation_text(text):
    """从解码后的日志文本提取真实对话（user/assistant 消息正文）。"""
    blocks = []
    for line in text.splitlines():
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        t = obj.get("type")
        if t not in ("user/message", "assistant/message"):
            continue
        if is_system_message(obj):
            continue
        content = obj.get("data", {}).get("content")
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
                blocks.append(tx)
    return "\n".join(blocks)


def find_archive_dirs():
    """扫描各工作空间根下的 session_archives 目录（工作空间根由会话 cwd 反推：sessions 目录键）。"""
    dirs = set()
    if os.path.isdir(SESSIONS_ROOT):
        for proj in os.listdir(SESSIONS_ROOT):
            p = os.path.join(SESSIONS_ROOT, proj)
            if not os.path.isdir(p):
                continue
            # 从该工作空间任一日志头取 cwd → 工作空间根 → session_archives
            for root, _, files in os.walk(p):
                if "session.jsonl.zstd" in files:
                    try:
                        events_txt = decode_zstd(os.path.join(root, "session.jsonl.zstd"))
                        for line in events_txt.splitlines()[:3]:
                            obj = json.loads(line)
                            if obj.get("type") == "session" and obj.get("cwd"):
                                d = os.path.join(obj["cwd"], "session_archives")
                                if os.path.isdir(d):
                                    dirs.add(d)
                                break
                    except Exception:
                        pass
                    break
    # 兜底：也扫各盘常见工作空间根
    for drive in ("C:\\Users\\SLIU\\", "E:\\", "D:\\"):
        for cand in glob.glob(os.path.join(drive, "**", "session_archives"), recursive=False):
            if os.path.isdir(cand):
                dirs.add(cand)
    return sorted(dirs)


def search_archives(keywords, limit):
    results = []
    for archive_dir in find_archive_dirs():
        mds = sorted((f for f in glob.glob(os.path.join(archive_dir, "*.md"))
                      if os.path.basename(f) != "index.md"), reverse=True)
        for md in mds:
            base = os.path.basename(md)
            stamp = base[:15] if len(base) >= 15 else base
            try:
                with open(md, "r", encoding="utf-8") as f:
                    text = f.read()
            except (OSError, UnicodeDecodeError):
                continue
            marker = "\n\n### "
            body = text.split(marker, 1)[-1] if marker in text else text
            if not all(k in body for k in keywords):
                continue
            pos = min(p for k in keywords if (p := body.find(k)) >= 0)
            snippet = body[max(0, pos - CTX): pos + CTX].replace("\n", " ").strip()
            results.append({"file": base, "date": stamp, "snippet": snippet,
                            "source": "archive"})
    return results[:limit]


def search_logs(keywords, limit, deep=False):
    """直接解码 DSH 会话日志全文检索（日志永不清除）。"""
    results = []
    logs = []
    for root, _, files in os.walk(SESSIONS_ROOT):
        for fn in files:
            if fn == "session.jsonl.zstd":
                logs.append(os.path.join(root, fn))
    logs.sort(key=os.path.getmtime, reverse=True)
    max_logs = len(logs) if deep else min(DEEP_SCAN_DEFAULT, len(logs))
    for path in logs[:max_logs]:
        try:
            text = conversation_text(decode_zstd(path))
        except Exception:
            continue
        if not all(k in text for k in keywords):
            continue
        pos = min(p for k in keywords if (p := text.find(k)) >= 0)
        snippet = text[max(0, pos - CTX): pos + CTX].replace("\n", " ").strip()
        sid = os.path.basename(os.path.dirname(path))
        mtime = time_str(os.path.getmtime(path))
        results.append({"file": sid, "date": mtime, "snippet": snippet,
                        "source": "session-log"})
    return results[:limit]


def time_str(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y%m%d_%H%M%S")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    keywords = args[:]
    if not keywords:
        print(__doc__)
        return 0
    limit = 10
    if "--limit" in sys.argv:
        i = sys.argv.index("--limit")
        try:
            limit = int(sys.argv[i + 1])
        except (IndexError, ValueError):
            pass
    out_json = "--json" in sys.argv
    deep = "--deep" in sys.argv

    results = search_archives(keywords, limit)
    if not results:
        results = search_logs(keywords, limit, deep=deep)

    if out_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("未在历史存档/会话日志中找到匹配（关键词: %s）。可换更宽泛的词。" % " + ".join(keywords))
        return 0
    print("命中 %d 条:" % len(results))
    for i, r in enumerate(results, 1):
        print("-" * 60)
        print("[%d] %s  (%s · %s)" % (i, r["file"], r["date"], r["source"]))
        print("    %s" % r["snippet"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
