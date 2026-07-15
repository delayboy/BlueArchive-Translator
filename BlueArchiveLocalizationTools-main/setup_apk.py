from utils.util import ZipUtils
from os import path
from download_xapk import download_xapk
TEMP_DIR = "Temp"
def extract_apk_file(apk_path: str) -> None:
    """Extract the XAPK file."""
    apk_files = ZipUtils.extract_zip(
        apk_path, path.join(TEMP_DIR), keywords=["apk"]
    )

    ZipUtils.extract_zip(
        apk_files, path.join(TEMP_DIR, "Data"), zips_dir=TEMP_DIR
    )

if not path.exists(path.join(TEMP_DIR, "Data")):
    apk_path = download_xapk()
    extract_apk_file(apk_path)