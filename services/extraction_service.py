from core.file_manager import prepare_workspace, extract_zip

def extract_uploaded_pbit(uploaded_file):
    base_path = prepare_workspace()
    extract_zip(uploaded_file, base_path)
    return base_path

