import re

def parse_dax_dependencies(dax_expressions):

    used_fields = set()
    pattern = r"([A-Za-z0-9_ ]+)\[([A-Za-z0-9_ ]+)\]"

    for dax in dax_expressions:

        if isinstance(dax, list):
            dax = " ".join(dax)

        if not isinstance(dax, str):
            continue

        matches = re.findall(pattern, dax)

        for table, column in matches:
            used_fields.add(f"{table.strip()}[{column.strip()}]")

    return used_fields

