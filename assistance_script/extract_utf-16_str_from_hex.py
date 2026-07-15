import re
import sys

def read_hex_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return "".join(f.read().split())

def extract_text(data):
    # 匹配连续双字节 UTF-16LE 可打印文本，例如 P\0R\0A\0...
    pat = re.compile(rb"(?:[\x20-\x7E]\x00)+")

    for m in pat.finditer(data):
        chunk = m.group()
        if len(chunk) >= 4:  # 至少两个字符，过滤零散匹配
            try:
                yield chunk.decode("utf-16le")
            except UnicodeDecodeError:
                continue

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python extract.py data.hex")
        sys.exit(1)

    hex_str = read_hex_file(sys.argv[1])
    data = bytes.fromhex(hex_str)

    for text in extract_text(data):
        print(text)