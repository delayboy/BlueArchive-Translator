from lib.console import notice, print
from utils.util import UnityUtils
from os import path
import os
import base64
from lib.encryption import convert_string, create_key
import json
import argparse
import requests
import subprocess
import re
from pathlib import Path
import setup_apk
TEMP_DIR = "Temp"
def decode_server_url(data: bytes) -> str:
    """
    Decodes the server URL from the given data.

    Args:
        data (bytes): Binary data to decode.

    Returns:
        str: Decoded server URL.
    """
    ciphers = {
        "ServerInfoDataUrl": "X04YXBFqd3ZpTg9cKmpvdmpOElwnamB2eE4cXDZqc3ZgTg==",
        "DefaultConnectionGroup": "tSrfb7xhQRKEKtZvrmFjEp4q1G+0YUUSkirOb7NhTxKfKv1vqGFPEoQqym8=",
        "SkipTutorial": "8AOaQvLC5wj3A4RC78L4CNEDmEL6wvsI",
        "Language": "wL4EWsDv8QX5vgRaye/zBQ==",
    }
    b64_data = base64.b64encode(data).decode()
    json_str = convert_string(b64_data, create_key("GameMainConfig"))
    obj = json.loads(json_str)
    encrypted_url = obj[ciphers["ServerInfoDataUrl"]]
    url = convert_string(encrypted_url, create_key("ServerInfoDataUrl"))
    return url
def get_server_url() -> str:
    """Decrypt the server version from the game's binary files."""
    print("Retrieving game info...")
    url = version = ""
    for dir, _, files in os.walk(
        path.join(path.join(TEMP_DIR, "Data"), "assets", "bin", "Data")
    ):
        for file in files:
            if url_obj := UnityUtils.search_unity_pack(
                path.join(dir, file), ["TextAsset"], ["GameMainConfig"], True
            ):
                url = decode_server_url(url_obj[0].read().m_Script.encode("utf-8", "surrogateescape"))  # type: ignore
                notice(f"Get URL successfully: {url}")
            if version_obj := UnityUtils.search_unity_pack(
                path.join(dir, file), ["PlayerSettings"]
            ):
                try:
                    version = version_obj[0].read().bundleVersion  # type: ignore
                except:
                    version = "unavailable"
                print(f"The apk version is {version}.")

            if url and version:
                break

    if not url:
        raise LookupError("Cannot find server url from apk.")
    if not version:
        notice("Cannot retrieve apk version data.")
    return url
def get_addressable_catalog_url(server_url: str, json_output_path: Path) -> str:
    """Fetches and extracts the latest AddressablesCatalogUrlRoot from the server URL."""
    response = requests.get(server_url)
    if response.status_code != 200:
        raise LookupError(f"Failed to fetch data from {server_url}. Status code: {response.status_code}")
    
    # Parse the JSON response
    data = response.json()

    # Extract the last AddressablesCatalogUrlRoot from the OverrideConnectionGroups
    connection_groups = data.get("ConnectionGroups", [])
    if not connection_groups:
        raise LookupError("Cannot find ConnectionGroups in the server response.")
    
    # Get the last OverrideConnectionGroup
    override_groups = connection_groups[0].get("OverrideConnectionGroups", [])
    if not override_groups:
        raise LookupError("Cannot find OverrideConnectionGroups in the server response.")

    # Get the last AddressablesCatalogUrlRoot in the list
    latest_catalog_url = override_groups[-1].get("AddressablesCatalogUrlRoot")
    if not latest_catalog_url:
        raise LookupError("Cannot find AddressablesCatalogUrlRoot in the last entry of OverrideConnectionGroups.")
    with open(json_output_path, "wb") as f:
        f.write(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode())
    return latest_catalog_url, connection_groups[0].get("BundleVersion")

import zipfile
import xml.etree.ElementTree as ET
from pyaxmlparser.axmlprinter import AXMLPrinter # Ensure this comes from your maintained AXMLParser package

def get_apk_version_info(apk_path):
    try:
        # Open the APK as a ZIP file and read the binary AndroidManifest.xml
        with zipfile.ZipFile(apk_path, 'r') as apk:
            manifest_content = apk.read('AndroidManifest.xml')
        
        # Use AXMLPrinter to convert the binary XML into plain text XML.
        # This class should also do the necessary cleanup of namespace URIs.
        xml_str = AXMLPrinter(manifest_content).get_xml()
        
        # Parse the XML string with ElementTree.
        root = ET.fromstring(xml_str)
        
        # The version attributes are usually in the 'android' namespace.
        # The AXMLPrinter (per docs) should have cleaned up the namespace URIs.
        # Here we explicitly define the expected android namespace.
        android_ns = "http://schemas.android.com/apk/res/android"
        
        # Extract versionCode and versionName using the namespace-qualified keys.
        version_code = root.attrib.get(f"{{{android_ns}}}versionCode")
        version_name = root.attrib.get(f"{{{android_ns}}}versionName")
        
        if version_code and version_name:
            return version_code, version_name
        else:
            print("Error: versionCode or versionName not found in the manifest.")
            return None
    except Exception as e:
        notice(f"Error extracting version info from manifest: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Yostar server URL for Blue Archive JP")
    parser.add_argument("output_path", type=Path, help="output file for server url")
    parser.add_argument("json_output_path", type=Path, help="output file for json from server url")

    args = parser.parse_args()
    with open(args.output_path, "wb") as fs:
        server_url = get_server_url()
        addressable_catalog_url, bundle_version = get_addressable_catalog_url(server_url, args.json_output_path)
        versionCode, versionName = get_apk_version_info(path.join(TEMP_DIR, "com.YostarJP.BlueArchive.apk"))
        fs.write(f"BA_SERVER_URL={server_url}\nADDRESSABLE_CATALOG_URL={addressable_catalog_url}\nBA_VERSION_CODE={versionCode}\nBA_VERSION_NAME={versionName}\nBUNDLE_VERSION={bundle_version}".encode())
