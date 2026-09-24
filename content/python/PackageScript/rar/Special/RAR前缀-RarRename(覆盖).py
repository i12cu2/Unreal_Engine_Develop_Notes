import os
import re
import rarfile
from rarfile import RarFile

def should_skip_folder(folder_name):
    """判断是否需要跳过该文件夹并继续深入"""
    return folder_name in ("Content", "库文件", "data", "config")

def normalize_path(path):
    """统一使用正斜杠处理路径"""
    return path.replace('\\', '/').rstrip('/')

def get_extracted_name(rar):
    def recurse(current_dir):
        current_dir = normalize_path(current_dir)
        folders = set()
        
        for entry in rar.infolist():
            if entry.isdir():
                full_path = normalize_path(entry.filename)
                parent = normalize_path(os.path.dirname(full_path))
                
                if parent == current_dir:
                    folder_name = os.path.basename(full_path)
                    folders.add(folder_name)

        # 处理跳过逻辑
        filtered = [f for f in folders if not should_skip_folder(f)]
        
        if len(filtered) == 1:
            return filtered[0].replace(' ', '')  # 去除空格
        elif len(folders) == 1:
            next_dir = os.path.join(current_dir, list(folders)[0])
            return recurse(next_dir)
        else:
            return None

    return recurse("")

def process_rar_files(directory):
    # 递归遍历所有子目录
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # 修改点1：移除对[开头的过滤，只过滤非rar文件
            if not filename.lower().endswith(".rar"):
                continue
            
            rar_path = os.path.join(root, filename)
            try:
                with RarFile(rar_path) as rf:
                    extracted_name = get_extracted_name(rf)
            except rarfile.NeedFirstVolume:
                print(f"跳过多卷压缩文件: {rar_path}")
                continue
            except rarfile.PasswordRequired:
                print(f"需要密码，跳过: {rar_path}")
                continue
            except Exception as e:
                print(f"处理文件 {rar_path} 时出错: {e}")
                continue

            if extracted_name:
                # 修改点2：使用正则表达式移除原有前缀
                original_name = re.sub(r'^\[.*?\]', '', filename).lstrip()
                new_filename = f"[{extracted_name}]{original_name}"
                new_path = os.path.join(root, new_filename)
                
                if not os.path.exists(new_path):
                    os.rename(rar_path, new_path)
                    print(f"重命名成功: {rar_path} -> {new_path}")
                else:
                    print(f"文件已存在，跳过: {new_path}")
            else:
                print(f"未提取到有效名称，保持原样: {rar_path}")

if __name__ == "__main__":
    process_rar_files(r"F:\UE资源整合包")