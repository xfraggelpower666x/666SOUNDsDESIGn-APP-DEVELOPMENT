"""Build the private 666DEV plugin from the reviewed Coding Profi source archive."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = "7537c8bf6fbfa3a275519a60e8a7e58a7324264f88b0133509d0fbc4cf077ac8"
SKILL = "skills/666dev-livecircle"
LEGACY = "skills/sceeri-coding-profi-livecircle/SKILL.md"
AUTHORITY = (
    "> Für 666DEV-Aufträge gilt der [native 666DEV-LiveCircle](../666dev-livecircle/SKILL.md). "
    "Diese Fachfacette verwendet dessen Projekt, Revision, Scope und Schreibregeln. "
    "Ältere Rollen, Trigger und Speicherziele in übernommenen Anleitungen dienen als Herkunftsmaterial.\n"
)
ROUTING = """## Plugin-Einstieg

Dieses Plugin ist **666DEV Coding Control**. Primäre Autorität ist 666DEV. Es verwendet
die Coding-Profi-Fachskills als Methodenbibliothek. Der fremde LiveCircle wird nicht gestartet.

- Direkte 666DEV-Trigger nach dem [Vertrag](../../references/666dev-livecircle.md) behandeln.
  Verifizierter Einstieg ist die vom Nutzer gewählte Revision von
  `xfraggelpower666x/666SOUNDsDESIGn-APP-DEVELOPMENT`. Lies zuerst deren `AGENTS.md`,
  Registry, Profil und LiveCircle-Vertrag.
- Bei vorhandenem Checkout ist die native CLI die Ausführungsschnittstelle. Verwende
  sonst den autorisierten GitHub-Lesezugang. Prüfe tatsächlichen Zugriff und Revision.
  Fehlende native Laufzeit, fehlende lokale Checkpoints oder nicht lesbare Quelle als
  `READBACK_PENDING` kennzeichnen. Chatbefunde geben keinen 666DEV-Nachweis vor.
- In einem Chat bleibt eine geklärte Projektbasis erhalten, bis sich Quelle,
  Profil, Revision oder Pointer ändern. Nach dem Chatwechsel den ausdrücklichen
  Handoff mit den nativen Quellen abgleichen. Import führt keine Folgeaktion aus.
- Für reine Fachaufgaben ohne gebundenes 666DEV-Projekt gelten die Coding-Methoden
  für die vorgelegten Dateien und den beauftragten Scope. Daraus entsteht kein
  666DEV-Checkpoint. Live-Ausführung benötigt ihre tatsächliche Host-Fähigkeit.
"""


def dump(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build(source: Path, destination: Path):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected the reviewed Coding Profi 0.75.0 source archive.")
    if destination.resolve() == source.resolve():
        raise ValueError("Choose a new output path.")
    with ZipFile(io.BytesIO(raw)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(files["plugin.json"])
    display = manifest["extensions"]["com.openai"]["interface"]
    display.update(
        displayName="666DEV Coding Control",
        shortDescription="666DEV LiveCircle und Code",
        longDescription="666DEV-Projektkontinuität und Coding-Profi-Fachskills für Analyse, Entwicklung, Repair, Test und Übergabe.",
        defaultPrompt=["666DEV HELP", "Zeige mir den 666DEV-LiveCircle für mein registriertes Projekt."],
    )
    manifest.update(name="666dev-coding-control", version="0.1.4", description=display["longDescription"])
    files["plugin.json"] = dump(manifest)
    overlay = json.loads(files[".codex-plugin/plugin.json"])
    overlay.update(name=manifest["name"], version=manifest["version"],
                   description=manifest["description"], interface=display)
    files[".codex-plugin/plugin.json"] = dump(overlay)
    for name in files:
        if name.startswith("skills/") and name.endswith("/SKILL.md") and name != LEGACY:
            header, frontmatter, body = files[name].decode("utf-8").split("---", 2)
            content = body.splitlines(keepends=True)
            heading = next((i for i, line in enumerate(content) if line.startswith("# ")), 0)
            content.insert(heading + 1, "\n" + AUTHORITY)
            files[name] = (header + "---" + frontmatter + "---" + "".join(content)).encode("utf-8")
    files["references/coding-profi-livecircle-original.md"] = files[LEGACY]
    files[LEGACY] = (
        "---\nname: sceeri-coding-profi-livecircle\ndescription: Verweist bei Projektkontinuität auf den nativen 666DEV-LiveCircle.\n---\n\n"
        "# Projektkontinuität\n\nFür LiveCircle, Projektbindung, Wiederaufnahme und Chatwechsel gilt "
        "ausschließlich der [native 666DEV-LiveCircle](../666dev-livecircle/SKILL.md).\n"
    ).encode("utf-8")
    files[f"{SKILL}/SKILL.md"] = (
        (ROOT / ".github/skills/666dev-livecircle/SKILL.md").read_text(encoding="utf-8")
        .replace("../../../docs/livecircle.md", "../../references/666dev-livecircle.md")
        + "\n" + ROUTING
    ).encode("utf-8")
    files["references/666dev-livecircle.md"] = (
        (ROOT / "docs/livecircle.md").read_text(encoding="utf-8")
        .replace("../.github/skills/666dev-livecircle/SKILL.md", "../skills/666dev-livecircle/SKILL.md")
    ).encode("utf-8")
    files["README.md"] = (
        "# 666DEV Coding Control\n\nStart mit [666DEV LiveCircle](skills/666dev-livecircle/SKILL.md).\n\n"
        "Der folgende Abschnitt dokumentiert die übernommenen Fachfunktionen des Quellpakets. "
        "Seine ursprünglichen Systemtrigger und Speicherregeln gelten als Herkunftsdokumentation.\n\n"
    ).encode("utf-8") + files["README.md"]
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            archive.writestr(ZipInfo(name), content, ZIP_DEFLATED)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build(args.source, args.destination)
