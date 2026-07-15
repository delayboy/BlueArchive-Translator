import pyzipper
with pyzipper.AESZipFile('C:/Users/Benson/Desktop/BlueArchive-Hack/BlueArchive_Data/StreamingAssets/Resource/Preload/TableBundles/Excel.zip', 'r') as zf:
    # 查看第一个加密文件的加密类型
    # 获取所有文件信息
    infos = zf.infolist()
    if not infos:
        print("压缩包为空")
    else:
        first_info = infos[0]  # 取第一个文件
        compression = first_info.compress_type
        encryption = getattr(first_info, 'encryption', None)  # pyzipper 特有属性
        print(f"压缩算法: {compression}, 加密类型: {encryption}")
        is_encrypted = (first_info.flag_bits & 0x1) != 0
        print(f"是否加密: {is_encrypted}")