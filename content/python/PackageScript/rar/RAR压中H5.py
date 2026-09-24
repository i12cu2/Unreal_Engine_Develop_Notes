import os
import sys
import subprocess
import shutil

# ============ 配置区 ============

# WinRAR 命令行路径
WINRAR_PATH = r"C:\Program File\WinRAR\Rar.exe"

# 目标移动路径（必填，必须已存在）
TARGET_MOVE_PATH = r"D:\agw\html"

# 判定参数
REQUIRE_INDEX = False       # True: 必须包含 index.html / index.htm
REQUIRE_JS_OR_CSS = True    # True: 除了 HTML，还必须含 .js 或 .css

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


def is_html_project(file_list):
    """
    判断压缩包是否为 HTML 项目。
    返回 (是否匹配, 判定说明)
    """
    if not file_list:
        return False, "无法读取内容或为空"

    # 统一分隔符，便于 basename 处理
    normalized = [f.replace('\\', '/') for f in file_list]

    html_files = [f for f in normalized if f.lower().endswith(('.html', '.htm'))]
    if not html_files:
        return False, "不含 HTML 文件"

    js_files  = [f for f in normalized if f.lower().endswith('.js')]
    css_files = [f for f in normalized if f.lower().endswith('.css')]

    has_index = any(
        os.path.basename(f).lower() in ('index.html', 'index.htm')
        for f in html_files
    )

    # 组装判定说明
    reasons = [f"{len(html_files)} 个 HTML"]
    if has_index:
        reasons.append("含 index")
    if js_files:
        reasons.append(f"{len(js_files)} 个 JS")
    if css_files:
        reasons.append(f"{len(css_files)} 个 CSS")
    reason_text = ", ".join(reasons)

    # 判定规则
    if REQUIRE_INDEX and not has_index:
        return False, f"缺少 index.html ({reason_text})"
    if REQUIRE_JS_OR_CSS and not (js_files or css_files):
        return False, f"只有 HTML 无 JS/CSS ({reason_text})"

    return True, reason_text


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

    detected = []          # [(rar_path, reason), ...]
    skipped_reasons = []   # [(rar_path, reason), ...]  仅用于展示前几个被排除的

    for rar_file in rar_files:
        files = list_rar_contents(rar_file)
        ok, reason = is_html_project(files)
        if ok:
            detected.append((rar_file, reason))
        else:
            skipped_reasons.append((rar_file, reason))

    # 输出结果
    if detected:
        print(f"发现 {len(detected)} 个 HTML 项目压缩包:")
        for rar_path, reason in detected:
            print(f"  [{reason}]  {rar_path}")

        move_detected_files([p for p, _ in detected])
    else:
        print("未发现 HTML 项目压缩包。")

    # 简短展示被排除的样本，便于你调整判定参数
    if skipped_reasons:
        print(f"\n（共 {len(skipped_reasons)} 个未匹配，展示前 5 个原因）")
        for rar_path, reason in skipped_reasons[:5]:
            print(f"  [{reason}]  {os.path.basename(rar_path)}")

    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()