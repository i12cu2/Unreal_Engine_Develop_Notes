r"""

遍历 D:\agw\300 下的每个素材单位（一级子文件夹），
深度搜索是否存在 .unitypackage 文件（不区分大小写）。
若存在，则把整个素材单位文件夹移动到 D:\agw\unity。

说明：
- 只移动一级子文件夹本身，不递归拆分内部结构。
- 目标目录已存在同名文件夹时，自动追加 _1、_2 后缀，避免覆盖。
"""

import os
import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\agw\游戏源码")     # 素材根目录
UNITY_DIR  = Path(r"D:\agw\unity")   # Unity 项目归置目录

# 判定后缀：只要素材单位内深度搜索出现该后缀的文件，就归为 Unity 项目
UNITY_EXTENSION = ".unitypackage"

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def contains_unity_package(unit: Path) -> bool:
    """深度搜索 unit 下是否存在 .unitypackage 文件（不区分大小写）"""
    for _, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(UNITY_EXTENSION):
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
        UNITY_DIR.mkdir(parents=True, exist_ok=True)

    # 把目标目录本身排除在外，防止误扫、误移
    unity_dir_resolved = UNITY_DIR.resolve()

    units = sorted(
        (p for p in SOURCE_DIR.iterdir()
         if p.is_dir() and p.resolve() != unity_dir_resolved),
        key=lambda p: p.name.lower(),
    )
    print(f"共发现 {len(units)} 个素材单位。\n")

    moved_count = 0
    skipped_count = 0

    for i, unit in enumerate(units, 1):
        try:
            is_unity = contains_unity_package(unit)
        except Exception as e:
            print(f"[{i}/{len(units)}] [扫描失败] {unit.name} -> {e}")
            skipped_count += 1
            continue

        if not is_unity:
            skipped_count += 1
            print(f"[{i}/{len(units)}] [非 Unity] 保持不动：{unit.name}")
            continue

        dest = unique_dest(UNITY_DIR, unit.name)

        if DRY_RUN:
            print(f"[{i}/{len(units)}] [Unity]   {unit}")
            print(f"                       ->  {dest}   （预览模式，未移动）")
            moved_count += 1
            continue

        try:
            shutil.move(str(unit), str(dest))
            print(f"[{i}/{len(units)}] [Unity]   已移动：{unit.name}  ->  {dest}")
            moved_count += 1
        except Exception as e:
            print(f"[{i}/{len(units)}] [Unity]   移动失败：{unit.name} -> {e}")
            skipped_count += 1

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  移入 Unity 目录 : {moved_count}")
    print(f"  跳过（非 Unity/失败） : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()