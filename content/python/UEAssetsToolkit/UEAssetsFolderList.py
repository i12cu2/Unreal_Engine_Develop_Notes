r"""
读取 SOURCE_DIR 下所有一级子文件夹的名字，逐行写入 OUTPUT_FILE。
仅读取目录结构，不改动源目录下的任何文件或文件夹。

说明：
- 只统计直接子目录，不含文件。
- 输出文件若已存在会被覆盖（先写临时文件再替换，避免中途失败留下半成品）。
"""

import sys
from pathlib import Path

# ================= 配置区 =================
SOURCE_DIR = Path(r"C:\Users\Admin\Desktop\Brushify")            # 源目录
OUTPUT_FILE = Path(r"C:\Users\Admin\Desktop\Brushify\folds.txt") # 输出文件路径
# =========================================


def main():
    if not SOURCE_DIR.is_dir():
        print(f"[错误] 源目录不存在或不是目录：{SOURCE_DIR}")
        sys.exit(1)

    try:
        folders = sorted(
            (p.name for p in SOURCE_DIR.iterdir() if p.is_dir()),
            key=str.lower,
        )
    except PermissionError:
        print(f"[错误] 没有权限读取目录：{SOURCE_DIR}")
        sys.exit(1)

    if not folders:
        print("警告：源目录下没有找到任何文件夹。")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    try:
        with temp_file.open("w", encoding="utf-8") as f:
            for name in folders:
                f.write(name + "\n")
        print(f"成功写入 {len(folders)} 个文件夹名到临时文件：{temp_file}")
    except Exception as e:
        print(f"[错误] 写入失败：{e}")
        if temp_file.exists():
            temp_file.unlink()
        sys.exit(1)

    try:
        temp_file.replace(OUTPUT_FILE)
        print(f"文件已写入：{OUTPUT_FILE}")
    except Exception as e:
        print(f"[错误] 替换目标文件失败：{e}")
        if temp_file.exists():
            temp_file.unlink()
        sys.exit(1)


if __name__ == "__main__":
    main()