import json
import opencc
import os

ch_converter = opencc.OpenCC('t2s.json')
test_key_words = {}
converter_file_names = """AcademyMessangerExcel.json
CharacterDialogEventExcel.json
CharacterDialogBattlePassExcel.json
CharacterDialogEmojiExcel.json
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
# CharacterDialogEventExcel.json 重新打包有立绘bug，跟翻译没关系，直接打包就会触发立绘消失的bug

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


if __name__ == '__main__':
    dir_path_now = "./ExcelDB"
    os.makedirs("./translate", exist_ok=True)
    filename_fiter = converter_file_names.split("\n")
    for name in os.listdir(dir_path_now):
        if name.endswith("json") and name in filename_fiter:
            if translate_json(dir_path_now, name, False):
                print(name)
    print(test_key_words)