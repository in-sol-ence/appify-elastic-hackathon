import csv
import io

from models.project import Project
from services.bom_calculator import bom_rows


def export_project_json(project: Project) -> str:
    return project.model_dump_json(indent=2)


def export_bom_csv(project: Project) -> str:
    rows = bom_rows(project)
    if not rows:
        return ""
    output = io.StringIO()
    fields = [key for key in rows[0] if key != "role_id"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows([{key: row[key] for key in fields} for row in rows])
    return output.getvalue()
