from pathlib import Path
from sqlalchemy.orm import Session
from . import decision_service
from ..schemas import decision as decision_schema
def export_to_markdown(db: Session, export_path: Path):
    export_path.mkdir(parents=True, exist_ok=True)
    files_created = []
    decisions = decision_service.get_multi(db, limit=1000)
    if decisions:
        with open(export_path / "decisions.md", "w", encoding="utf-8") as f:
            f.write("# Decision Log\n\n")
            for d in decisions:
                f.write(f"## {d.summary}\n\n**Timestamp:** {d.timestamp}\n\n")
                if d.rationale is not None: f.write(f"**Rationale:**\n{d.rationale}\n\n")
                if d.implementation_details is not None: f.write(f"**Implementation Details:**\n{d.implementation_details}\n\n")
                if isinstance(d.tags, list) and len(d.tags) > 0: f.write(f"**Tags:** {', '.join(d.tags)}\n\n")
                f.write("---\n")
        files_created.append("decisions.md")
    return {"status": "success", "path": str(export_path), "files_created": files_created}
def import_from_markdown(db: Session, import_path: Path):
    if not (import_path / "decisions.md").exists():
        return {"status": "failed", "error": "decisions.md not found"}
    with open(import_path / "decisions.md", "r", encoding="utf-8") as f: content = f.read()
    decision_blocks = content.split('---')
    count = 0
    for block in decision_blocks:
        if not block.strip() or not block.startswith("##"): continue
        try:
            summary = block.split('\n')[0].replace("##", "").strip()
            rationale = block.split("**Rationale:**")[1].split("**")[0].strip() if "**Rationale:**" in block else None
            decision_data = decision_schema.DecisionCreate(summary=summary, rationale=rationale)
            decision_service.create(db, decision_data)
            count += 1
        except Exception: continue
    return {"status": "success", "decisions_imported": count}