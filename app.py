import streamlit as st
import zipfile
import json
import os
import shutil
import re
import pandas as pd

st.set_page_config(page_title="Power BI Model Analyzer", layout="wide")
st.title("📊 Power BI Model Analyzer")
st.write("Upload a PBIT file to analyze field usage, dependencies, unused objects and export report.")

uploaded_file = st.file_uploader("Upload PBIT File", type=["pbit"])

# -------------------------------------------------
# JSON Loader
# -------------------------------------------------
def load_json_file(path):
    with open(path, "rb") as f:
        raw = f.read()

    for enc in ["utf-16-le", "utf-16-be", "utf-8"]:
        try:
            return json.loads(raw.decode(enc))
        except:
            continue

    raise Exception(f"Could not decode {path}")

# -------------------------------------------------
# Detect System Date Tables
# -------------------------------------------------
def is_system_date_table(table):
    for ann in table.get("annotations", []):
        if ann.get("name") in [
            "__PBI_TemplateDateTable",
            "__PBI_LocalDateTable"
        ] and ann.get("value") == "true":
            return True
    return False

# -------------------------------------------------
# Recursive Field Extractor (Layout Scanner)
# -------------------------------------------------
def extract_fields(obj, alias_map=None):
    if isinstance(obj, dict):

        # Column
        if "Column" in obj:
            col = obj["Column"]
            prop = col.get("Property")

            source = col.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = col.get("Expression", {}).get("SourceRef", {}).get("Entity")

            table = None
            if alias_map and source:
                table = alias_map.get(source)
            elif entity:
                table = entity

            if table and prop:
                used_fields.add(f"{table}[{prop}]")

        # Measure
        if "Measure" in obj:
            msr = obj["Measure"]
            prop = msr.get("Property")

            source = msr.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = msr.get("Expression", {}).get("SourceRef", {}).get("Entity")

            table = None
            if alias_map and source:
                table = alias_map.get(source)
            elif entity:
                table = entity

            if table and prop:
                used_fields.add(f"{table}[{prop}]")

        # Aggregation
        if "Aggregation" in obj:
            extract_fields(obj["Aggregation"], alias_map)

        # HierarchyLevel
        if "HierarchyLevel" in obj:
            level = obj["HierarchyLevel"]
            hierarchy = level.get("Expression", {}).get("Hierarchy", {})
            source = hierarchy.get("Expression", {}).get("SourceRef", {}).get("Source")
            entity = hierarchy.get("Expression", {}).get("SourceRef", {}).get("Entity")

            table = None
            if alias_map and source:
                table = alias_map.get(source)
            elif entity:
                table = entity

            level_name = level.get("Level")

            if table and level_name:
                used_fields.add(f"{table}[{level_name}]")

        for v in obj.values():
            extract_fields(v, alias_map)

    elif isinstance(obj, list):
        for item in obj:
            extract_fields(item, alias_map)

# -------------------------------------------------
# DAX Dependency Extractor
# -------------------------------------------------
def extract_dax_dependencies(dax_text):
    pattern = r"([A-Za-z0-9_ ]+)\[([A-Za-z0-9_ ]+)\]"
    matches = re.findall(pattern, dax_text)

    deps = set()
    for table, column in matches:
        deps.add(f"{table.strip()}[{column.strip()}]")
    return deps

# =================================================
# MAIN PROCESS
# =================================================
if uploaded_file:

    base_path = os.path.join(os.getcwd(), "extracted_pbit")

    if os.path.exists(base_path):
        shutil.rmtree(base_path)

    os.makedirs(base_path, exist_ok=True)

    pbit_path = os.path.join(base_path, uploaded_file.name)

    with open(pbit_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract PBIT
    with zipfile.ZipFile(pbit_path, 'r') as zip_ref:
        zip_ref.extractall(base_path)

    st.success("✅ PBIT Extracted")

    # Load Schema
    schema_json = load_json_file(os.path.join(base_path, "DataModelSchema"))
    model = schema_json.get("model", {})
    tables = model.get("tables", [])

    all_columns = set()
    all_measures = set()
    used_fields = set()
    measure_dependencies = {}

    dax_expressions = []
    all_tables = set()

    # ---------------------------------------------
    # Collect Model Metadata
    # ---------------------------------------------
    for table in tables:

        if is_system_date_table(table):
            continue

        table_name = table.get("name")
        all_tables.add(table_name)

        # Columns
        for col in table.get("columns", []):
            all_columns.add(f"{table_name}[{col.get('name')}]")

            if col.get("expression"):
                dax_expressions.append(col["expression"])

        # Measures
        for msr in table.get("measures", []):
            measure_name = f"{table_name}[{msr.get('name')}]"
            all_measures.add(measure_name)

            expression = msr.get("expression", "")
            if expression:
                dax_expressions.append(expression)
                measure_dependencies[measure_name] = extract_dax_dependencies(expression)

    # ---------------------------------------------
    # Parse Layout
    # ---------------------------------------------
    layout_json = load_json_file(os.path.join(base_path, "Report", "Layout"))

    for section in layout_json.get("sections", []):

        # Page filters
        if section.get("filters"):
            try:
                extract_fields(json.loads(section["filters"]))
            except:
                pass

        for visual in section.get("visualContainers", []):

            # Visual filters
            if visual.get("filters"):
                try:
                    extract_fields(json.loads(visual["filters"]))
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
                        extract_fields(query_part, alias_map)
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
                    extract_fields(proto, alias_map)
                    extract_fields(cfg_json, alias_map)
                except:
                    pass

    # ---------------------------------------------
    # Parse DAX Dependencies
    # ---------------------------------------------
    for dax in dax_expressions:
        deps = extract_dax_dependencies(dax)
        used_fields.update(deps)

    # ---------------------------------------------
    # Compute Usage
    # ---------------------------------------------
    used_columns = used_fields.intersection(all_columns)
    used_measures = used_fields.intersection(all_measures)

    unused_columns = all_columns - used_columns
    unused_measures = all_measures - used_measures

    used_tables = set(field.split("[")[0] for field in used_fields)
    unused_tables = all_tables - used_tables

    # =============================================
    # DASHBOARD
    # =============================================
    st.markdown("## 📊 Model Summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Tables", len(all_tables))
    c2.metric("Unused Tables", len(unused_tables))
    c3.metric("Used Tables", len(used_tables))

    c4, c5 = st.columns(2)
    c4.metric("Columns", len(all_columns))
    c5.metric("Unused Columns", len(unused_columns))

    c6, c7 = st.columns(2)
    c6.metric("Measures", len(all_measures))
    c7.metric("Unused Measures", len(unused_measures))

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Used Fields")
        st.write(sorted(used_fields))

    with col2:
        st.subheader("🚫 Unused Fields")
        st.write(sorted(unused_columns.union(unused_measures)))

    # ---------------------------------------------
    # Measure Dependencies
    # ---------------------------------------------
    st.markdown("## 🔗 Measure Dependencies")

    for measure, deps in measure_dependencies.items():
        if deps:
            st.write(f"**{measure}**")
            for d in deps:
                st.write(f"   ↳ {d}")

    # ---------------------------------------------
    # Excel Export
    # ---------------------------------------------
    export_rows = []

    for col in all_columns:
        export_rows.append({
            "Field": col,
            "Type": "Column",
            "Used": col in used_columns
        })

    for msr in all_measures:
        export_rows.append({
            "Field": msr,
            "Type": "Measure",
            "Used": msr in used_measures
        })

    for tbl in all_tables:
        export_rows.append({
            "Field": tbl,
            "Type": "Table",
            "Used": tbl not in unused_tables
        })

    df = pd.DataFrame(export_rows)

    excel_file = os.path.join(base_path, "PowerBI_Model_Analysis.xlsx")
    df.to_excel(excel_file, index=False)

    with open(excel_file, "rb") as f:
        st.download_button(
            "📥 Download Excel Report",
            f,
            file_name="PowerBI_Model_Analysis.xlsx"
        )
