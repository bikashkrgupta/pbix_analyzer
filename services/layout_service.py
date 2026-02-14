
import os
import json
from core.json_loader import load_json


# ---------------------------------------------
# Internal recursive field extractor
# ---------------------------------------------
def _extract_fields(obj, used_fields, alias_map=None):

    if isinstance(obj, dict):

        # Column
        if "Column" in obj:
            col = obj["Column"]
            prop = col.get("Property")
            source = col.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = col.get("Expression", {}).get("SourceRef", {}).get("Entity")

            table = alias_map.get(source) if alias_map and source else entity

            if table and prop:
                used_fields.add(f"{table}[{prop}]")

        # Measure
        if "Measure" in obj:
            msr = obj["Measure"]
            prop = msr.get("Property")
            source = msr.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = msr.get("Expression", {}).get("SourceRef", {}).get("Entity")

            table = alias_map.get(source) if alias_map and source else entity

            if table and prop:
                used_fields.add(f"{table}[{prop}]")

        # Aggregation
        if "Aggregation" in obj:
            _extract_fields(obj["Aggregation"], used_fields, alias_map)

        # Recursive
        for v in obj.values():
            _extract_fields(v, used_fields, alias_map)

    elif isinstance(obj, list):
        for item in obj:
            _extract_fields(item, used_fields, alias_map)


# ---------------------------------------------
# Public function
# ---------------------------------------------
def parse_layout_usage(base_path):

    used_fields = set()

    layout_path = os.path.join(base_path, "Report", "Layout")
    layout_json = load_json(layout_path)

    for section in layout_json.get("sections", []):

        # Page filters
        if section.get("filters"):
            try:
                _extract_fields(json.loads(section["filters"]), used_fields)
            except:
                pass

        for visual in section.get("visualContainers", []):

            # Visual filters
            if visual.get("filters"):
                try:
                    _extract_fields(json.loads(visual["filters"]), used_fields)
                except:
                    pass

            # Query parsing
            if visual.get("query"):
                try:
                    q_json = json.loads(visual["query"])
                    for cmd in q_json.get("Commands", []):
                        sqd = cmd.get("SemanticQueryDataShapeCommand", {})
                        query_part = sqd.get("Query", {})

                        alias_map = {
                            f.get("Name"): f.get("Entity")
                            for f in query_part.get("From", [])
                        }

                        _extract_fields(query_part, used_fields, alias_map)
                except:
                    pass

            # Config parsing
            if visual.get("config"):
                try:
                    cfg_json = json.loads(visual["config"])
                    proto = cfg_json.get("singleVisual", {}).get("prototypeQuery", {})

                    alias_map = {
                        f.get("Name"): f.get("Entity")
                        for f in proto.get("From", [])
                    }

                    _extract_fields(proto, used_fields, alias_map)
                    _extract_fields(cfg_json, used_fields, alias_map)

                except:
                    pass

    return used_fields
