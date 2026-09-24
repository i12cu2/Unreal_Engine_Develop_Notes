"""
遍历目标目录，深度搜索并删除指定的垃圾文件夹 / 文件，
然后再重新遍历一遍，删除所有空文件夹。

流程：
1. 深度遍历 TARGET_DIR，删除名字命中 TARGET_FOLDER_NAMES 的文件夹（整棵子树）；
2. 深度遍历 TARGET_DIR，删除名字命中 TARGET_FILE_NAMES 的文件；
3. 重新遍历 TARGET_DIR，自底向上删除所有空文件夹。
"""

import os
import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
TARGET_DIR = Path(r"D:\660p\动画\dir")   # 待清理的根目录

# 要删除的文件夹名字（不区分大小写）
TARGET_FOLDER_NAMES = [
    "库文件",
    "源文件",
    "Splash",
    #"SOURCE",
    "Splash",
    "StarterContent",
]

# 要删除的文件名字（不区分大小写）
TARGET_FILE_NAMES = [
    "manifest",
    ".DS_Store",
    "__MACOSX"
]

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def normalize(names):
    """统一转小写，方便做不区分大小写的比较"""
    return {n.lower() for n in names}


def pass_delete_folders(root: Path, folder_names_lower):
    """第一遍：深度遍历，删除名字命中的文件夹"""
    deleted = 0
    # topdown=False 先处理深层，避免父目录被提前删除导致 os.walk 报错
    # 实际这里用自底向上逐层扫描更稳，直接 os.walk 即可
    for dirpath, dirnames, _ in os.walk(root, topdown=False):
        for d in list(dirnames):
            if d.lower() in folder_names_lower:
                target = Path(dirpath) / d
                print(f"  [文件夹] {'预览' if DRY_RUN else '删除'}：{target}")
                if not DRY_RUN:
                    try:
                        shutil.rmtree(target)
                        deleted += 1
                    except Exception as e:
                        print(f"    删除失败：{e}")
                else:
                    deleted += 1
    return deleted


def pass_delete_files(root: Path, file_names_lower):
    """第二遍：深度遍历，删除名字命中的文件"""
    deleted = 0
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower() in file_names_lower:
                target = Path(dirpath) / f
                print(f"  [文件]   {'预览' if DRY_RUN else '删除'}：{target}")
                if not DRY_RUN:
                    try:
                        target.unlink()
                        deleted += 1
                    except Exception as e:
                        print(f"    删除失败：{e}")
                else:
                    deleted += 1
    return deleted


def pass_delete_empty_dirs(root: Path):
    """第三遍：自底向上删除空文件夹（保留根目录本身）"""
    deleted = 0
    # 多跑几轮，直到没有新的空文件夹被删掉
    while True:
        removed_this_round = 0
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            current = Path(dirpath)
            if current == root:
                continue  # 不删根目录
            try:
                if not any(current.iterdir()):
                    print(f"  [空目录] {'预览' if DRY_RUN else '删除'}：{current}")
                    if not DRY_RUN:
                        current.rmdir()
                    removed_this_round += 1
            except Exception as e:
                print(f"    处理失败：{e}")
        deleted += removed_this_round
        if DRY_RUN or removed_this_round == 0:
            break
    return deleted


def main():
    if not TARGET_DIR.is_dir():
        print(f"[错误] 目标目录不存在：{TARGET_DIR}")
        sys.exit(1)

    folder_names_lower = normalize(TARGET_FOLDER_NAMES)
    file_names_lower = normalize(TARGET_FILE_NAMES)

    print(f"目标目录：{TARGET_DIR}")
    print(f"删除文件夹名单：{TARGET_FOLDER_NAMES}")
    print(f"删除文件名单：  {TARGET_FILE_NAMES}")
    print(f"模式：{'预览（DRY_RUN）' if DRY_RUN else '实际执行'}")
    print("=" * 60)

    print("\n[第 1 遍] 删除命中名单的文件夹...")
    n_folder = pass_delete_folders(TARGET_DIR, folder_names_lower)
    print(f"  -> 共 {n_folder} 个文件夹\n")

    print("[第 2 遍] 删除命中名单的文件...")
    n_file = pass_delete_files(TARGET_DIR, file_names_lower)
    print(f"  -> 共 {n_file} 个文件\n")

    print("[第 3 遍] 删除空文件夹...")
    n_empty = pass_delete_empty_dirs(TARGET_DIR)
    print(f"  -> 共 {n_empty} 个空目录\n")

    print("=" * 60)
    print(f"完成。文件夹 {n_folder} 个，文件 {n_file} 个，空目录 {n_empty} 个。")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()