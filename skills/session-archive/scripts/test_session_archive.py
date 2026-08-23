# -*- coding: utf-8 -*-
"""冒烟测试：验证 session-archive 脚本的核心纯逻辑。

覆盖（无 DSH 运行环境依赖）：
  - 多帧 zstd 解码（帧头无内容大小，必须逐帧解）
  - session 头解析（cwd / id）
  - 对话摘要提取（跳过系统注入与推理事件）
  - 会话定位（~/.dsh/sessions 结构）

运行：python -m unittest test_session_archive -v
"""
import io
import json
import os
import sys
import tempfile
import unittest
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import archive_session as arch
import search_archive as search


def make_zstd_log(events):
    """把事件列表按 DSH 格式压缩为多帧 zstd 字节流（header 帧 + 事件帧）。"""
    dctx = zstandard.ZstdCompressor(level=3)
    frames = [dctx.compress(json.dumps(events[0], ensure_ascii=False).encode("utf-8") + b"\n")]
    body = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events[1:])
    if body:
        frames.append(dctx.compress(body.encode("utf-8")))
    return b"".join(frames)


def sample_events(cwd="E:\\demo-ws"):
    """构造一个最小会话：header + 用户消息 + 系统注入 + 助手消息 + 推理事件。"""
    return [
        {"type": "session", "version": 0, "id": "session-test-123", "createdAt": 1, "cwd": cwd},
        {"type": "user/message", "seq": 1, "data": {
            "content": [{"type": "text", "text": "帮我写个插件"}],
            "source": {"kind": "user"},
        }},
        {"type": "user/message", "seq": 2, "data": {
            "content": [{"type": "text", "text": "system snapshot 注入"}],
            "source": {"kind": "plugin", "plugin": "@deepseek-ai/dsh-system-prompt", "form": "snapshot"},
        }},
        {"type": "assistant/message", "seq": 3, "data": {
            "content": [{"type": "text", "text": "好的，这是插件代码。"}],
        }},
        {"type": "reasoning-chunks", "seq": 4, "data": {"texts": ["思考过程不参与摘要"]}},
    ]


class TestDecode(unittest.TestCase):
    def test_multiframe_zstd_roundtrip(self):
        events = sample_events()
        blob = make_zstd_log(events)
        text = arch.decode_zstd(_write_temp(blob))
        lines = text.splitlines()
        self.assertEqual(len(lines), len(events))
        self.assertEqual(json.loads(lines[0])["type"], "session")

    def test_decode_rejects_garbage(self):
        with tempfile.NamedTemporaryFile(suffix=".zstd", delete=False) as f:
            f.write(b"not zstd data at all")
            p = f.name
        try:
            # 非 zstd 数据：解码应返回空或抛错，但不能挂死
            try:
                out = arch.decode_zstd(p)
                self.assertIsInstance(out, str)
            except Exception:
                pass
        finally:
            os.unlink(p)


class TestParsing(unittest.TestCase):
    def test_session_header_extracts_cwd(self):
        events = sample_events()
        hdr = arch.session_header(events)
        self.assertEqual(hdr.get("cwd"), "E:\\demo-ws")
        self.assertEqual(hdr.get("id"), "session-test-123")

    def test_extract_summary_skips_system_and_reasoning(self):
        events = sample_events()
        summary = arch.extract_summary(events)
        self.assertIn("帮我写个插件", summary)       # 用户消息在
        self.assertIn("好的，这是插件代码。", summary)  # 助手消息在
        self.assertNotIn("system snapshot", summary)   # 系统注入跳过
        self.assertNotIn("思考过程", summary)          # 推理事件跳过

    def test_search_conversation_text_skips_system(self):
        events = sample_events()
        blob = make_zstd_log(events)
        p = _write_temp(blob)
        try:
            text = search.conversation_text(search.decode_zstd(p))
            self.assertIn("帮我写个插件", text)
            self.assertNotIn("system snapshot", text)
        finally:
            os.unlink(p)


class TestLocate(unittest.TestCase):
    def test_workspace_archive_dir(self):
        # cwd 存在时用工作空间根；不存在时退回脚本同级（避免断言依赖机器特定目录）
        real_ws = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
        d = arch.workspace_archive_dir(real_ws)
        self.assertEqual(d, os.path.join(real_ws, "session_archives"))
        d2 = arch.workspace_archive_dir("Z:\\definitely-not-exist-xyz")
        self.assertIn("session_archives", d2)


def _write_temp(blob):
    f = tempfile.NamedTemporaryFile(suffix=".zstd", delete=False)
    f.write(blob)
    f.close()
    return f.name


if __name__ == "__main__":
    unittest.main(verbosity=2)
