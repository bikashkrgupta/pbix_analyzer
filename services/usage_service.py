def compute_usage(used_fields, metadata):

    used_columns = used_fields.intersection(metadata["columns"])
    used_measures = used_fields.intersection(metadata["measures"])

    unused_columns = metadata["columns"] - used_columns
    unused_measures = metadata["measures"] - used_measures

    return {
        "used_columns": used_columns,
        "unused_columns": unused_columns,
        "used_measures": used_measures,
        "unused_measures": unused_measures,
        "summary": {
            "Total Tables": len(metadata["tables"]),
            "Total Columns": len(metadata["columns"]),
            "Total Measures": len(metadata["measures"])
        }
    }

