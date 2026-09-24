r"""
遍历 D:\agw\300 下的每个素材单位（一级子文件夹），
深度搜索是否存在 .exe 文件（不区分大小写）。
若存在，则把整个素材单位文件夹移动到 D:\agw\exe。

说明：
- 只移动一级子文件夹本身，不递归拆分内部结构。
- 目标目录已存在同名文件夹时，自动追加 _1、_2 后缀，避免覆盖。
"""

import os
import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\agw\300")   # 素材根目录
EXE_DIR    = Path(r"D:\agw\exe")   # 含 exe 的素材单位归置目录

# 判定后缀：只要素材单位内深度搜索出现该后缀的文件，就视为需要归置
EXE_EXTENSION = ".exe"

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def contains_exe(unit: Path) -> bool:
    """深度搜索 unit 下是否存在 .exe 文件（不区分大小写）"""
    for _, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(EXE_EXTENSION):
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
        EXE_DIR.mkdir(parents=True, exist_ok=True)

    # 排除目标目录本身，防止误扫、误移
    exe_dir_resolved = EXE_DIR.resolve()

    units = sorted(
        (p for p in SOURCE_DIR.iterdir()
         if p.is_dir() and p.resolve() != exe_dir_resolved),
        key=lambda p: p.name.lower(),
    )
    total = len(units)
    print(f"共发现 {total} 个素材单位。\n")

    moved_count = 0
    skipped_count = 0

    for i, unit in enumerate(units, 1):
        try:
            is_exe = contains_exe(unit)
        except Exception as e:
            print(f"[{i}/{total}] [扫描失败] {unit.name} -> {e}")
            skipped_count += 1
            continue

        if not is_exe:
            skipped_count += 1
            print(f"[{i}/{total}] [无 exe] 保持不动：{unit.name}")
            continue

        dest = unique_dest(EXE_DIR, unit.name)

        if DRY_RUN:
            print(f"[{i}/{total}] [含 exe] {unit}")
            print(f"                     ->  {dest}   （预览模式，未移动）")
            moved_count += 1
            continue

        try:
            shutil.move(str(unit), str(dest))
            print(f"[{i}/{total}] [含 exe] 已移动：{unit.name}  ->  {dest}")
            moved_count += 1
        except Exception as e:
            print(f"[{i}/{total}] [含 exe] 移动失败：{unit.name} -> {e}")
            skipped_count += 1

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  移入 exe 目录 : {moved_count}")
    print(f"  跳过（无 exe/失败） : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()