import os
import sys
import subprocess
import shutil

# ============ 配置区 ============

# WinRAR 命令行路径
WINRAR_PATH = r"C:\Program File\WinRAR\Rar.exe"

# 目标移动路径（必填，必须已存在）
TARGET_MOVE_PATH = r"D:\agw\cocos"

# 判定阈值：得分 >= 该值即认为命中
SCORE_THRESHOLD = 4

# 是否额外判定子类型（用于打印）
DETECT_SUBTYPE = True

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

def analyze_cocos(file_list):
    """
    对压缩包内文件列表进行 Cocos 特征打分。
    返回: (score, is_match, subtype, reasons)
        score    : 得分
        is_match : 是否达到阈值
        subtype  : "creator-src" / "creator-build" / "cocos2d-x" / "unknown"
        reasons  : 命中的特征描述列表
    """
    if not file_list:
        return 0, False, "unknown", ["无法读取内容或为空"]

    # 统一分隔符
    files = [f.replace('\\', '/') for f in file_list]

    basenames = [os.path.basename(f) for f in files]
    basenames_lower = [b.lower() for b in basenames]

    # 便捷集合
    def any_ext(exts):
        return any(f.lower().endswith(exts) for f in files)

    def any_name(*names):
        return any(b in names for b in basenames_lower)

    def any_in_dir(dirname, exts=None):
        prefix = dirname.rstrip('/') + '/'
        for f in files:
            if f.startswith(prefix):
                if exts is None or f.lower().endswith(exts):
                    return True
        return False

    score = 0
    reasons = []

    # --- Cocos Creator 源码特征 ---
    has_assets_dir = any(f.startswith('assets/') or '/assets/' in f for f in files)
    has_meta = any_ext(('.meta',))
    if has_assets_dir and has_meta:
        score += 5
        reasons.append("assets/ + .meta")

    if any_ext(('.fire', '.scene', '.prefab', '.anim')):
        score += 4
        reasons.append("含 Cocos 场景/预制资源 (.fire/.scene/.prefab/.anim)")

    if any_name('project.json'):
        score += 2
        reasons.append("project.json (Creator 工程配置)")
    if any_name('package.json'):
        # package.json 太通用,只加 1 分,且只有在其它 cocos 信号存在时才有意义
        if has_meta or has_assets_dir:
            score += 1
            reasons.append("package.json")

    if any_in_dir('settings'):
        score += 2
        reasons.append("settings/ 目录")

    # --- Cocos Creator 构建产物特征 ---
    has_index = any(b in ('index.html', 'index.htm') for b in basenames_lower)
    has_cocos_engine = (
        any_name('cocos2d-js-min.js', 'cocos2d.js', 'cocos-js')
        or any(f.startswith('cocos-js/') or '/cocos-js/' in f for f in files)
        or any(f.startswith('cocos2d-js/') for f in files)
        or any('cocos-js' in f.lower() for f in files)
    )
    if has_cocos_engine:
        score += 4
        reasons.append("含 Cocos 引擎文件")

    if has_index and (has_cocos_engine or any_in_dir('src', ('.js',))):
        # 有 index.html 且带引擎或 src 目录
        if has_cocos_engine:
            score += 2
            reasons.append("index.html + 引擎")

    if any(f.lower().endswith('src/settings.json') or f.lower().endswith('src/settings.js')
           for f in files):
        score += 3
        reasons.append("src/settings.json (构建产物配置)")

    # --- Cocos2d-x 原生工程特征 ---
    has_classes = any(f.startswith('Classes/') or '/Classes/' in f for f in files)
    has_resources = any(f.startswith('Resources/') or '/Resources/' in f for f in files)
    has_proj = any(
        f.startswith('proj.') or '/proj.' in f
        for f in files
    )
    has_cpp = any_ext(('.cpp', '.hpp', '.h', '.cc'))
    if has_classes and has_resources:
        score += 3
        reasons.append("Classes/ + Resources/")
    if has_proj:
        score += 2
        reasons.append("proj.* 工程目录")
    if has_cpp and has_resources:
        score += 2
        reasons.append("C++ 源码 + Resources")

    # --- 顶层目录名里的 hint（弱信号）---
    top_dirs = set()
    for f in files:
        parts = f.split('/')
        if len(parts) > 1:
            top_dirs.add(parts[0].lower())
    if any('cocos' in d for d in top_dirs):
        score += 1
        reasons.append(f"顶层目录名含 cocos")

    # --- 子类型判定 ---
    subtype = "unknown"
    if has_assets_dir and has_meta:
        subtype = "creator-src"
    elif has_cocos_engine or any_in_dir('src', ('.js',)) or \
         any(f.lower().endswith('src/settings.json') for f in files):
        subtype = "creator-build"
    elif has_classes and (has_proj or has_cpp):
        subtype = "cocos2d-x"

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

    detected = []        # [(rar_path, score, subtype, reasons)]
    skipped = []         # [(rar_path, score, reasons)]

    for rar_file in rar_files:
        files = list_rar_contents(rar_file)
        score, is_match, subtype, reasons = analyze_cocos(files)
        if is_match:
            detected.append((rar_file, score, subtype, reasons))
        else:
            skipped.append((rar_file, score, reasons))

    if detected:
        print(f"发现 {len(detected)} 个 Cocos 项目压缩包:")
        for rar_path, score, subtype, reasons in detected:
            tag = f"{subtype}" if DETECT_SUBTYPE else "cocos"
            print(f"  [score={score} | {tag}]  {rar_path}")
            print(f"        依据: {'; '.join(reasons)}")
        move_detected_files([p for p, *_ in detected])
    else:
        print("未发现 Cocos 项目压缩包。")

    # 展示未匹配样本（可用于调参）
    if skipped:
        print(f"\n（共 {len(skipped)} 个未匹配，展示前 5 个）")
        for rar_path, score, reasons in skipped[:5]:
            print(f"  [score={score}]  {os.path.basename(rar_path)}")
            if reasons:
                print(f"        命中: {'; '.join(reasons)}")

    input("\n按 Enter 键退出...")


if __name__ == "__main__":
    main()

# ============================================================================
# 判定逻辑梗概
# ----------------------------------------------------------------------------
# 目标: 判断一个 RAR 压缩包是否为 Cocos 项目, 若是则把整个压缩包移动到指定路径。
#
# 总体思路: 加权打分。列出压缩包内文件清单后, 逐项匹配特征并累加分数,
#           总分 >= SCORE_THRESHOLD 即判定为 Cocos 项目。
#
# 一、特征与分值 (score)
#   1) Cocos Creator 源码 (creator-src)
#      - assets/ 目录 且 存在 .meta 文件 ......... +5  (金标准)
#      - 存在 .fire / .scene / .prefab / .anim .. +4
#      - project.json ........................... +2
#      - settings/ 目录 ......................... +2
#      - package.json (仅在已有 Cocos 信号时) ... +1  (弱信号)
#
#   2) Cocos Creator 构建产物 (creator-build)
#      - 含 Cocos 引擎文件
#        (cocos2d-js-min.js / cocos2d.js / cocos-js/ 等) .. +4
#      - index.html + 引擎 ...................... +2
#      - src/settings.json (或 src/settings.js) . +3
#
#   3) Cocos2d-x 原生工程 (cocos2d-x)
#      - Classes/ + Resources/ ................. +3
#      - proj.* (proj.android / proj.win32 等) .. +2
#      - C++ 源码 + Resources/ .................. +2
#
#   4) 弱信号
#      - 顶层目录名含 "cocos" ................... +1
#
# 二、子类型判定 (subtype) —— 只做展示, 不影响是否命中
#   - creator-src  : 有 assets/ 且存在 .meta
#   - creator-build: 有引擎文件 / src/ 下的 js / src/settings.json
#   - cocos2d-x    : 有 Classes/ 且 (有 proj.* 或 C++ 源码)
#   - unknown      : 其它
#
# 三、判定流程
#   1. 校验 WinRAR 路径与目标路径是否有效
#   2. 收集输入 RAR (命令行拖放 或 RAR_PATHS 硬编码)
#   3. 对每个 RAR: Rar.exe lb 列出文件清单 -> analyze_cocos() 打分
#   4. score >= SCORE_THRESHOLD  -> 判定命中, 加入待移动列表
#      否则 -> 记录到 skipped, 仅打印前 5 个便于调参
#   5. 对命中的 RAR 调用 shutil.move 移动到 TARGET_MOVE_PATH
#      (整个压缩包移动, 不解压)
#
# 四、调参建议
#   - 误判多 -> 调高 SCORE_THRESHOLD (如 6)
#   - 漏判多 -> 调低 SCORE_THRESHOLD (如 3), 或查看未匹配样本的原因
#   - 只要 Creator 源码 -> 命中条件改为 subtype == "creator-src"
#   - 不要构建产物     -> subtype == "creator-build" 时直接返回 False
#
# 五、已知边界
#   - 加密头 RAR: Rar.exe lb 会失败 -> 空列表 -> 不会命中
#   - 纯 H5 项目若目录名含 cocos 可能被误判, 靠阈值过滤
#   - 缺少 assets/ 的 Cocos 源码主要靠 .scene/.prefab 补分
# ============================================================================