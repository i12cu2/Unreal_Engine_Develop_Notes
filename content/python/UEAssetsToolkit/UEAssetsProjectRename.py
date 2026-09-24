r"""
处理 D:\660p\overProject 下的每个一级子文件夹：

1. 深度查找该文件夹下第一个 .uproject 文件，取其文件名前缀（去扩展名）。
2. 用此前缀作为目标文件夹名。
3. 若目标名已被占用，则依次尝试 名字_1、名字_2 …，直到找到空位。
4. 就地重命名该文件夹（不移动位置）。

说明：
- 若某文件夹内找不到 .uproject，跳过不动。
- 若原名与目标名完全一致，也跳过不动（避免无意义操作）。
- 重命名在同级目录内进行，不会改变父目录结构。
"""

import os
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\660p\overProject")   # 待重命名的根目录
UPROJECT_EXTENSION = ".uproject"            # 判定后缀（不区分大小写）
DRY_RUN = False                              # 先 True 预览，确认无误后再改为 False
# =========================================


def find_uproject(unit: Path):
    """深度查找 unit 下第一个 .uproject 文件，返回完整路径；找不到返回 None"""
    for dirpath, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(UPROJECT_EXTENSION):
                return Path(dirpath) / f
    return None


def unique_name(parent: Path, base_name: str, exclude: Path = None) -> str:
    """
    在 parent 目录下为 base_name 找一个不冲突的名字。
    exclude：如果候选名恰为某个已存在路径，但那个路径就是我们自己（即将被重命名掉），
             也允许使用（避免自己挡住自己）。
    """
    candidate = base_name
    i = 1
    while True:
        target = parent / candidate
        if not target.exists() or (exclude is not None and target == exclude):
            return candidate
        candidate = f"{base_name}_{i}"
        i += 1


def main():
    if not SOURCE_DIR.is_dir():
        print(f"[错误] 源目录不存在：{SOURCE_DIR}")
        sys.exit(1)

    units = sorted(
        (p for p in SOURCE_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    total = len(units)
    print(f"共发现 {total} 个文件夹。\n")

    renamed_count = 0
    skipped_count = 0

    for i, unit in enumerate(units, 1):
        uproject = find_uproject(unit)
        if uproject is None:
            print(f"[{i}/{total}] [无 .uproject] 跳过：{unit.name}")
            skipped_count += 1
            continue

        base_name = uproject.stem  # 去掉 .uproject 后的文件名

        # 若原名与目标名相同，跳过
        if unit.name == base_name:
            print(f"[{i}/{total}] [同名] 跳过：{unit.name}")
            skipped_count += 1
            continue

        new_name = unique_name(SOURCE_DIR, base_name, exclude=unit)
        new_path = SOURCE_DIR / new_name

        if DRY_RUN:
            print(f"[{i}/{total}] [预览] {unit.name}  ->  {new_name}")
            renamed_count += 1
            continue

        try:
            unit.rename(new_path)
            print(f"[{i}/{total}] 已重命名：{unit.name}  ->  {new_name}")
            renamed_count += 1
        except Exception as e:
            print(f"[{i}/{total}] 重命名失败：{unit.name} -> {e}")
            skipped_count += 1

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  重命名 : {renamed_count}")
    print(f"  跳过   : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()