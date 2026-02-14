import json

def load_json(path):
    with open(path, "rb") as f:
        raw = f.read()

    for enc in ["utf-16-le", "utf-16-be", "utf-8"]:
        try:
            return json.loads(raw.decode(enc))
        except:
            continue

    raise Exception(f"Unable to decode {path}")

