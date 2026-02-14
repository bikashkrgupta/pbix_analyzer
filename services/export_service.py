
import pandas as pd
import os

def generate_excel(base_path, usage_result):

    rows = []

    for col in usage_result["used_columns"]:
        rows.append({"Field": col, "Used": True})

    for col in usage_result["unused_columns"]:
        rows.append({"Field": col, "Used": False})

    df = pd.DataFrame(rows)

    path = os.path.join(base_path, "PowerBI_Model_Analysis.xlsx")
    df.to_excel(path, index=False)

    return path
