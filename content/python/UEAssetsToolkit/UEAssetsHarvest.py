"""
从 D:\agw\300 剩余的素材单位中，剥离外层嵌套，收割真正的内容根文件夹。

流程：
1. 以 D:\agw\300 下每个一级子文件夹为一个素材单位。
2. 素材单位当前层必须“有且仅有一个子文件夹”，否则跳过。
3. 从这个唯一子文件夹开始，沿单链一直向下深入，
   直到某一层的子文件夹数量不等于 1（0 个或多个）。
4. 若该层有多个子文件夹，且其中任意一个的名字（不区分大小写）
   在 TARGET_NAMES 中，则将该层文件夹整体移动到 DEST_DIR。
5. 移动成功后，把整个素材单位移入回收站。
"""

import sys
import shutil
from pathlib import Path

try:
    from send2trash import send2trash
except ImportError:
    print("缺少 send2trash 库，请先运行：pip install send2trash")
    sys.exit(1)

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\660p\动画\dir")            # 素材根目录
DEST_DIR   = Path(r"D:\660p\动画\clear")    # 内容根文件夹移动目标
TARGET_NAMES = {
    "maps", "blueprint", "material", "mesh", "tex", "fx",
    "levels", "materials", "level", "meshes", "textures",
    "animations", "demo", "props","art","map","character",
    "vfx","demomaps","audio","sfx","demomap","runtime",
    "shaders","scene","nature","ai","bp","shared","umg",
    "blueprints","mannequin","common","scenes","resource",
    "mechmaterials"
}   
DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def subfolders(p: Path):
    """返回 p 下的所有子文件夹（只算目录，不算文件）"""
    try:
        return [d for d in p.iterdir() if d.is_dir()]
    except Exception:
        return []


def find_root_folder(unit: Path):
    """
    从素材单位出发，沿单链下钻，返回 (root_folder, matched)：
      root_folder: 找到的那一层文件夹；未找到返回 None
      matched:     该层是否包含 TARGET_NAMES 中的名字
    规则：
      - 当前层子文件夹数量为 1 -> 进入该子文件夹，继续
      - 当前层子文件夹数量 > 1 -> 停止，检查是否匹配
      - 当前层子文件夹数量 = 0 -> 返回 None（死路）
    """
    current = unit
    while True:
        subs = subfolders(current)
        if len(subs) == 1:
            current = subs[0]
            continue
        if len(subs) > 1:
            names_lower = {d.name.lower() for d in subs}
            return current, bool(names_lower & TARGET_NAMES)
        return None, False


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
        DEST_DIR.mkdir(parents=True, exist_ok=True)

    units = sorted(
        (p for p in SOURCE_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    print(f"共发现 {len(units)} 个素材单位。\n")

    moved_count = 0
    trashed_count = 0

    for unit in units:
        print(f"素材单位：{unit.name}")

        # 前提：素材单位当前层有且仅有一个子文件夹
        subs = subfolders(unit)
        if len(subs) != 1:
            print(f"  当前层子文件夹数量 = {len(subs)}，不满足“有且仅有一个”，跳过。\n")
            continue

        root, matched = find_root_folder(unit)

        if root is None:
            print("  下钻后到达空文件夹（只有文件），跳过。\n")
            continue

        if not matched:
            print(f"  找到内容层 {root}，但其中没有匹配的目标名，跳过。\n")
            continue

        print(f"  命中内容层：{root}")
        dest = unique_dest(DEST_DIR, root.name)

        if DRY_RUN:
            print(f"  [预览] 将移动：{root}")
            print(f"        ->  {dest}")
            print(f"  [预览] 将把素材单位移入回收站：{unit}\n")
            moved_count += 1
            trashed_count += 1
            continue

        # 第一步：移动内容根文件夹
        try:
            shutil.move(str(root), str(dest))
            print(f"  已移动：{root}  ->  {dest}")
            moved_count += 1
        except Exception as e:
            print(f"  移动失败：{e}，跳过该素材单位（不删除）。\n")
            continue

        # 第二步：移动成功后才把素材单位移入回收站
        try:
            send2trash(str(unit))
            print(f"  已将素材单位移入回收站：{unit}\n")
            trashed_count += 1
        except Exception as e:
            print(f"  移入回收站失败：{e}\n")

    print("-" * 60)
    print(f"完成。成功收割内容层：{moved_count} 个；"
          f"移入回收站素材单位：{trashed_count} 个。")


if __name__ == "__main__":
    main()