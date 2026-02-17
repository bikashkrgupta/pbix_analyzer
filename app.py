import streamlit as st
import zipfile
import json
import os
import shutil
import re
import pandas as pd

st.set_page_config(page_title="Power BI Model Analyzer", layout="wide")
st.title("📊 Power BI Model Analyzer")
st.write("Upload a PBIT file to analyze field usage, dependencies, relationships, unused objects, and export report.")

uploaded_file = st.file_uploader("Upload PBIT File", type=["pbit"])

# -------------------------
# JSON Loader
# -------------------------
def load_json_file(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ["utf-16-le", "utf-16-be", "utf-8"]:
        try:
            return json.loads(raw.decode(enc))
        except:
            continue
    raise Exception(f"Could not decode {path}")

# -------------------------
# Detect System Date Tables
# -------------------------
def is_system_date_table(table):
    for ann in table.get("annotations", []):
        if ann.get("name") in ["__PBI_TemplateDateTable", "__PBI_LocalDateTable"] and ann.get("value") == "true":
            return True
    return False

# -------------------------
# Recursive Field Extractor
# -------------------------
def extract_fields(obj, alias_map=None):
    if isinstance(obj, dict):
        if "Column" in obj:
            col = obj["Column"]
            prop = col.get("Property")
            source = col.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = col.get("Expression", {}).get("SourceRef", {}).get("Entity")
            table = alias_map.get(source) if alias_map and source else entity
            if table and prop:
                used_fields.add(f"{table.strip()}[{prop.strip()}]")

        if "Measure" in obj:
            msr = obj["Measure"]
            prop = msr.get("Property")
            source = msr.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = msr.get("Expression", {}).get("SourceRef", {}).get("Entity")
            table = alias_map.get(source) if alias_map and source else entity
            if table and prop:
                used_fields.add(f"{table.strip()}[{prop.strip()}]")

        for v in obj.values():
            extract_fields(v, alias_map)

    elif isinstance(obj, list):
        for item in obj:
            extract_fields(item, alias_map)

# -------------------------
# MAIN PROCESS
# -------------------------
if uploaded_file:

    base_path = os.path.join(os.getcwd(), "extracted_pbit")
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path, exist_ok=True)

    pbit_path = os.path.join(base_path, uploaded_file.name)
    with open(pbit_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(pbit_path, 'r') as zip_ref:
        zip_ref.extractall(base_path)

    st.success("✅ PBIT Extracted")

    # -------------------------
    # Load Model
    # -------------------------
    schema_json = load_json_file(os.path.join(base_path, "DataModelSchema"))
    model = schema_json.get("model", {})
    tables = model.get("tables", [])
    relationships = model.get("relationships", [])

    all_columns = set()
    all_measures = set()
    used_fields = set()
    measure_dependencies_raw = {}
    all_tables = set()

    # -------------------------
    # Extract Relationship Columns
    # -------------------------
    relationship_columns = set()

    for rel in relationships:
        from_table = rel.get("fromTable")
        from_column = rel.get("fromColumn")
        to_table = rel.get("toTable")
        to_column = rel.get("toColumn")

        if from_table and from_column:
            relationship_columns.add(f"{from_table}[{from_column}]")

        if to_table and to_column:
            relationship_columns.add(f"{to_table}[{to_column}]")

    # -------------------------
    # Collect Metadata
    # -------------------------
    for table in tables:
        if is_system_date_table(table):
            continue

        table_name = table.get("name")
        all_tables.add(table_name)

        for col in table.get("columns", []):
            col_name = f"{table_name}[{col.get('name')}]"
            all_columns.add(col_name)

            if col.get("expression"):
                measure_dependencies_raw[col_name] = col.get("expression")

        for msr in table.get("measures", []):
            measure_name = f"{table_name}[{msr.get('name')}]"
            all_measures.add(measure_name)

            if msr.get("expression"):
                measure_dependencies_raw[measure_name] = msr.get("expression")

    # -------------------------
    # Extract Used Fields From Layout
    # -------------------------
    layout_json = load_json_file(os.path.join(base_path, "Report", "Layout"))

    for section in layout_json.get("sections", []):

        if section.get("filters"):
            try:
                extract_fields(json.loads(section["filters"]))
            except:
                pass

        for visual in section.get("visualContainers", []):

            if visual.get("filters"):
                try:
                    extract_fields(json.loads(visual["filters"]))
                except:
                    pass

            if visual.get("query"):
                try:
                    q_json = json.loads(visual["query"])
                    for cmd in q_json.get("Commands", []):
                        sqd = cmd.get("SemanticQueryDataShapeCommand", {})
                        query_part = sqd.get("Query", {})
                        alias_map = {f.get("Name"): f.get("Entity") for f in query_part.get("From", [])}
                        extract_fields(query_part, alias_map)
                except:
                    pass

            if visual.get("config"):
                try:
                    cfg_json = json.loads(visual["config"])
                    proto = cfg_json.get("singleVisual", {}).get("prototypeQuery", {})
                    alias_map = {f.get("Name"): f.get("Entity") for f in proto.get("From", [])}
                    extract_fields(proto, alias_map)
                    extract_fields(cfg_json, alias_map)
                except:
                    pass

    # -------------------------
    # Direct Usage
    # -------------------------
    direct_columns = used_fields.intersection(all_columns)
    direct_measures = used_fields.intersection(all_measures)

    # -------------------------
    # Build Dependency Graph
    # -------------------------
    normalized_columns = {c.lower().strip(): c for c in all_columns}
    normalized_measures = {m.lower().strip(): m for m in all_measures}

    dependency_graph = {}

    for obj_name, expr in measure_dependencies_raw.items():

        deps = set()

        if isinstance(expr, list):
            expr = " ".join(expr)

        if not isinstance(expr, str):
            dependency_graph[obj_name] = deps
            continue

        expr = expr.replace("\n", " ")
        expr = re.sub(r"\s+", " ", expr)

        pattern_col = r"([A-Za-z0-9_ ]+)\s*\[\s*([^\]]+)\s*\]"
        for table, col in re.findall(pattern_col, expr):
            candidate_raw = f"{table.strip()}[{col.strip()}]"
            candidate_norm = candidate_raw.lower().strip()
            if candidate_norm in normalized_columns:
                deps.add(normalized_columns[candidate_norm])

        pattern_msr = r"(?<![A-Za-z0-9_ ])\[\s*([^\]]+?)\s*\]"
        for m in re.findall(pattern_msr, expr):
            m_clean = m.strip().lower()
            for msr_norm, msr_original in normalized_measures.items():
                if msr_norm.endswith(f"[{m_clean}]"):
                    deps.add(msr_original)

        dependency_graph[obj_name] = deps

    # -------------------------
    # Recursive Propagation
    # -------------------------
    all_used_measures = set(direct_measures)
    all_used_columns = set(direct_columns).union(relationship_columns)

    changed = True
    while changed:
        changed = False
        for measure in list(all_used_measures):
            for dep in dependency_graph.get(measure, []):
                if dep in all_measures and dep not in all_used_measures:
                    all_used_measures.add(dep)
                    changed = True
                if dep in all_columns and dep not in all_used_columns:
                    all_used_columns.add(dep)
                    changed = True

    # -------------------------
    # Categorization
    # -------------------------
    indirect_measures = all_used_measures - direct_measures
    indirect_columns = all_used_columns - direct_columns - relationship_columns
    relationship_only_columns = relationship_columns - direct_columns
    unused_columns = all_columns - all_used_columns
    unused_measures = all_measures - all_used_measures

    used_tables = set(f.split("[")[0] for f in all_used_columns.union(all_used_measures))
    unused_tables = all_tables - used_tables

    # =========================
    # DASHBOARD
    # =========================
    st.markdown("## 📊 Model Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tables", len(all_tables))
    c2.metric("Used Tables", len(all_tables) - len(unused_tables))
    c3.metric("Unused Tables", len(unused_tables))

    c4, c5, c6 = st.columns(3)
    c4.metric("Columns", len(all_columns))
    c5.metric("Unused Columns", len(unused_columns))
    c6.metric("Relationships", len(relationships))

    c7, c8 = st.columns(2)
    c7.metric("Measures", len(all_measures))
    c8.metric("Unused Measures", len(unused_measures))

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Used Fields")
        st.write("### 🟢 Direct Columns")
        st.write(sorted(direct_columns))
        st.write("### 🔗 Relationship Columns")
        st.write(sorted(relationship_only_columns))
        st.write("### 🟡 Indirect Columns")
        st.write(sorted(indirect_columns))
        st.write("### 🔵 Direct Measures")
        st.write(sorted(direct_measures))
        st.write("### 🟣 Indirect Measures")
        st.write(sorted(indirect_measures))

    with col2:
        st.subheader("🚫 Unused Fields")
        st.write("### 🔴 Unused Columns")
        st.write(sorted(unused_columns))
        st.write("### 🟠 Unused Measures")
        st.write(sorted(unused_measures))

    # -------------------------
    # Excel Export
    # -------------------------
    export_rows = []

    for col in all_columns:
        if col in direct_columns:
            status = "Directly Used"
        elif col in relationship_columns:
            status = "Used in Relationship"
        elif col in indirect_columns:
            status = "Indirectly Used"
        else:
            status = "Unused"

        export_rows.append({"Field": col, "Type": "Column", "Status": status})

    for msr in all_measures:
        if msr in direct_measures:
            status = "Directly Used"
        elif msr in indirect_measures:
            status = "Indirectly Used"
        else:
            status = "Unused"

        export_rows.append({"Field": msr, "Type": "Measure", "Status": status})

    df = pd.DataFrame(export_rows)
    excel_file = os.path.join(base_path, "PowerBI_Model_Analysis.xlsx")
    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        st.download_button("📥 Download Excel Report", f, file_name="PowerBI_Model_Analysis.xlsx")





