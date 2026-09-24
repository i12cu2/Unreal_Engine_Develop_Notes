import os
import sys
import subprocess
import shutil
import re

# ============ 配置区 ============

# WinRAR 命令行路径
WINRAR_PATH = r"C:\Program File\WinRAR\Rar.exe"

# 目标移动路径（必填，必须已存在）
TARGET_MOVE_PATH = r"D:\agw\Scratch3"

# 判定阈值：得分 >= 该值即认为命中
SCORE_THRESHOLD = 4

# 若填写路径则优先使用；留空 [] 时从拖放参数读取
RAR_PATHS = [
    # r"D:\SomeArchive.rar",
]

# ==================================


def validate_winrar():
    if not os.path.exists(WINRAR_PATH):
        print(f"错误: WinRAR 未找到在 {WINRAR_PATH}")
        return False
    return True


def validate_target_path():
    if not TARGET_MOVE_PATH:
        print("错误: 未配置 TARGET_MOVE_PATH")
        return False
    if not os.path.exists(TARGET_MOVE_PATH):
        print(f"错误: 目标路径不存在: {TARGET_MOVE_PATH}")
        return False
    if not os.path.isdir(TARGET_MOVE_PATH):
        print(f"错误: 目标路径不是文件夹: {TARGET_MOVE_PATH}")
        return False
    return True


def collect_input_paths():
    if RAR_PATHS:
        return [os.path.abspath(p) for p in RAR_PATHS]
    if len(sys.argv) < 2:
        print("请拖放一个或多个 RAR 文件（或包含 RAR 的文件夹）到此脚本上")
        input("按 Enter 键退出...")
        sys.exit(1)
    return [os.path.abspath(path) for path in sys.argv[1:]]


def find_all_rar_files(paths):
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
    """用 Rar.exe lb 列出压缩包内所有文件（含相对路径）"""
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


# ---------- 判定核心 ----------

# Scratch 资源文件通常是以内容的 MD5 命名的 32 位十六进制串
_HASH_NAME_RE = re.compile(r'^[0-9a-f]{32}$')


def _looks_like_scratch_asset(filename):
    """判断文件名是否为 Scratch 风格的哈希资源名（不含扩展名）"""
    stem, _ = os.path.splitext(filename)
    return bool(_HASH_NAME_RE.match(stem.lower()))


def analyze_scratch(file_list):
    """
    对压缩包内文件列表进行 Scratch 3.0 项目打分。
    返回: (score, is_match, subtype, reasons)
        subtype 取值:
            "sb3-file"   —— 压缩包里含 .sb3 文件
            "sb2-file"   —— 压缩包里含 .sb2 文件（Scratch 2.0）
            "sb3-dir"    —— 压缩包本身就是 .sb3 解压后的结构
            "unknown"
    """
    if not file_list:
        return 0, False, "unknown", ["无法读取内容或为空"]

    files = [f.replace('\\', '/') for f in file_list]
    basenames = [os.path.basename(f) for f in files]
    basenames_lower = [b.lower() for b in basenames]

    score = 0
    reasons = []

    # --- 形态 A: 压缩包里直接含有 .sb3 / .sb2 文件 ---
    sb3_files = [f for f in files if f.lower().endswith('.sb3')]
    sb2_files = [f for f in files if f.lower().endswith('.sb2')]

    if sb3_files:
        score += 5
        reasons.append(f"含 {len(sb3_files)} 个 .sb3 文件")

    if sb2_files:
        score += 4
        reasons.append(f"含 {len(sb2_files)} 个 .sb2 文件")

    # --- 形态 B: 压缩包本身就是 .sb3 解压后的结构 ---
    project_json_present = any(b == 'project.json' for b in basenames_lower)
    if project_json_present:
        score += 3
        reasons.append("含 project.json")

    # 资源文件（哈希命名 + 常见 Scratch 扩展名）
    asset_exts = ('.png', '.svg', '.jpg', '.jpeg', '.bmp', '.wav', '.mp3', '.ogg')
    asset_count = sum(
        1 for b in basenames
        if _looks_like_scratch_asset(b) and b.lower().endswith(asset_exts)
    )
    if asset_count >= 2:
        score += 2
        reasons.append(f"含 {asset_count} 个哈希命名资源")

    # 目录层级通常很浅（project.json + 资源都在同一层）
    depth_max = max((f.count('/') for f in files), default=0)
    if project_json_present and depth_max <= 1:
        score += 1
        reasons.append("层级很浅(典型 sb3 结构)")

    # --- 子类型判定 ---
    subtype = "unknown"
    if sb3_files:
        subtype = "sb3-file"
    elif sb2_files:
        subtype = "sb2-file"
    elif project_json_present and asset_count >= 2:
        subtype = "sb3-dir"

    is_match = score >= SCORE_THRESHOLD
    return score, is_match, subtype, reasons


def move_detected_files(detected_rars):
    print(f"\n开始移动 {len(detected_rars)} 个文件到: {TARGET_MOVE_PATH}")
    ok, fail = 0, 0
    for rar_path in detected_rars:
        filename = os.path.basename(rar_path)
        destination = os.path.join(TARGET_MOVE_PATH, filename)
        if os.path.exists(destination):
            print(f"跳过 {filename}：目标位置已存在同名文件")
            fail += 1
            continue
        try:
            shutil.move(rar_path, destination)
            print(f"已移动: {filename}")
            ok += 1
        except Exception as e:
            print(f"移动失败 {filename}: {e}")
            fail += 1
    print(f"\n移动完成: 成功 {ok} 个, 失败 {fail} 个")
    return ok


def main():
    if not validate_winrar():
        input("按 Enter 键退出...")
        sys.exit(1)
    if not validate_target_path():
        input("按 Enter 键退出...")
        sys.exit(1)

    input_paths = collect_input_paths()
    rar_files = find_all_rar_files(input_paths)

    if not rar_files:
        print("未找到任何 RAR 文件。")
        input("按 Enter 键退出...")
        sys.exit(0)

    print(f"找到 {len(rar_files)} 个 RAR 文件，正在检查内容...\n")

    detected = []   # [(rar_path, score, subtype, reasons)]
    skipped = []    # [(rar_path, score, reasons)]

    for rar_file in rar_files:
        files = list_rar_contents(rar_file)
        score, is_match, subtype, reasons = analyze_scratch(files)
        if is_match:
            detected.append((rar_file, score, subtype, reasons))
        else:
            skipped.append((rar_file, score, reasons))

    if detected:
        print(f"发现 {len(detected)} 个 Scratch 项目压缩包:")
        for rar_path, score, subtype, reasons in detected:
            print(f"  [score={score} | {subtype}]  {rar_path}")
            print(f"        依据: {'; '.join(reasons)}")
        move_detected_files([p for p, *_ in detected])
    else:
        print("未发现 Scratch 项目压缩包。")

    if skipped:
        print(f"\n（共 {len(skipped)} 个未匹配，展示前 5 个）")
        for rar_path, score, reasons in skipped[:5]:
            print(f"  [score={score}]  {os.path.basename(rar_path)}")
            if reasons:
                print(f"        命中: {'; '.join(reasons)}")

    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()