"""
处理 D:\agw\300 下的素材文件夹：
1. 深度搜索每个素材单位中名为 Content 的文件夹；
2. 在 Content 中排除 __ExternalActors__、__ExternalObjects__、Collections、Developers；
3. 若剩余子文件夹数量恰好为 1，则将其移动到 D:\agw\t58\Content\；
4. 只要该素材单位中有任何文件夹被成功移动，就把整个素材单位移入回收站。
"""

import os
import shutil
import sys
from pathlib import Path

# 尝试导入 send2trash，用于安全地移入回收站
try:
    from send2trash import send2trash
except ImportError:
    print("缺少 send2trash 库，请先运行：pip install send2trash")
    sys.exit(1)

# ================= 配置区 =================
SOURCE_DIR = Path(r"D:\agw\300")            # 素材根目录
DEST_CONTENT_DIR = Path(r"D:\agw\t58\Content")  # 提取出的文件夹存放位置
EXCLUDE_DIRS = {
    "__externalactors__",
    "__externalobjects__",
    "collections",
    "developers",
    "Splash",
}  # 排除名单（统一小写比较）
# =========================================


def find_content_folders(root: Path):
    """深度搜索 root 下所有名为 Content 的文件夹（不区分大小写）"""
    content_folders = []
    for dirpath, dirnames, filenames in os.walk(root):
        for d in dirnames:
            if d.lower() == "content":
                content_folders.append(Path(dirpath) / d)
    return content_folders


def get_unique_dest(dest_dir: Path, name: str) -> Path:
    """如果目标已存在，自动添加 _1、_2 等后缀，避免覆盖"""
    dest = dest_dir / name
    if not dest.exists():
        return dest
    i = 1
    while True:
        new_dest = dest_dir / f"{name}_{i}"
        if not new_dest.exists():
            return new_dest
        i += 1


def main():
    if not SOURCE_DIR.is_dir():
        print(f"[错误] 源目录不存在：{SOURCE_DIR}")
        return

    # 确保目标 Content 目录存在
    DEST_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    # 获取所有一级子文件夹作为素材单位
    units = [p for p in SOURCE_DIR.iterdir() if p.is_dir()]
    print(f"共发现 {len(units)} 个素材单位。\n")

    processed_units = 0

    for unit in units:
        print(f"处理素材单位：{unit.name}")
        content_folders = find_content_folders(unit)
        if not content_folders:
            print("  未找到 Content 文件夹，跳过。\n")
            continue

        unit_moved = False  # 标记该素材单位是否有成功移动

        for content in content_folders:
            print(f"  检查 Content 文件夹：{content}")
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
                dest_folder = get_unique_dest(DEST_CONTENT_DIR, src_folder.name)
                try:
                    shutil.move(str(src_folder), str(dest_folder))
                    print(f"    已移动：{src_folder.name} -> {dest_folder}")
                    unit_moved = True
                except Exception as e:
                    print(f"    移动失败：{e}")
            else:
                print(f"    有效子文件夹数量为 {len(valid)}，不符合条件（必须恰好为 1），跳过。")

        # 只要该素材单位中有任何一个文件夹被成功移动，就删除整个素材单位
        if unit_moved:
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