import streamlit as st
import zipfile
import json
import os
import shutil

st.set_page_config(page_title="PBIT Field Usage Analyzer", layout="wide")
st.title("📊 PBIT Field Usage Analyzer")
st.write("Upload a PBIT file to detect used and unused Columns & Measures (System date tables excluded).")

uploaded_file = st.file_uploader("Upload PBIT File", type=["pbit"])


# --------------------------
# JSON Loader (UTF Safe)
# --------------------------
def load_json_file(path):
    with open(path, "rb") as f:
        raw = f.read()

    for enc in ["utf-16-le", "utf-16-be", "utf-8"]:
        try:
            return json.loads(raw.decode(enc))
        except:
            continue

    raise Exception(f"Could not decode {path}")


# --------------------------
# Detect System Date Tables
# --------------------------
def is_system_date_table(table):
    for ann in table.get("annotations", []):
        if ann.get("name") in [
            "__PBI_TemplateDateTable",
            "__PBI_LocalDateTable"
        ] and ann.get("value") == "true":
            return True
    return False


if uploaded_file:

    base_path = os.path.join(os.getcwd(), "extracted_pbit")

    if os.path.exists(base_path):
        shutil.rmtree(base_path)

    os.makedirs(base_path, exist_ok=True)

    pbit_path = os.path.join(base_path, uploaded_file.name)

    with open(pbit_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # --------------------------
    # Extract PBIT
    # --------------------------
    try:
        with zipfile.ZipFile(pbit_path, 'r') as zip_ref:
            zip_ref.extractall(base_path)

        st.success("✅ PBIT Extracted Successfully")

    except Exception as e:
        st.error(f"Error extracting PBIT: {e}")
        st.stop()

    # --------------------------
    # Load DataModelSchema
    # --------------------------
    schema_path = os.path.join(base_path, "DataModelSchema")

    if not os.path.exists(schema_path):
        st.error("❌ DataModelSchema not found.")
        st.stop()

    schema_json = load_json_file(schema_path)
    model = schema_json.get("model", {})
    tables = model.get("tables", [])

    all_columns = set()
    all_measures = set()

    # Collect ONLY real model tables
    for table in tables:

        if is_system_date_table(table):
            continue  # 🔥 skip template + local auto date tables

        table_name = table.get("name")

        # Columns
        for col in table.get("columns", []):
            all_columns.add(f"{table_name}[{col.get('name')}]")

        # Measures
        for msr in table.get("measures", []):
            all_measures.add(f"{table_name}[{msr.get('name')}]")

    # --------------------------
    # Load Layout (Used Fields)
    # --------------------------
    layout_path = os.path.join(base_path, "Report", "Layout")

    if not os.path.exists(layout_path):
        st.error("❌ Layout file not found.")
        st.stop()

    layout_json = load_json_file(layout_path)
    used_fields = set()

    sections = layout_json.get("sections", [])

    for section in sections:

        visuals = section.get("visualContainers", [])

        for visual in visuals:

            # ----------------------
            # Parse semantic query
            # ----------------------
            query_str = visual.get("query")

            if query_str:
                try:
                    q_json = json.loads(query_str)
                    commands = q_json.get("Commands", [])

                    for cmd in commands:

                        sqd = cmd.get("SemanticQueryDataShapeCommand", {})
                        query_part = sqd.get("Query", {})

                        from_list = query_part.get("From", [])
                        alias_map = {
                            f.get("Name"): f.get("Entity")
                            for f in from_list
                        }

                        for sel in query_part.get("Select", []):

                            # Column
                            if "Column" in sel:
                                col = sel["Column"]
                                alias = col["Expression"]["SourceRef"]["Source"]
                                table = alias_map.get(alias)
                                prop = col.get("Property")

                                if table and prop:
                                    field_name = f"{table}[{prop}]"
                                    if field_name in all_columns:
                                        used_fields.add(field_name)

                            # Measure
                            if "Measure" in sel:
                                msr = sel["Measure"]
                                alias = msr["Expression"]["SourceRef"]["Source"]
                                table = alias_map.get(alias)
                                prop = msr.get("Property")

                                if table and prop:
                                    field_name = f"{table}[{prop}]"
                                    if field_name in all_measures:
                                        used_fields.add(field_name)

                except:
                    pass

            # ----------------------
            # Parse config → prototypeQuery
            # ----------------------
            config_str = visual.get("config")

            if config_str:
                try:
                    cfg_json = json.loads(config_str)

                    proto_query = (
                        cfg_json
                        .get("singleVisual", {})
                        .get("prototypeQuery", {})
                    )

                    from_list = proto_query.get("From", [])
                    alias_map = {
                        f.get("Name"): f.get("Entity")
                        for f in from_list
                    }

                    for sel in proto_query.get("Select", []):

                        # Column
                        if "Column" in sel:
                            col = sel["Column"]
                            alias = col["Expression"]["SourceRef"]["Source"]
                            table = alias_map.get(alias)
                            prop = col.get("Property")

                            if table and prop:
                                field_name = f"{table}[{prop}]"
                                if field_name in all_columns:
                                    used_fields.add(field_name)

                        # Measure
                        if "Measure" in sel:
                            msr = sel["Measure"]
                            alias = msr["Expression"]["SourceRef"]["Source"]
                            table = alias_map.get(alias)
                            prop = msr.get("Property")

                            if table and prop:
                                field_name = f"{table}[{prop}]"
                                if field_name in all_measures:
                                    used_fields.add(field_name)

                except:
                    pass

    # --------------------------
    # Separate used vs unused
    # --------------------------
    used_columns = used_fields.intersection(all_columns)
    used_measures = used_fields.intersection(all_measures)

    unused_columns = all_columns - used_columns
    unused_measures = all_measures - used_measures

    # --------------------------
    # Display Results
    # --------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📌 Used Columns")
        st.write(sorted(used_columns))

        st.subheader("📌 Used Measures")
        st.write(sorted(used_measures))

    with col2:
        st.subheader("🚫 Unused Columns")
        st.write(sorted(unused_columns))

        st.subheader("🚫 Unused Measures")
        st.write(sorted(unused_measures))

    st.markdown("---")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("Total Columns", len(all_columns))
    with m2:
        st.metric("Used Columns", len(used_columns))
    with m3:
        st.metric("Total Measures", len(all_measures))
    with m4:
        st.metric("Used Measures", len(used_measures))
