"""Present native 666DEV LiveCircle data in the local visual workspace."""
from html import escape

from .scripts.render_ui import ASSETS, PLACEHOLDERS, apply_checkpoint, render

TEMPLATE = ASSETS / "ui-template.html"
ASSET_FILES = (TEMPLATE, *(ASSETS / asset for asset in PLACEHOLDERS.values()))


def render_workspace(record: dict | None, checkpoint: dict | None = None) -> str:
    project = record["project_id"] if record else None
    commit = record["source_commit"] if record else None
    status = record["status"] if record else "OFFEN"
    basis = f"{project} · Git {commit}" if commit else "Projektquelle offen"
    companion = {"start_mode": "formats", "status": status}
    if commit:
        companion.update(project_key=f"666dev:{project}", source_revision=commit)
    items = [{"label": "Quellstand", "text": commit or "OFFEN"}]
    if record:
        for key, label in (("working", "Working"), ("current", "Current")):
            pointer = record[key]
            items.append({"label": label, "text": pointer["checkpoint_id"] if pointer else "OFFEN"})
        for kind, counts in record.get("acceptance", {}).items():
            label = {"test": "Tests", "build": "Builds"}[kind]
            items.append({"label": label, "text": (
                f"{counts['passed']} bestanden · {counts['failed']} fehlgeschlagen · "
                f"{counts['blocked']} blockiert · {counts['pending']} offen"
            )})
    data = {
        "title": f"666DEV · {project}" if project else "666DEV · Visualformen",
        "basis": basis,
        "views": [{"id": "livecircle", "title": "LiveCircle", "summary": "Lokaler Quellenabgleich",
                   "kind": "cards", "route_terms": ["livecircle", "quellstand"],
                   "source": basis, "status": status, "items": items}],
        "gaps": [] if commit else ["Ein belegter Projektcommit fehlt."],
        "companion": companion,
    }
    notice = ""
    if checkpoint is not None:
        try:
            if status in {"CONFLICT_QUARANTINE", "READBACK_PENDING"}:
                raise ValueError("Projektbasis ist für die Wiederaufnahme gesperrt.")
            companion.pop("start_mode")
            data = apply_checkpoint(data, checkpoint)
        except ValueError as error:
            companion["start_mode"] = "formats"
            data["gaps"].append(str(error))
            companion["next_step"] = "UI-Handoff prüfen"
            companion["reason"] = str(error)
            notice = f'<p role="status">UI-Handoff: {escape(str(error))}</p>'
    html = render(data, TEMPLATE.read_text(encoding="utf-8"))
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>666DEV · Visualformen</title></head><body>' + notice + html + '</body></html>')
