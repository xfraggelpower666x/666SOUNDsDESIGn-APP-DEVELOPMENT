import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from devhub import cli
from devhub.chat_archive import export_markdown, import_archive, search_archive
from devhub.core import DevhubError


def official_chat():
    def message(role, text):
        return {"author": {"role": role}, "content": {"parts": [text, {"asset": "ignored"}]}}

    return {
        "conversation_id": "chat-1", "title": "666DEV Straße", "current_node": "chosen",
        "mapping": {
            "root": {"parent": None, "message": None},
            "question": {"parent": "root", "message": message("user", "Chat-KONTEXT")},
            "alternative": {"parent": "question", "message": message("assistant", "Alternativtext")},
            "chosen": {"parent": "question", "message": message("assistant", "```\n666DEV UPDATE")},
        },
    }


class ChatArchiveTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_official_branch_and_cli_roundtrip(self):
        chat = official_chat()
        malformed = {"title": "Defekt", "current_node": "x", "mapping": {"x": {"parent": "x"}}}
        path = self.root / "export with spaces.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr("conversations-000.json", json.dumps([chat, malformed]))
            archive.writestr("images/image.png", b"ignored")
        with patch.object(cli, "ROOT", self.root):
            command = ["666DEV", "CHAT-ARCHIVE"]
            first = json.loads(cli.execute(command + ["IMPORT", str(path)]))
            self.assertEqual({"added": 1, "unchanged": 0, "skipped": 1,
                              "sources": ["chatgpt-export"]}, first)
            self.assertEqual(1, json.loads(cli.execute(command + ["IMPORT", str(path)]))["unchanged"])
            rows = json.loads(cli.execute(command + ["SEARCH", "STRASSE"]))["results"]
            self.assertEqual(1, len(rows))
            self.assertEqual(2, rows[0]["turns"])
            self.assertEqual(1, len(search_archive(self.root, "chat-kontext")["results"]))
            self.assertFalse(search_archive(self.root, "Alternativtext")["results"])
            markdown = cli.execute(command + ["EXPORT", rows[0]["key"]])

        self.assertIn("chat-1", markdown)
        self.assertIn("````\n```\n666DEV UPDATE\n````", markdown)
        self.assertFalse((self.root / "projects").exists())

    def test_ai_exporter_formats_and_edited_snapshot(self):
        path = self.root / "exporter.zip"
        item = {"id": "chat-2", "title": "Exportiert", "messages": [{"role": "user", "content": "Erste Version"}]}
        universal = {"schema": "ai-exporter-universal", "account_id": "excluded", "conversations": [item]}
        openai = {"object": "chatgpt.export", "data": [item]}
        with ZipFile(path, "w") as archive:
            archive.writestr("openai/conversations.json", json.dumps(openai))
            archive.writestr("universal/conversations.json", json.dumps(universal))
        self.assertEqual(["ai-exporter-universal"], import_archive(self.root, path)["sources"])
        openai_path = self.root / "openai.json"
        openai_path.write_text(json.dumps(openai), encoding="utf-8")
        self.assertEqual(1, import_archive(self.root, openai_path)["unchanged"])

        item["messages"][0]["content"] = "Zweite Version"
        openai_path.write_text(json.dumps(openai), encoding="utf-8")
        self.assertEqual(1, import_archive(self.root, openai_path)["added"])
        search = search_archive(self.root, "Exportiert")
        self.assertEqual(2, len(search["results"]))
        self.assertTrue(any(row["source"] == "ai-exporter-openai" for row in search["results"]))
        self.assertNotIn("excluded", export_markdown(self.root, search["results"][0]["key"]))

    def test_later_malformed_document_rolls_back_prior_rows(self):
        path = self.root / "broken.zip"
        with ZipFile(path, "w") as archive:
            archive.writestr("conversations-000.json", json.dumps([official_chat()]))
            archive.writestr("conversations-001.json", "{")

        with self.assertRaises(DevhubError):
            import_archive(self.root, path)
        self.assertEqual({"results": [], "more": False}, search_archive(self.root))
