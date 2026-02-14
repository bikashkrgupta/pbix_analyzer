import os
from core.json_loader import load_json

def load_schema(base_path):
    return load_json(os.path.join(base_path, "DataModelSchema"))

