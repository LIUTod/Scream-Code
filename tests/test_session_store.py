from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from src.session_store import StoredSession, load_session, most_recent_saved_session_id, save_session


class SessionStoreTests(unittest.TestCase):
    def test_most_recent_saved_session_id_by_mtime(self) -> None:
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.chdir(tmp)
                save_session(
                    StoredSession(
                        session_id='older',
                        messages=('a',),
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
                time.sleep(0.02)
                save_session(
                    StoredSession(
                        session_id='newer',
                        messages=('b',),
                        input_tokens=1,
                        output_tokens=2,
                    )
                )
                self.assertEqual(most_recent_saved_session_id(), 'newer')
        finally:
            os.chdir(old)

    def test_save_session_writes_scream_index(self) -> None:
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.chdir(tmp)
                save_session(
                    StoredSession(
                        session_id='idx_sid',
                        messages=('a',),
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
                idx = Path(tmp) / '.scream' / 'sessions.json'
                self.assertTrue(idx.is_file())
                loaded = json.loads(idx.read_text(encoding='utf-8'))
                self.assertEqual(loaded.get('latest_session_id'), 'idx_sid')
        finally:
            os.chdir(old)

    def test_roundtrip_llm_conversation_messages(self) -> None:
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.chdir(tmp)
                snap = ({'role': 'assistant', 'content': '你好'},)
                save_session(
                    StoredSession(
                        session_id='snap1',
                        messages=('u1',),
                        input_tokens=1,
                        output_tokens=2,
                        llm_conversation_messages=snap,
                    )
                )
                loaded = load_session('snap1')
                self.assertEqual(loaded.llm_conversation_messages, snap)
        finally:
            os.chdir(old)

    def test_most_recent_none_when_empty(self) -> None:
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.chdir(tmp)
                self.assertIsNone(most_recent_saved_session_id())
        finally:
            os.chdir(old)


if __name__ == '__main__':
    unittest.main()
