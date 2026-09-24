r"""
处理 D:\agw\project 下的每个项目单位（一级子文件夹）：

1. 深度查找 .uproject 文件，取其父文件夹。
2. 将该父文件夹重命名为 .uproject 的前缀（去掉扩展名）。
3. 重命名后移动到 TARGET_DIR（重名自动加 _1、_2）。
4. 移动成功后，把原项目单位文件夹移入回收站。

注意：
- 若 .uproject 的父文件夹恰好就是项目单位本身，
  则移动后单位已不存在，跳过删除步骤。
- 若某单位找不到 .uproject，跳过不动。
- 若找到多个 .uproject，取第一个找到的（深度优先顺序）。
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
SOURCE_DIR = Path(r"D:\agw\project")            # 项目单位根目录
TARGET_DIR = Path(r"D:\agw\project_renamed")    # 重命名后的工程存放位置（请按需修改）
DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def find_uproject(unit: Path):
    """深度查找 unit 下第一个 .uproject 文件，返回完整路径；找不到返回 None"""
    for dirpath, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(".uproject"):
                return Path(dirpath) / f
    return None


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

    units = sorted(
        (p for p in SOURCE_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    total = len(units)
    print(f"共发现 {total} 个项目单位。\n")

    moved_count = 0
    trashed_count = 0
    skipped_count = 0

    for i, unit in enumerate(units, 1):
        print(f"[{i}/{total}] 项目单位：{unit.name}")

        uproject = find_uproject(unit)
        if uproject is None:
            print("  未找到 .uproject，跳过。\n")
            skipped_count += 1
            continue

        parent = uproject.parent
        new_name = uproject.stem  # 去掉 .uproject 后的文件名

        print(f"  找到 .uproject：{uproject}")
        print(f"  父文件夹：       {parent}")
        print(f"  目标名：         {new_name}")

        # ---------- 步骤 1：重命名父文件夹 ----------
        if parent != unit and parent.name != new_name:
            if DRY_RUN:
                print(f"  [预览] 重命名：{parent.name}  ->  {new_name}")
            else:
                new_parent = parent.with_name(new_name)
                if new_parent.exists():
                    print(f"  重命名目标已存在：{new_parent}，跳过。\n")
                    skipped_count += 1
                    continue
                try:
                    parent.rename(new_parent)
                    parent = new_parent
                    print(f"  已重命名：{parent.name}")
                except Exception as e:
                    print(f"  重命名失败：{e}，跳过。\n")
                    skipped_count += 1
                    continue

        # ---------- 步骤 2：移动到目标目录 ----------
        dest = unique_dest(TARGET_DIR, parent.name)
        print(f"  移动目标：{dest}")

        if DRY_RUN:
            print(f"  [预览] 移动：{parent}")
            print(f"        ->    {dest}")
            if parent != unit:
                print(f"  [预览] 移入回收站：{unit}")
            print()
            moved_count += 1
            if parent != unit:
                trashed_count += 1
            continue

        try:
            shutil.move(str(parent), str(dest))
            print(f"  已移动：{parent}  ->  {dest}")
            moved_count += 1
        except Exception as e:
            print(f"  移动失败：{e}，跳过该单位（不删除）。\n")
            skipped_count += 1
            continue

        # ---------- 步骤 3：删除原项目单位 ----------
        if not unit.exists():
            print("  项目单位已随内容一并移走，无需删除。\n")
            continue

        try:
            send2trash(str(unit))
            print(f"  已将项目单位移入回收站：{unit.name}\n")
            trashed_count += 1
        except Exception as e:
            print(f"  移入回收站失败：{e}\n")

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  移动工程文件夹 : {moved_count}")
    print(f"  删除项目单位   : {trashed_count}")
    print(f"  跳过           : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()