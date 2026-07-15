import os


#  重命名文件夹
# os.rename('translate', 'ExcelDB') 或 shutil.move('translate', 'ExcelDB')
# 拷贝文件夹，如果目标文件夹已存在，会报错，可以先删除或使用 dirs_exist_ok=True
# shutil.copytree(source, destination, dirs_exist_ok=True)
# 删除整个文件夹及其所有内容
# shutil.rmtree('ExcelDB')

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


def execute_clean_command(delete_file_list: list, fake_execute=True):
    for delete_file_path in delete_file_list:
        if fake_execute:
            print(f"假装删除({os.path.basename(delete_file_path)}){delete_file_path}")
        else:
            delete_all_in_dir(delete_file_path)


def enum_all_file_in_dir(dir_path: str) -> list:
    delete_file_list = []
    if not os.path.exists(dir_path):
        return delete_file_list

    print(f"存在{dir_path}文件夹，进行清理")
    # 设置topdown参数进行深度优先遍历
    file_num = 0
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for name in files:
            file_num += 1
            file_path = os.path.join(root, name)

            if name.__eq__("_remote.repositories") or name.endswith("CppClean.log") or name.endswith(
                    "vcxproj.FileListAbsolute.txt") or name.endswith(".log") or name.endswith(".lastUpdated"):
                delete_file_list.append(file_path)
            elif name.endswith(".o") and root.__contains__("MinFFS-1.7.6.1"):
                delete_file_list.append(file_path)
            elif name.startswith("events.out.tfevents"):
                delete_file_list.append(file_path)
            elif name.__eq__("Browse.VC.db") and root.__contains__(".vs"):
                delete_file_list.append(file_path)
            elif name.endswith(".obj"):
                if os.path.basename(root).__eq__("Debug") or os.path.basename(root).__eq__("Release"):
                    delete_file_list.append(file_path)
        for dir_name in dirs:
            file_num += 1
            sub_dir_path = os.path.join(root, dir_name)
            if dir_name.__eq__("ipch") or dir_name.__eq__("__pycache__") or dir_name.endswith(".tlog"):
                delete_file_list.append(sub_dir_path)
            elif dir_name.__eq__("ShaderCache") and os.path.basename(root).__eq__("Library"):
                delete_file_list.append(sub_dir_path)
            elif dir_name.__eq__("il2cpp_cache") and os.path.basename(root).__eq__("Library"):
                delete_file_list.append(sub_dir_path)
            elif dir_name.__eq__("obj") and os.path.exists(os.path.join(sub_dir_path,"project.nuget.cache")):
                delete_file_list.append(sub_dir_path)
            elif dir_name.__eq__(".claude"):
                delete_file_list.append(sub_dir_path)
        if file_num % 1000 == 0:
            print(f"已扫描{file_num}个文件")

    return delete_file_list


if __name__ == '__main__':
    dFiles = enum_all_file_in_dir(os.path.abspath("."))
    execute_clean_command(dFiles, True)
    yesOrNo = input('确认是否删除(y/N):')
    if yesOrNo.__eq__('y') or yesOrNo.__eq__("Y"):
        execute_clean_command(dFiles, False)
    else:
        print("您选择了否，已跳过删除命令")
