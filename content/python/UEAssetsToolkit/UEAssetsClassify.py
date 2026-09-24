"""
自动分类并移动 Unreal 相关文件夹

规则（递归扫描每个一级子文件夹）：
    - 只要含有 *.uproject  -> 项目工程文件夹 -> 移动到 PROJECT_DIR
    - 否则含有 *.uplugin   -> 插件文件夹     -> 移动到 PLUGIN_DIR
    - 两者都没有           -> 素材文件夹     -> 原地保留，不移动
"""

import os
import shutil
import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR  = Path(r"D:\agw\300")      # 待分类的根目录
PLUGIN_DIR  = Path(r"D:\agw\plugins")  # 插件文件夹移动目标
PROJECT_DIR = Path(r"D:\agw\project")  # 项目工程文件夹移动目标
DRY_RUN     = False                    # True = 只预览不实际移动，建议先设 True 跑一遍
# =========================================


def classify(folder: Path) -> str:
    """递归扫描 folder，返回 'project' / 'plugin' / 'asset'。

    优先级说明：先看 .uproject。因为一个工程内部通常自带 Plugins 子目录，
    里面会有 .uplugin，若先判插件会把整个工程误判成插件。
    """
    has_uproject = False
    has_uplugin = False

    for root, dirs, files in os.walk(folder):
        for name in files:
            low = name.lower()
            if low.endswith(".uproject"):
                has_uproject = True
            elif low.endswith(".uplugin"):
                has_uplugin = True
        # 两个都找到了就不用再往下扫了
        if has_uproject and has_uplugin:
            break

    if has_uproject:
        return "project"
    if has_uplugin:
        return "plugin"
    return "asset"


def unique_dest(dest_dir: Path, name: str) -> Path:
    """目标目录若已存在同名文件夹，自动追加 _1 _2 ... 后缀，避免覆盖"""
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
    # 1. 基础校验
    if not SOURCE_DIR.is_dir():
        print(f"[错误] 源目录不存在：{SOURCE_DIR}")
        sys.exit(1)

    if not DRY_RUN:
        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)

    targets = {PLUGIN_DIR.resolve(), PROJECT_DIR.resolve()}

    # 2. 取出所有一级子文件夹（排除目标目录本身，防止误移）
    folders = sorted(
        (p for p in SOURCE_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    folders = [p for p in folders if p.resolve() not in targets]

    total = len(folders)
    stats = {"plugin": 0, "project": 0, "asset": 0, "failed": 0}

    print(f"共发现 {total} 个待分类文件夹")
    print("-" * 70)

    # 3. 逐个扫描 + 移动
    for i, folder in enumerate(folders, 1):
        try:
            kind = classify(folder)
        except Exception as e:
            stats["failed"] += 1
            print(f"[{i}/{total}] [扫描失败] {folder.name} -> {e}")
            continue

        # 素材：原地不动
        if kind == "asset":
            stats["asset"] += 1
            print(f"[{i}/{total}] [素材] 保持不动：{folder.name}")
            continue

        label    = "插件" if kind == "plugin" else "项目"
        dest_dir = PLUGIN_DIR if kind == "plugin" else PROJECT_DIR

        # 预览模式
        if DRY_RUN:
            dest = unique_dest(dest_dir, folder.name)
            stats[kind] += 1
            print(f"[{i}/{total}] [{label}] {folder}  ==>  {dest}   （预览模式，未移动）")
            continue

        # 实际移动
        try:
            dest = unique_dest(dest_dir, folder.name)
            shutil.move(str(folder), str(dest))
            stats[kind] += 1
            print(f"[{i}/{total}] [{label}] 已移动：{folder.name}  ->  {dest}")
        except Exception as e:
            stats["failed"] += 1
            print(f"[{i}/{total}] [{label}] 移动失败：{folder.name} -> {e}")

    # 4. 汇总
    print("-" * 70)
    print("处理完成，统计如下：")
    print(f"  插件文件夹 : {stats['plugin']}")
    print(f"  项目文件夹 : {stats['project']}")
    print(f"  素材文件夹 : {stats['asset']}  （未移动）")
    print(f"  失败       : {stats['failed']}")


if __name__ == "__main__":
    main()