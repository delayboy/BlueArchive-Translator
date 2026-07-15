from struct import iter_unpack
from .chunk import *
from .utf import UTF, UTFBuilder
from .awb import AWB, AWBBuilder
from .hca import HCA
import os
import io
from pydub import AudioSegment

class ACB(UTF):
    __slots__ = ["filename", "payload", "awb"]
    payload: list
    filename: str
    awb: AWB

    def __init__(self, filename) -> None:
        self.payload = UTF(filename).get_payload()
        self.filename = filename
        self.acbparse(self.payload)
    
    def acbparse(self, payload: list) -> None:
        for dict_entry in range(len(payload)):
            for k, v in payload[dict_entry].items():
                if v[0] == UTFTypeValues.bytes:
                    if v[1].startswith(UTFType.UTF.value):
                        par = UTF(v[1]).get_payload()
                        payload[dict_entry][k] = par
                        self.acbparse(par)
        self.load_awb()
    
    def load_awb(self) -> None:
        if self.payload[0]['AwbFile'][1] == b'':
            if isinstance(self.filename, str):
                awb_path = os.path.join(os.path.dirname(self.filename), self.payload[0]['Name'][1]+".awb")
                awbObj = AWB(awb_path)
            else:
                awbObj = AWB(self.payload[0]['Name'][1]+".awb")
        else:
            awbObj = AWB(self.payload[0]['AwbFile'][1])
        self.awb = awbObj

    def extract(self, decode: bool = False, key: int = 0, dirname: str = ""):
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        
        pl = self.payload[0]
        # 提取并排序
        cue_names = [e["CueName"][1] if isinstance(e["CueName"], tuple) else e["CueName"] 
                     for e in pl.get("CueNameTable", [])]
        cue_names.sort()

        # 将排序后的与 AWB 里的文件配对
        for idx, file_data in enumerate(self.awb.getfiles()):
            # 确定基础文件名
            base_name = cue_names[idx] if idx < len(cue_names) else str(idx)
            safe_name = "".join(c for c in base_name if c not in r'<>:"/\|?*')

            # 确定后缀
            w_table = pl.get("WaveformTable", [])
            encode_type = w_table[idx]["EncodeType"][1] if idx < len(w_table) else 2
            ext = self.get_extension(encode_type)
            
            if decode and ext == ".hca":
                try:
                    hca_data = HCA(file_data, key=key, subkey=self.awb.subkey).decode()
                    out_path = os.path.join(dirname, f"{safe_name}.ogg")
                    with io.BytesIO(hca_data) as wav_io:
                        AudioSegment.from_wav(wav_io).export(out_path, format="ogg", tags={'artist': '《蔚蓝档案》国服 / 上海星啸有限公司'})
                    continue
                except Exception:
                    ext = ".hca"

            with open(os.path.join(dirname, safe_name + ext), "wb") as f:
                f.write(file_data)

    def get_extension(self, EncodeType: int) -> str:
        mapping = {
            0: ".adx", 3: ".adx",
            2: ".hca", 6: ".hca",
            7: ".vag", 10: ".vag",
            8: ".at3",
            9: ".bcwav",
            11: ".at9", 18: ".at9",
            12: ".xma",
            13: ".dsp", 4: ".dsp", 5: ".dsp",
            19: ".m4a"
        }
        return mapping.get(EncodeType, "")

class ACBBuilder(UTFBuilder):
    pass