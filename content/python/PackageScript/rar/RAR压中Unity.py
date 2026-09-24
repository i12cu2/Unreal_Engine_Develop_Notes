import os
import sys
import subprocess
import shutil

# ============ 配置区 ============

# WinRAR 命令行路径（Rar.exe 或 WinRAR.exe 均可，推荐用 Rar.exe）
WINRAR_PATH = r"C:\Program File\WinRAR\Rar.exe"

# 目标移动路径（必填，且必须已存在）
TARGET_MOVE_PATH = r"D:\agw\unity"

# 需要检测的扩展名（压缩包内存在该类型文件则触发移动）
TARGET_EXTENSION = ".unitypackage"

# 若此处填写了 RAR 文件/文件夹路径，则优先使用；
# 留空 [] 时，则从命令行参数（拖放）中获取
RAR_PATHS = [
    # r"D:\SomeArchive.rar",
]

# ==================================


def validate_winrar():
    """验证 WinRAR 是否存在"""
    if not os.path.exists(WINRAR_PATH):
        print(f"错误: WinRAR 未找到在 {WINRAR_PATH}")
        return False
    return True


def validate_target_path():
    """验证目标移动路径是否有效"""
    if not TARGET_MOVE_PATH:
        print("错误: 未配置目标路径 TARGET_MOVE_PATH")
        return False
    if not os.path.exists(TARGET_MOVE_PATH):
        print(f"错误: 目标路径不存在: {TARGET_MOVE_PATH}")
        return False
    if not os.path.isdir(TARGET_MOVE_PATH):
        print(f"错误: 目标路径不是文件夹: {TARGET_MOVE_PATH}")
        return False
    return True


def collect_input_paths():
    """收集待处理的 RAR 文件 / 文件夹路径"""
    if RAR_PATHS:
        return [os.path.abspath(p) for p in RAR_PATHS]

    if len(sys.argv) < 2:
        print("请拖放一个或多个 RAR 文件（或包含 RAR 的文件夹）到此脚本上")
        input("按 Enter 键退出...")
        sys.exit(1)

    return [os.path.abspath(path) for path in sys.argv[1:]]


def find_all_rar_files(paths):
    """递归查找所有 RAR 文件"""
    rar_files = []
    for path in paths:
        if os.path.isfile(path) and path.lower().endswith('.rar'):
            rar_files.append(os.path.abspath(path))
        elif os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.lower().endswith('.rar'):
                        rar_files.append(os.path.abspath(os.path.join(root, file)))
    return rar_files


def list_rar_contents(rar_path):
    """列出压缩包内所有文件（含路径）"""
    try:
        result = subprocess.run(
            [WINRAR_PATH, 'lb', rar_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            check=True
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []
    except Exception:
        return []


def contains_target_files(file_list):
    """检查文件列表是否包含目标扩展名文件"""
    return any(f.lower().endswith(TARGET_EXTENSION) for f in file_list)


def move_detected_files(detected_rars):
    """把检测到的 RAR 文件移动到目标路径"""
    print(f"\n开始移动 {len(detected_rars)} 个文件到: {TARGET_MOVE_PATH}")
    successful_moves = 0
    failed_moves = 0

    for rar_path in detected_rars:
        filename = os.path.basename(rar_path)
        destination = os.path.join(TARGET_MOVE_PATH, filename)

        if os.path.exists(destination):
            print(f"跳过 {filename}：目标位置已存在同名文件")
            failed_moves += 1
            continue

        try:
            shutil.move(rar_path, destination)
            print(f"已移动: {filename}")
            successful_moves += 1
        except Exception as e:
            print(f"移动失败 {filename}: {str(e)}")
            failed_moves += 1

    print(f"\n移动操作完成: 成功 {successful_moves} 个, 失败 {failed_moves} 个")
    return successful_moves


def main():
    # 1. 环境校验
    if not validate_winrar():
        input("按 Enter 键退出...")
        sys.exit(1)

    if not validate_target_path():
        input("按 Enter 键退出...")
        sys.exit(1)

    # 2. 收集输入
    input_paths = collect_input_paths()
    rar_files = find_all_rar_files(input_paths)

    if not rar_files:
        print("未找到任何 RAR 文件。")
        input("按 Enter 键退出...")
        sys.exit(0)

    print(f"找到 {len(rar_files)} 个 RAR 文件，正在检查内容...\n")

    # 3. 逐个检查，筛选出包含 .unitypackage 的 RAR
    detected_rars = []
    for rar_file in rar_files:
        files = list_rar_contents(rar_file)
        if files and contains_target_files(files):
            detected_rars.append(rar_file)

    # 4. 输出并移动
    if detected_rars:
        print(f"发现以下 {len(detected_rars)} 个 RAR 中包含 {TARGET_EXTENSION}:")
        for rar_path in detected_rars:
            print(f"  {rar_path}")

        move_detected_files(detected_rars)
    else:
        print(f"未发现包含 {TARGET_EXTENSION} 的 RAR 文件。")

    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()