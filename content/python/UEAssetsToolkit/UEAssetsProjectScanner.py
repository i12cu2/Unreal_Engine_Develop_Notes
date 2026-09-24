r"""
只读扫描 D:\agw\over 下的每个一级子文件夹（素材单位），
深度查找是否存在 .uproject 文件（不区分大小写）。
若存在，则输出该素材单位名字，并列出其中所有命中的 .uproject 文件路径。

本脚本不写入、不修改、不移动、不删除任何文件，仅做遍历和打印。
"""

import os
import sys
from pathlib import Path

# ================= 配置区 =================
SCAN_DIR = Path(r"D:\agw\over")   # 待扫描的根目录
UPROJECT_EXTENSION = ".uproject"  # 判定后缀（不区分大小写）
# =========================================


def find_uprojects(unit: Path):
    """深度查找 unit 下所有 .uproject 文件，返回完整路径列表"""
    results = []
    for dirpath, _, filenames in os.walk(unit):
        for f in filenames:
            if f.lower().endswith(UPROJECT_EXTENSION):
                results.append(Path(dirpath) / f)
    return results


def main():
    if not SCAN_DIR.is_dir():
        print(f"[错误] 目录不存在：{SCAN_DIR}")
        sys.exit(1)

    units = sorted(
        (p for p in SCAN_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name.lower(),
    )
    total = len(units)

    hits = []  # [(单位名, [uproject路径, ...]), ...]
    for unit in units:
        try:
            ups = find_uprojects(unit)
            if ups:
                hits.append((unit.name, ups))
        except Exception as e:
            print(f"[扫描失败] {unit.name} -> {e}")

    print(f"共扫描 {total} 个素材单位，命中 {len(hits)} 个：\n")
    for name, ups in hits:
        print(f"素材单位：{name}")
        for p in ups:
            print(f"    {p}")
        print()


if __name__ == "__main__":
    main()