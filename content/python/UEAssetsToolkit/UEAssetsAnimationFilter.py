r"""
遍历 D:\660p1.77T\overContent 下的每个单位素材文件夹：

1. 深度查找该单位内是否存在名字命中 TARGET_FOLDER_NAMES 的文件夹
   （不区分大小写），只要出现其中任意一个即视为命中。
2. 命中则把整个单位素材文件夹移动到 TARGET_DIR；
   未命中则原地不动。

说明：
- 移动对象是整个一级子文件夹本身，不拆分内部结构。
- 目标目录已有同名文件夹时，自动追加 _1、_2 后缀，避免覆盖。
"""

import os
import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\660p1.77T\Anim")   # 素材根目录
TARGET_DIR = Path(r"D:\660p1.77T\overContentAnim2") # 命中的单位移动目标（请按需修改）

# 判定名单：只要单位内深度搜索出现其中任意一个文件夹名（不区分大小写）即命中
TARGET_FOLDER_NAMES = [
    "animation",
    "animations",
]

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def normalize(names):
    """统一转小写，方便做不区分大小写的比较"""
    return {n.lower() for n in names}


def contains_target_folder(unit: Path, names_lower) -> bool:
    """深度查找 unit 下是否存在名字命中名单的文件夹"""
    for dirpath, dirnames, _ in os.walk(unit):
        for d in dirnames:
            if d.lower() in names_lower:
                return True
    return False


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
        sys.exit(1)

    if not DRY_RUN:
        TARGET_DIR.mkdir(parents=True, exist_ok=True)

    # 排除目标目录本身，防止误扫、误移
    target_resolved = TARGET_DIR.resolve()

    names_lower = normalize(TARGET_FOLDER_NAMES)

    units = sorted(
        (p for p in SOURCE_DIR.iterdir()
         if p.is_dir() and p.resolve() != target_resolved),
        key=lambda p: p.name.lower(),
    )
    total = len(units)
    print(f"共发现 {total} 个素材单位。\n")

    moved_count = 0
    skipped_count = 0

    for i, unit in enumerate(units, 1):
        try:
            hit = contains_target_folder(unit, names_lower)
        except Exception as e:
            print(f"[{i}/{total}] [扫描失败] {unit.name} -> {e}")
            skipped_count += 1
            continue

        if not hit:
            skipped_count += 1
            print(f"[{i}/{total}] [未命中] 保持不动：{unit.name}")
            continue

        dest = unique_dest(TARGET_DIR, unit.name)

        if DRY_RUN:
            print(f"[{i}/{total}] [命中] {unit}")
            print(f"                    ->  {dest}   （预览模式，未移动）")
            moved_count += 1
            continue

        try:
            shutil.move(str(unit), str(dest))
            print(f"[{i}/{total}] [命中] 已移动：{unit.name}  ->  {dest}")
            moved_count += 1
        except Exception as e:
            print(f"[{i}/{total}] [命中] 移动失败：{unit.name} -> {e}")
            skipped_count += 1

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  命中并移动 : {moved_count}")
    print(f"  跳过（未命中/失败） : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()