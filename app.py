import streamlit as st
import zipfile
import json
import os
import tempfile

st.set_page_config(page_title="PBIX Field Usage Analyzer", layout="wide")

st.title("📊 PBIX Field Usage Analyzer")
st.write("Upload a PBIX file to detect used Measures and Columns.")

uploaded_file = st.file_uploader("Upload PBIX File", type=["pbix"])

if uploaded_file:

    with tempfile.TemporaryDirectory() as tmpdirname:

        pbix_path = os.path.join(tmpdirname, uploaded_file.name)

        # Save uploaded file
        with open(pbix_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Extract PBIX
        with zipfile.ZipFile(pbix_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)

        st.success("✅ PBIX Extracted Successfully")

        # Load Layout
        layout_path = os.path.join(tmpdirname, "Report", "Layout")

        def load_layout_file(path):
            with open(path, "rb") as f:
                raw = f.read()

            json_start = raw.find(b'{')
            json_bytes = raw[json_start:]

            for encoding in ["utf-8", "utf-16", "utf-16-le", "utf-16-be"]:
                try:
                    return json.loads(json_bytes.decode(encoding))
                except:
                    continue

            raise Exception("Could not decode Layout")

        layout_json = load_layout_file(layout_path)

        st.success("✅ Layout Loaded Successfully")

        # Detect Used Fields
        used_measures = set()
        used_columns = set()

        sections = layout_json.get("sections", [])

        for section in sections:
            visuals = section.get("visualContainers", [])

            for visual in visuals:

                query_str = visual.get("query")
                if query_str:
                    try:
                        query = json.loads(query_str)
                        commands = query.get("Commands", [])


                        for cmd in commands:
                            semantic = cmd.get("SemanticQueryDataShapeCommand", {})
                            query_part = semantic.get("Query", {})
                            selects = query_part.get("Select", [])

                            for sel in selects:
                                if "Measure" in sel:
                                    used_measures.add(sel.get("Name"))
                                elif "Column" in sel:
                                    used_columns.add(sel.get("Name"))
                    except:
                        pass

        # Display Results
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📌 Used Measures")
            st.write(list(sorted(used_measures)))

        with col2:
            st.subheader("📌 Used Columns")
            st.write(list(sorted(used_columns)))

        st.markdown("---")
        st.metric("Total Measures Used", len(used_measures))
        st.metric("Total Columns Used", len(used_columns))
