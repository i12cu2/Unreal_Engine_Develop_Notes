@echo off
setlocal enabledelayedexpansion

echo 开始遍历当前目录下的 Git 项目...
echo.

for /d %%i in (*) do (
    if exist "%%i\.git" (
        echo 正在更新项目: %%i
        pushd "%%i"
        git pull
        popd
        echo.
    ) else (
        echo 跳过非 Git 项目: %%i
    )
)

echo 所有 Git 项目已更新完毕。
pause