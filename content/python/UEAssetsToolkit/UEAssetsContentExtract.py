"""
处理 D:\agw\300 下的素材单位：
1. 在素材单位内深度搜索“类 Content 文件夹”：
   只要某个文件夹的直接子文件夹中，包含以下四个名字中的任意一个
   （不区分大小写），就把它视为 Content 文件夹：
       __ExternalActors__
       __ExternalObjects__
       Collections
       Developers
2. 对每个找到的 Content 文件夹，列出它的直接子文件夹，
   并排除上述四个名字。若剩余子文件夹数量恰好为 1，
   则将该唯一子文件夹移动到 D:\agw\t58\Content\。
3. 只要某个素材单位中有任意一个子文件夹被成功移动，
   就把整个素材单位移入回收站。
"""

import os
import shutil
import sys
from pathlib import Path

try:
    from send2trash import send2trash
except ImportError:
    print("缺少 send2trash 库，请先运行：pip install send2trash")
    sys.exit(1)

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\agw\300")            # 素材根目录
DEST_CONTENT_DIR = Path(r"D:\agw\t58\Content")  # 提取出的文件夹存放位置

# 标志文件夹：只要某个文件夹的直接子文件夹中包含其中任意一个，
# 就认为该文件夹是 Content 类文件夹
MARKER_DIRS = {
    "__externalactors__",
    "__externalobjects__",
    "collections",
    "developers",
}

# 排除名单：在 Content 文件夹内，这些子文件夹不计入有效数量
EXCLUDE_DIRS = MARKER_DIRS  # 与标志文件夹相同

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def find_content_folders(unit: Path):
    """
    在素材单位内深度搜索所有“类 Content 文件夹”。
    判定条件：该文件夹的直接子文件夹（第一层）中，
    包含 MARKER_DIRS 中的任意一个名字（不区分大小写）。
    注意：不把素材单位根目录自身算作 Content 文件夹。
    """
    content_folders = []
    for dirpath, dirnames, filenames in os.walk(unit):
        current = Path(dirpath)
        if current == unit:
            continue  # 跳过素材单位根
        names_lower = {d.lower() for d in dirnames}
        if names_lower & MARKER_DIRS:
            content_folders.append(current)
    return content_folders


def unique_dest(dest_dir: Path, name: str) -> Path:
    """目标已存在同名文件夹时，自动加 _1、_2 后缀，避免覆盖"""
    dest = dest_dir / name
    if not dest.exists():
        return dest
    i = 1
    while True:
        cand = dest_dir / f"{name}_{i}"
        if not cand.exists():
            return cand
        i += 1


def main():
    if not SOURCE_DIR.is_dir():
        print(f"[错误] 源目录不存在：{SOURCE_DIR}")
        return

    if not DRY_RUN:
        DEST_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    units = sorted(
        (p for p in SOURCE_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    print(f"共发现 {len(units)} 个素材单位。\n")

    processed_units = 0

    for unit in units:
        print(f"处理素材单位：{unit.name}")
        content_folders = find_content_folders(unit)

        if not content_folders:
            print("  未找到包含标志文件夹的 Content 类文件夹，跳过。\n")
            continue

        unit_moved = False  # 标记该素材单位是否有成功移动

        for content in content_folders:
            print(f"  检查 Content 类文件夹：{content}")
            try:
                subfolders = [d for d in content.iterdir() if d.is_dir()]
            except Exception as e:
                print(f"    无法访问：{e}")
                continue

            # 过滤排除名单
            valid = [d for d in subfolders if d.name.lower() not in EXCLUDE_DIRS]
            print(f"    有效子文件夹（排除后）：{[d.name for d in valid]}")

            if len(valid) == 1:
                src_folder = valid[0]
                dest_folder = unique_dest(DEST_CONTENT_DIR, src_folder.name)

                if DRY_RUN:
                    print(f"    [预览] 将移动：{src_folder}  ->  {dest_folder}")
                    unit_moved = True
                else:
                    try:
                        shutil.move(str(src_folder), str(dest_folder))
                        print(f"    已移动：{src_folder.name}  ->  {dest_folder}")
                        unit_moved = True
                    except Exception as e:
                        print(f"    移动失败：{e}")
            else:
                print(f"    有效子文件夹数量为 {len(valid)}，不符合条件（必须恰好为 1），跳过。")

        # 只要该素材单位中有任何一个文件夹被成功移动，就删除整个素材单位
        if unit_moved:
            if DRY_RUN:
                print(f"  [预览] 将把素材单位移入回收站：{unit.name}")
                processed_units += 1
            else:
                try:
                    send2trash(str(unit))
                    print(f"  已将素材单位移入回收站：{unit.name}")
                    processed_units += 1
                except Exception as e:
                    print(f"  移入回收站失败：{e}")
        else:
            print("  没有成功移动任何文件夹，不删除该素材单位。")

        print("-" * 60)

    print(f"\n全部完成。共处理并移入回收站的素材单位数量：{processed_units}")


if __name__ == "__main__":
    main()