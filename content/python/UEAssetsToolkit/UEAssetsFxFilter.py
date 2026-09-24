r"""
遍历 D:\660p1.77T\overContent 下的每个单位素材文件夹：

1. 只看单位素材文件夹的“名字”（一级子文件夹名），
   若名字中包含 "fx" 或 "vfx"（不区分大小写），即视为命中。
2. 命中则把整个单位素材文件夹移动到 TARGET_DIR；
   未命中则原地不动。

说明：
- 这里用的是“包含”匹配，不是“完全相等”匹配。
  例如 MyFXPack、VFX_Sparks、xxx_fx 都会命中。
- 移动对象是整个一级子文件夹本身，不拆分内部结构。
- 目标目录已有同名文件夹时，自动追加 _1、_2 后缀，避免覆盖。
"""

import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\660p1.77T\overContent")   # 素材根目录
TARGET_DIR = Path(r"D:\660p1.77T\overContentfx")  # 命中的单位移动目标

# 关键词名单：只要文件夹名字里“包含”其中任意一个（不区分大小写）即命中
KEYWORDS = [
    "fx",
    "vfx",
]

DRY_RUN = False   # 先 True 预览，确认无误后再改为 False 实际执行
# =========================================


def name_matches(name: str, keywords_lower) -> bool:
    """名字里是否包含任意关键词（不区分大小写，包含即可）"""
    low = name.lower()
    return any(k in low for k in keywords_lower)


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

    keywords_lower = [k.lower() for k in KEYWORDS]

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
        if not name_matches(unit.name, keywords_lower):
            skipped_count += 1
            print(f"[{i}/{total}] [未命中] 保持不动：{unit.name}")
            continue

        dest = unique_dest(TARGET_DIR, unit.name)

        if DRY_RUN:
            print(f"[{i}/{total}] [命中] {unit.name}")
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