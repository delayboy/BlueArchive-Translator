import os
import zipfile
import sys
def pad_normal(file_path, target_size):
    """
    Pads a non-ZIP file with null bytes (\x00) to reach the target size.
    """
    current_size = os.path.getsize(file_path)
    if current_size >= target_size:
        print("File already meets or exceeds target size.")
        return
    
    with open(file_path, 'ab') as f:
        f.write(b'\x00' * (target_size - current_size))
    print(f"Padded {file_path} to {target_size} bytes.")

def pad_zip(zip_path, target_size, padding_byte=b'\x00'):
    with open(zip_path, 'rb') as f:
        zip_data = f.read()

    # Locate EOCD (End of Central Directory) signature: 0x06054b50
    eocd_signature = b'\x50\x4b\x05\x06'
    eocd_index = zip_data.rfind(eocd_signature)

    if eocd_index == -1:
        print("Error: Not a valid ZIP file (EOCD not found).")
        return
    
    current_size = len(zip_data)
    padding_needed = target_size - current_size
    
    if padding_needed <= 0:
        print("Error: File is already larger than or equal to the target size.")
        return

    zip_content = zip_data[:eocd_index]
    eocd_data = zip_data[eocd_index:]

    padded_zip = zip_content + (padding_byte * padding_needed) + eocd_data

    with open(zip_path, 'wb') as f:
        f.write(padded_zip)

    print(f"Padded ZIP file saved as: {zip_path} (size: {len(padded_zip)} bytes)")

def pad_file(file_path, target_size):
    if not file_path.endswith(".zip"):
        pad_normal(file_path, target_size)
    else:
        pad_zip(file_path, target_size)

if __name__ == "__main__":
    # Check if the correct number of arguments are passed
    if len(sys.argv) != 3:
        print("Usage: python pad.py <file_path> <target_size>")
        sys.exit(1)
    
    # Get the file path and target size from command line arguments
    file_path = sys.argv[1]
    target_size = int(sys.argv[2])

    # Call pad_file to perform the padding
    pad_file(file_path, target_size)