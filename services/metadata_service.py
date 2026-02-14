
def collect_metadata(schema_json):

    model = schema_json.get("model", {})
    tables = model.get("tables", [])

    all_tables = set()
    all_columns = set()
    all_measures = set()
    dax_expressions = []

    for table in tables:
        table_name = table.get("name")
        all_tables.add(table_name)

        for col in table.get("columns", []):
            all_columns.add(f"{table_name}[{col.get('name')}]")
            if col.get("expression"):
                dax_expressions.append(col["expression"])

        for msr in table.get("measures", []):
            all_measures.add(f"{table_name}[{msr.get('name')}]")
            if msr.get("expression"):
                dax_expressions.append(msr["expression"])

    return {
        "tables": all_tables,
        "columns": all_columns,
        "measures": all_measures,
        "dax_expressions": dax_expressions
    }
