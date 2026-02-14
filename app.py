import streamlit as st
from services.extraction_service import extract_uploaded_pbit
from services.schema_service import load_schema
from services.layout_service import parse_layout_usage
from services.metadata_service import collect_metadata
from services.dependency_service import parse_dax_dependencies
from services.usage_service import compute_usage
from services.export_service import generate_excel

st.set_page_config(page_title="Power BI SaaS Analyzer", layout="wide")

st.title("📊 Power BI SaaS Model Analyzer")
uploaded_file = st.file_uploader("Upload PBIT File", type=["pbit"])

if uploaded_file:

    base_path = extract_uploaded_pbit(uploaded_file)

    schema_json = load_schema(base_path)

    metadata = collect_metadata(schema_json)

    used_fields = parse_layout_usage(base_path)

    used_fields.update(
        parse_dax_dependencies(metadata["dax_expressions"])
    )

    usage_result = compute_usage(
        used_fields,
        metadata
    )

    generate_excel(base_path, usage_result)

    st.success("Analysis Complete ✅")
    st.write(usage_result["summary"])

