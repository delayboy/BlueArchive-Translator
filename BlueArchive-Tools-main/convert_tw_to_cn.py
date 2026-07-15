import json
import opencc
import os

ch_converter = opencc.OpenCC('t2s.json')
test_key_words = {}
converter_file_names = """AcademyMessangerExcel.json
CharacterDialogBattlePassExcel.json
CharacterDialogEmojiExcel.json
CharacterDialogEventExcel.json
CharacterDialogExcel.json
CharacterDialogSubtitleExcel.json
CharacterVoiceSubtitleExcel.json
LocalizeCharProfileExcel.json
LocalizeErrorExcel.json
LocalizeEtcExcel.json
LocalizeExcel.json
LocalizeGachaShopExcel.json
LocalizeSkillExcel.json
ScenarioCharacterNameExcel.json
ScenarioScriptExcel.json
TutorialCharacterDialogExcel.json
Video_GlobalExcel.json
"""


def translate_json(dir_path, file_name='ScenarioScriptExcel.json', use_test=True):
    with open(f"{dir_path}/{file_name}", 'r', encoding='utf-8') as f:
        data = json.load(f)

    for i, item in enumerate(data):
        if use_test:
            for key in item.keys():
                if str(key).lower().endswith("tw") and type(item[key]) == str:
                    if key in ['ImagePathTw', 'AudioClipTw', 'PrefabNameTw', 'EmblemBGPathTw', 'VideoPathTw']:
                        continue
                    test_key_words[key] = item[key]
                    return True
                else:
                    continue
            return False
        for key in item.keys():
            if str(key).lower().endswith("tw"):
                if key in ['ImagePathTw', 'AudioClipTw', 'PrefabNameTw', 'EmblemBGPathTw', 'VideoPathTw']:
                    continue
                print(i, file_name, key, item[key])
                item[key] = ch_converter.convert(item[key])
        if file_name.__contains__("ScenarioScriptExcel"):
            item['TextJp']=''
            item['TextTh']=''
        if use_test:
            break
    if use_test:
        return False
    with open(f"translate/{file_name}", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    # os.remove(file_name)
    print(f"Done. {len(data)} entries processed.")
    return True

def delete_all_in_dir(dir_path: str):
    if not os.path.exists(dir_path):
        return
    if os.path.isfile(dir_path):
        os.remove(dir_path)
        return
    print(f"存在{dir_path}文件夹，进行清理")
    # 设置topdown参数进行深度优先遍历
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            if os.path.exists(file_path):
                os.remove(file_path)
        for dir_name in dirs:
            sub_dir_path = os.path.join(root, dir_name)
            if os.path.exists(sub_dir_path):
                os.removedirs(sub_dir_path)

    if os.path.exists(dir_path):
        os.removedirs(dir_path)

if __name__ == '__main__':
    dir_path_now = "./ExcelDB"
    os.makedirs("./translate", exist_ok=True)
    filename_fiter = converter_file_names.split("\n")
    for name in os.listdir(dir_path_now):
        if name.endswith("json") and name in filename_fiter:
            if translate_json(dir_path_now, name, False):
                print(name)
    print(test_key_words)