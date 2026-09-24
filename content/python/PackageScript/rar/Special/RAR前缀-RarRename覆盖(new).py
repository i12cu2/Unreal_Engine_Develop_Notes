import os
import re
import sys
import argparse
from pathlib import Path
import subprocess

def ensure_rarfile():
    """检测并自动安装 rarfile 库"""
    global rarfile, RarFile   # 新增这一行，声明全局变量
    try:
        import rarfile
        from rarfile import RarFile
        return True
    except ImportError:
        print("检测到缺少 rarfile 库，正在自动安装...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "rarfile"])
            print("安装成功！正在重新导入...")
            import rarfile
            from rarfile import RarFile
            return True
        except Exception as e:
            print(f"自动安装失败: {e}")
            print("请检查网络连接或手动运行以下命令安装：")
            print("pip install rarfile")
            print("\n按任意键退出...")
            if sys.platform.startswith('win'):
                import msvcrt
                msvcrt.getch()
            else:
                input()
            sys.exit(1)

# 执行自动安装检测
ensure_rarfile()

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

def collect_rar_files(paths):
    """
    从给定的路径列表中收集所有RAR文件
    支持文件和文件夹路径
    """
    rar_files = []
    
    for path_str in paths:
        path = Path(path_str)
        
        if not path.exists():
            print(f"警告: 路径不存在: {path}")
            continue
            
        if path.is_file():
            # 如果是文件，检查是否为RAR文件
            if path.suffix.lower() == '.rar':
                rar_files.append(str(path))
                print(f"添加RAR文件: {path.name}")
            else:
                print(f"跳过非RAR文件: {path.name}")
                
        elif path.is_dir():
            # 如果是文件夹，递归搜索所有RAR文件
            try:
                dir_rar_count = 0
                for rar_path in path.rglob('*.rar'):
                    rar_files.append(str(rar_path))
                    dir_rar_count += 1
                print(f"在文件夹 '{path.name}' 中发现 {dir_rar_count} 个RAR文件")
            except Exception as e:
                print(f"扫描文件夹失败 '{path}': {str(e)}")
    
    return rar_files

def process_rar_file_list(rar_files):
    """处理RAR文件列表"""
    for rar_path in rar_files:
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
            # 使用正则表达式移除原有前缀
            original_name = re.sub(r'^\[.*?\]', '', os.path.basename(rar_path)).lstrip()
            new_filename = f"[{extracted_name}]{original_name}"
            new_path = os.path.join(os.path.dirname(rar_path), new_filename)
            
            if not os.path.exists(new_path):
                os.rename(rar_path, new_path)
                print(f"重命名成功: {os.path.basename(rar_path)} -> {new_filename}")
            else:
                print(f"文件已存在，跳过: {new_filename}")
        else:
            print(f"未提取到有效名称，保持原样: {os.path.basename(rar_path)}")

def wait_for_exit():
    """等待用户按键退出"""
    if sys.platform.startswith('win'):
        # Windows系统
        print("\n程序执行完毕，按任意键退出...")
        import msvcrt
        msvcrt.getch()
    else:
        # 其他系统（如Linux、macOS）
        input("\n程序执行完毕，按回车键退出...")

def main():
    # 使用argparse处理命令行参数，支持拖放操作
    parser = argparse.ArgumentParser(description='RAR文件重命名工具')
    parser.add_argument('paths', nargs='*', help='要处理的文件或文件夹路径')
    args = parser.parse_args()
    
    # 如果没有提供路径参数，使用交互式输入
    if not args.paths:
        print("提示: 您可以直接将文件或文件夹拖放到此程序上，或手动输入路径")
        input_path = input("请拖放文件或文件夹到此处，或直接输入路径: ").strip().strip('"')
        if not input_path:
            print("未提供路径，程序退出")
            wait_for_exit()
            return
        target_paths = [input_path]
    else:
        target_paths = args.paths
    
    print("=" * 60)
    print("开始扫描RAR文件...")
    print("=" * 60)
    
    # 收集所有RAR文件
    rar_files = collect_rar_files(target_paths)
    
    if not rar_files:
        print("未找到任何RAR文件，程序退出")
        wait_for_exit()
        return
        
    print(f"\n总共发现待处理RAR文件: {len(rar_files)}个")
    print("文件列表:")
    for i, rar_file in enumerate(rar_files, 1):
        print(f"  {i:2d}. {rar_file}")
    
    # 修改确认方式：按回车继续，其他键取消
    print(f"\n按回车键开始处理这 {len(rar_files)} 个文件，按其他任意键取消...")
    response = input()
    if response != "":
        print("用户取消操作")
        wait_for_exit()
        return
    
    print("\n开始处理RAR文件...")
    print("=" * 60)
    
    # 处理RAR文件
    process_rar_file_list(rar_files)
    
    print("=" * 60)
    print("所有文件处理完成!")
    
    # 程序结束前等待用户按键
    wait_for_exit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n程序发生未捕获的异常: {e}")
        import traceback
        traceback.print_exc()
        # 确保等待用户按键
        if sys.platform.startswith('win'):
            import msvcrt
            print("\n按任意键退出...")
            msvcrt.getch()
        else:
            input("\n按回车键退出...")