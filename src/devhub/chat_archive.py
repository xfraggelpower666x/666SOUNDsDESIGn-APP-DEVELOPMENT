"""Lokaler Textindex für Chat-Exporte, unabhängig vom Projektzustand."""
from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from .core import DevhubError

MAX_JSON_BYTES = 128 * 1024 * 1024
MAX_IMPORT_BYTES = 512 * 1024 * 1024
MAX_RESULTS = 50
OFFICIAL_MEMBER = re.compile(r"conversations(?:-\d+)?\.json")
EXPORTER_MEMBERS = ("universal/conversations.json", "openai/conversations.json")
ROLES = {"user": "Nutzer", "assistant": "Assistenz"}


def _document(stream):
    with stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise DevhubError("Eine JSON-Datei überschreitet 128 MiB.")
    return json.loads(raw.decode("utf-8-sig"))


def _documents(path: Path):
    if path.suffix.lower() == ".json":
        yield _document(path.open("rb"))
        return
    if path.suffix.lower() != ".zip":
        raise DevhubError("Eine JSON- oder ZIP-Exportdatei auswählen.")
    with ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        selected = sorted((item for item in files if OFFICIAL_MEMBER.fullmatch(item.filename)),
                          key=lambda item: item.filename)
        if not selected:
            for member in EXPORTER_MEMBERS:
                selected = [item for item in files if item.filename == member]
                if selected:
                    break
        if not selected:
            raise DevhubError("Das ZIP enthält kein unterstütztes Chat-Exportformat.")
        if len({item.filename for item in selected}) != len(selected):
            raise DevhubError("Das ZIP enthält doppelte JSON-Einträge.")
        if sum(item.file_size for item in selected) > MAX_IMPORT_BYTES:
            raise DevhubError("Die Chat-JSON-Dateien im ZIP überschreiten zusammen 512 MiB.")
        for item in selected:
            if item.file_size > MAX_JSON_BYTES:
                raise DevhubError("Eine JSON-Datei im ZIP überschreitet 128 MiB.")
            yield _document(archive.open(item))


def _records(document):
    if isinstance(document, list):
        return "chatgpt-export", document
    if isinstance(document, dict):
        if document.get("schema") == "ai-exporter-universal" and isinstance(document.get("conversations"), list):
            return "ai-exporter-universal", document["conversations"]
        if document.get("object") == "chatgpt.export" and isinstance(document.get("data"), list):
            return "ai-exporter-openai", document["data"]
    raise DevhubError("Das JSON entspricht keinem unterstützten Chat-Exportformat.")


def _active_messages(record: dict):
    mapping = record.get("mapping")
    node_id = record.get("current_node")
    if not isinstance(mapping, dict) or not isinstance(node_id, str):
        return []
    messages = []
    visited = set()
    while node_id is not None:
        if not isinstance(node_id, str) or node_id in visited or not isinstance(mapping.get(node_id), dict):
            return []
        visited.add(node_id)
        node = mapping[node_id]
        messages.append(node.get("message"))
        node_id = node.get("parent")
    return reversed(messages)


def _text_messages(record: dict, source: str) -> list[tuple[str, str]]:
    raw = _active_messages(record) if source == "chatgpt-export" else record.get("messages")
    messages = []
    for message in raw or ():
        if not isinstance(message, dict):
            continue
        author = message.get("author")
        role = author.get("role") if isinstance(author, dict) else message.get("role")
        if not isinstance(role, str) or role not in ROLES:
            continue
        content = message.get("content")
        if isinstance(content, dict):
            parts = content.get("parts")
            content = "\n".join(part for part in parts if isinstance(part, str)) if isinstance(parts, list) else None
        if isinstance(content, str) and content.strip():
            messages.append((role, content))
    return messages


def _value(text, fallback=""):
    return text if isinstance(text, str) and text.strip() else fallback


def _database(root: Path) -> Path:
    directory = root.resolve() / ".work" / "chat-archive"
    path = directory / "archive.sqlite3"
    if directory.resolve() != directory or path.resolve() != path:
        raise DevhubError("Der Archivpfad muss im lokalen .work-Verzeichnis liegen.")
    return path


def import_archive(root: Path, path: Path) -> dict:
    database = _database(root)
    added = unchanged = skipped = 0
    sources = set()
    try:
        if str(path).startswith(("//", "\\\\")):
            raise DevhubError("Eine lokale Exportdatei auswählen.")
        path = path.resolve(strict=True)
        if not path.is_file() or str(path).startswith("\\\\"):
            raise DevhubError("Eine lokale Exportdatei auswählen.")
        database.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(database, timeout=15)) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS chats (
                key TEXT PRIMARY KEY, source TEXT NOT NULL, source_id TEXT NOT NULL,
                title TEXT NOT NULL, messages TEXT NOT NULL, search_text TEXT NOT NULL,
                turns INTEGER NOT NULL, characters INTEGER NOT NULL
            )""")
            connection.execute("BEGIN IMMEDIATE")
            for document in _documents(path):
                source, records = _records(document)
                sources.add(source)
                for record in records:
                    if not isinstance(record, dict):
                        skipped += 1
                        continue
                    if source != "chatgpt-export" and not isinstance(record.get("messages"), list):
                        skipped += 1
                        continue
                    messages = _text_messages(record, source)
                    if not messages:
                        skipped += 1
                        continue
                    source_id = _value(record.get("conversation_id")) or _value(record.get("id"))
                    title = _value(record.get("title"), "Ohne Titel")
                    serialized = json.dumps(messages, ensure_ascii=False)
                    key = sha256(json.dumps([source_id, title, messages]).encode("ascii")).hexdigest()
                    text = "\n".join(content for _, content in messages)
                    result = connection.execute(
                        "INSERT INTO chats VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(key) DO NOTHING",
                        (key, source, source_id, title, serialized, f"{title}\n{text}".casefold(),
                         len(messages), sum(len(content) for _, content in messages)),
                    )
                    added += result.rowcount
                    unchanged += 1 - result.rowcount
    except (OSError, ValueError, BadZipFile, RuntimeError, sqlite3.Error) as exc:
        raise DevhubError("Chat-Export konnte nicht vollständig eingelesen werden.") from exc
    return {"added": added, "unchanged": unchanged, "skipped": skipped, "sources": sorted(sources)}


def _read(root: Path, statement: str, parameters: tuple):
    database = _database(root)
    if not database.is_file():
        return []
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(statement, parameters).fetchall()
    except sqlite3.Error as exc:
        raise DevhubError("Das lokale Chat-Archiv ist gerade nicht lesbar.") from exc


def search_archive(root: Path, query: str = "") -> dict:
    if not isinstance(query, str) or len(query) > 500:
        raise DevhubError("Die Suche erlaubt maximal 500 Zeichen.")
    rows = _read(root, """SELECT key, source, substr(title, 1, 300) AS title, turns, characters FROM chats
                 WHERE instr(search_text, ?) > 0 ORDER BY rowid DESC LIMIT ?""",
                 (query.casefold().strip(), MAX_RESULTS + 1))
    return {"results": [dict(row) for row in rows[:MAX_RESULTS]], "more": len(rows) > MAX_RESULTS}


def _quote(text: str) -> str:
    length = max((match.end() - match.start() + 1 for match in re.finditer(r"`+", text)), default=3)
    fence = "`" * max(3, length)
    return f"{fence}\n{text}\n{fence}"


def export_markdown(root: Path, key: str) -> str:
    if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
        raise DevhubError("Einen vollständigen Archivschlüssel angeben.")
    rows = _read(root, "SELECT source, source_id, title, messages FROM chats WHERE key = ?", (key,))
    if not rows:
        raise DevhubError("Der Chat wurde im lokalen Archiv nicht gefunden.")
    row = rows[0]
    sources = f"Quelle: {row['source']}\n\nArchivschlüssel: `{key}`"
    if row["source_id"]:
        sources += f"\n\nQuell-ID\n\n{_quote(row['source_id'])}"
    parts = ["# Chat-Referenz", sources, "## Titel", _quote(row["title"])]
    for role, content in json.loads(row["messages"]):
        parts.extend((f"## {ROLES[role]}", _quote(content)))
    return "\n\n".join(parts) + "\n"
