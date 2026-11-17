"""Lesende Auswertung von Entwicklungsmanifesten und zweisprachigen Kartenpaketen."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from .core import DevhubError, STATUSES

MAX_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 256
CORE_SECTIONS = {
    "format_version", "vorlage", "anwendungshinweis", "projekt", "ziele", "produktion",
    "rechte", "evidenz", "entscheidungen", "entwicklungsvorschlaege", "auswertung",
    "eintragsvorlagen",
}
EVIDENCE_ALIASES = {"typ": "art", "quelle_oder_pfad": "quelle_oder_datei", "datum": "pruefdatum"}


def read_object(payload: bytes) -> dict:
    def unique(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("JSON object has duplicate keys.")
        return result

    result = json.loads(payload, object_pairs_hook=unique)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object.")
    return result


def read_cards(path: Path) -> tuple[dict, int]:
    with zipfile.ZipFile(path) as bundle:
        files = [item for item in bundle.infolist() if not item.is_dir()]
        if len(files) > MAX_ARCHIVE_ENTRIES or sum(item.file_size for item in files) > MAX_BYTES:
            raise ValueError("Card package exceeds the size or entry limit.")
        names = {item.filename for item in files}
        if len(names) != len(files):
            raise ValueError("Duplicate archive paths.")
        index = read_object(bundle.read("INDEX.json"))
        if index["format_version"] != "1.0.0":
            raise ValueError("Unsupported cards index version.")
        if len(index["cards"]) != index["topic_count"]:
            raise ValueError("Card topic count does not match the index.")
        card_paths = set()
        card_ids = set()
        for row in index["cards"]:
            if row["id"] in card_ids or set(row["files"]) != {"de", "en"}:
                raise ValueError("Missing translation or duplicate topic.")
            card_ids.add(row["id"])
            for folder, lang in (("DEU", "de"), ("ENG", "en")):
                name = row["files"][lang]
                if name != f"{folder}/{row['id']}.json" or Path(name).name != f"{row['id']}.json":
                    raise ValueError("Invalid card path.")
                card = read_object(bundle.read(name))
                if (card["language"], card["card_id"], card["title"], card["source_manifest_version"]) != (
                    lang, row["id"], row["title"][lang], index["manifest_version"]
                ):
                    raise ValueError("Card metadata does not match the index.")
                card_paths.add(name)
        if len(card_paths) != index["card_count"] or card_paths != {
            name for name in names if name.startswith(("DEU/", "ENG/")) and name.endswith(".json")
        }:
            raise ValueError("Card inventory does not match the index.")
        source = None
        for record in (index["source_manifest"], *index.get("source_documents", [])):
            name = record["path"]
            if not name.startswith("SOURCE/") or name != f"SOURCE/{Path(name).name}":
                raise ValueError("Invalid source document path.")
            body = bundle.read(name)
            if hashlib.sha256(body).hexdigest() != record["sha256"]:
                raise ValueError("Source hash does not match the index.")
            if record is index["source_manifest"]:
                source = read_object(body)
        if source is None or source["format_version"] != index["manifest_version"]:
            raise ValueError("Source manifest version does not match the index.")
        return source, len(card_paths)


def inspect_manifest(project_id: str, path: Path) -> dict:
    try:
        if path.suffix.lower() == ".zip":
            manifest, cards = read_cards(path)
        else:
            with path.open("rb") as stream:
                payload = stream.read(MAX_BYTES + 1)
            if len(payload) > MAX_BYTES:
                raise ValueError("Manifest exceeds the size limit.")
            manifest, cards = read_object(payload), None
        version = manifest["format_version"]
        if version not in ("1.0.0", "1.5.0"):
            raise ValueError("Unsupported development manifest version.")
        declared = manifest["projekt"]["id"]
        if declared not in (None, project_id):
            raise ValueError("Manifest project ID does not match the selected project.")
        if not isinstance(manifest["evidenz"], list):
            raise ValueError("Evidence must be an array.")
        observations = []
        seen = set()
        for record in manifest["evidenz"]:
            item = dict(record)
            for legacy, canonical in EVIDENCE_ALIASES.items():
                if legacy in item:
                    if canonical in item and item[canonical] != item[legacy]:
                        raise ValueError("Conflicting fields in an evidence record.")
                    item[canonical] = item.pop(legacy)
            if not isinstance(item["id"], str) or not item["id"] or item["id"] in seen:
                raise ValueError("Missing or duplicate evidence ID.")
            seen.add(item["id"])
            status = item.get("status") or "OFFEN"
            if status not in STATUSES:
                raise ValueError("Invalid evidence status.")
            observations.append({"id": item["id"], "source_status": status,
                                 "status": "OFFEN" if status == "VERIFIZIERT" else status,
                                 "art": item.get("art"), "pruefdatum": item.get("pruefdatum")})
        return {
            "project_id": project_id, "declared_project_id": declared,
            "format_version": version, "structure_status": "VERIFIZIERT", "card_count": cards,
            "evidenz": observations,
            "additional_sections": sorted(manifest.keys() - CORE_SECTIONS),
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError,
            NotImplementedError, zipfile.BadZipFile) as exc:
        raise DevhubError(f"Invalid or unreadable development manifest: {exc}") from exc
