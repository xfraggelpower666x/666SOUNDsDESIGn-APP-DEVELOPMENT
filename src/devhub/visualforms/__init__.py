"""Present native 666DEV LiveCircle data in the local visual workspace."""
from .scripts.render_ui import ASSETS, PLACEHOLDERS, render

TEMPLATE = ASSETS / "ui-template.html"
ASSET_FILES = (TEMPLATE, *(ASSETS / asset for asset in PLACEHOLDERS.values()))


def render_workspace(record: dict | None) -> str:
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
    html = render(data, TEMPLATE.read_text(encoding="utf-8"))
    return ('<!doctype html><html lang="de"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>666DEV · Visualformen</title></head><body>' + html + '</body></html>')
