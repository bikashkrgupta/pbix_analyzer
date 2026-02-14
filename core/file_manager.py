import os
import shutil
import zipfile

def prepare_workspace():
    base_path = os.path.join(os.getcwd(), "workspace")

    if os.path.exists(base_path):
        shutil.rmtree(base_path)

    os.makedirs(base_path, exist_ok=True)
    return base_path


def extract_zip(uploaded_file, base_path):
    file_path = os.path.join(base_path, uploaded_file.name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(base_path)

    return base_path

