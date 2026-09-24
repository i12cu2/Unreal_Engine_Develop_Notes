r"""
处理 D:\agw\project_renamed 下的每个项目单位（一级子文件夹）：

1. 深度查找 .uproject 文件；找不到就跳过。
2. 访问该 .uproject 同级的 Content 文件夹。
3. 列出 Content 内的子文件夹，排除 EXCLUDE_DIRS 中的名字。
4. 若剩余子文件夹数量恰好为 1，则将其移动到 TARGET_DIR。
5. 移动成功后，把整个项目单位文件夹移入回收站。

说明：
- 移动失败时不会删除项目单位，避免数据丢失。
- 目标目录重名时自动追加 _1、_2 后缀。
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
SOURCE_DIR = Path(r"D:\agw\project_renamed")    # 项目单位根目录
TARGET_DIR = Path(r"D:\agw\t58\Content")        # 提取出的文件夹存放位置（请按需修改）

UPROJECT_EXTENSION = ".uproject"

EXCLUDE_DIRS = {
    "__externalactors__",
    "__externalobjects__",
    "collections",
    "developers",
    "splash",
    "startercontent",
}   # 排除名单（统一小写比较）

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def find_uproject(unit: Path):
    """深度查找 unit 下第一个 .uproject 文件，返回完整路径；找不到返回 None"""
    for dirpath, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(UPROJECT_EXTENSION):
                return Path(dirpath) / f
    return None


def find_content_folder(uproject: Path):
    """在 .uproject 同级目录下查找名为 Content 的文件夹（不区分大小写）"""
    parent = uproject.parent
    for d in parent.iterdir():
        if d.is_dir() and d.name.lower() == "content":
            return d
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

        # ---------- 步骤 1：找 .uproject ----------
        uproject = find_uproject(unit)
        if uproject is None:
            print("  未找到 .uproject，跳过。\n")
            skipped_count += 1
            continue
        print(f"  找到 .uproject：{uproject}")

        # ---------- 步骤 2：找同级 Content ----------
        content = find_content_folder(uproject)
        if content is None:
            print("  同级未找到 Content 文件夹，跳过。\n")
            skipped_count += 1
            continue
        print(f"  同级 Content：{content}")

        # ---------- 步骤 3：过滤排除名单 ----------
        try:
            subfolders = [d for d in content.iterdir() if d.is_dir()]
        except Exception as e:
            print(f"  无法访问 Content：{e}，跳过。\n")
            skipped_count += 1
            continue

        valid = [d for d in subfolders if d.name.lower() not in EXCLUDE_DIRS]
        print(f"  有效子文件夹（排除后）：{[d.name for d in valid]}")

        if len(valid) != 1:
            print(f"  有效子文件夹数量为 {len(valid)}，不符合条件（必须恰好为 1），跳过。\n")
            skipped_count += 1
            continue

        src_folder = valid[0]
        dest_folder = unique_dest(TARGET_DIR, src_folder.name)
        print(f"  待移动：{src_folder}")
        print(f"  目标：  {dest_folder}")

        # ---------- 步骤 4：移动 ----------
        if DRY_RUN:
            print(f"  [预览] 将移动：{src_folder}  ->  {dest_folder}")
            print(f"  [预览] 将把项目单位移入回收站：{unit}\n")
            moved_count += 1
            trashed_count += 1
            continue

        try:
            shutil.move(str(src_folder), str(dest_folder))
            print(f"  已移动：{src_folder.name}  ->  {dest_folder}")
            moved_count += 1
        except Exception as e:
            print(f"  移动失败：{e}，跳过该单位（不删除）。\n")
            skipped_count += 1
            continue

        # ---------- 步骤 5：删除项目单位 ----------
        try:
            send2trash(str(unit))
            print(f"  已将项目单位移入回收站：{unit.name}\n")
            trashed_count += 1
        except Exception as e:
            print(f"  移入回收站失败：{e}\n")

    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  移动的文件夹 : {moved_count}")
    print(f"  删除的项目单位 : {trashed_count}")
    print(f"  跳过         : {skipped_count}")
    if DRY_RUN:
        print("当前为预览模式，未做任何实际改动。确认后请将 DRY_RUN 改为 False。")


if __name__ == "__main__":
    main()