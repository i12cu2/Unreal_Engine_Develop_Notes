import subprocess
import sys
import importlib
import platform
import re

# ============================================================
# 第一部分：自动检测并安装依赖 (psutil)
# ============================================================
def install_and_import(package):
    try:
        return importlib.import_module(package)
    except ImportError:
        print(f"⚠️ 未找到 {package}，正在尝试自动安装...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )
            print(f"✅ {package} 安装成功，重新导入...")
            return importlib.import_module(package)
        except subprocess.CalledProcessError:
            print(f"❌ 自动安装 {package} 失败，请手动执行: pip install {package}")
            sys.exit(1)

psutil = install_and_import("psutil")

# ============================================================
# 第二部分：获取内存信息（含当前实际频率）
# ============================================================

def get_memory_info_windows():
    """
    Windows 系统：获取标称频率和当前运行频率，自动判断是否跑满
    """
    try:
        # 使用 Get-CimInstance 获取 DeviceLocator, Speed(标称), ConfiguredClockSpeed(当前)
        cmd = [
            'powershell', '-Command',
            'Get-CimInstance -ClassName Win32_PhysicalMemory | ForEach-Object { $_.DeviceLocator + "|" + $_.Speed + "|" + $_.ConfiguredClockSpeed }'
        ]
        output = subprocess.check_output(cmd, shell=False, encoding='utf-8', stderr=subprocess.STDOUT)
        lines = output.strip().split('\n')
        
        print("\n--- 各内存插槽频率详情 ---")
        all_slots = []
        for line in lines:
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 3:
                    slot, speed_str, conf_str = parts
                    speed = speed_str.strip()
                    conf = conf_str.strip()
                    # 转换为整数，便于比较
                    try:
                        speed_val = int(speed) if speed else 0
                        conf_val = int(conf) if conf else 0
                    except ValueError:
                        speed_val = conf_val = 0
                    
                    # 显示信息
                    slot_info = {
                        'slot': slot,
                        'speed': speed_val,
                        'conf': conf_val
                    }
                    all_slots.append(slot_info)
                    
                    if speed_val > 0 and conf_val > 0:
                        if conf_val < speed_val:
                            status = "⚠️ 未跑满 (当前低于标称)"
                        elif conf_val == speed_val:
                            status = "✅ 已跑满"
                        else:
                            status = "🔺 超频运行 (当前高于标称)"
                        print(f"  🔹 插槽 {slot}: 标称 {speed_val} MT/s | 当前 {conf_val} MT/s → {status}")
                    elif speed_val > 0 and conf_val == 0:
                        print(f"  🔹 插槽 {slot}: 标称 {speed_val} MT/s | 当前频率未知 (无法获取)")
                    else:
                        print(f"  ⚠️ 插槽 {slot}: 数据读取异常")
        
        # 分析所有插槽，给出总体结论
        if all_slots:
            # 过滤出有效数据
            valid = [s for s in all_slots if s['speed'] > 0 and s['conf'] > 0]
            if valid:
                # 检查是否有任何一条未跑满
                has_underclock = any(s['conf'] < s['speed'] for s in valid)
                if has_underclock:
                    print("\n" + "="*50)
                    print("⚠️ 检测到至少一条内存运行频率低于标称值，即【内存没有跑满】。")
                    print("建议：重启进入 BIOS，开启 XMP (Intel) 或 EXPO (AMD) 以恢复标称速度。")
                    print("="*50)
                else:
                    # 检查是否所有都跑满或超频
                    all_full = all(s['conf'] >= s['speed'] for s in valid)
                    if all_full:
                        print("\n" + "="*50)
                        print("✅ 所有内存均以标称或以上频率运行，已跑满，无需调整。")
                        print("="*50)
            else:
                # 无有效 conf 数据，无法自动判断
                print("\n" + "="*50)
                print("❌ 未能获取当前运行频率，无法自动判断。")
                print("请手动打开任务管理器查看【性能】->【内存】->【速度】并对比标称值。")
                print("="*50)
        else:
            print("❌ 未读取到任何内存信息。")

    except subprocess.CalledProcessError as e:
        print(f"❌ 执行 PowerShell 命令失败: {e}")
    except Exception as e:
        print(f"❌ 获取内存信息时发生错误: {e}")

def get_memory_info_linux():
    """Linux：尝试读取 dmidecode，但当前运行频率较难获取，给出手动提示"""
    try:
        output = subprocess.check_output(
            ['sudo', 'dmidecode', '-t', 'memory'],
            stderr=subprocess.DEVNULL,
            text=True
        )
        speeds = re.findall(r'\tSpeed: (\d+) MT/s', output)
        conf_speeds = re.findall(r'\tConfigured Memory Speed: (\d+) MT/s', output)
        if speeds:
            print("\n--- 各内存插槽信息 ---")
            for i, s in enumerate(speeds):
                conf = conf_speeds[i] if i < len(conf_speeds) else "未知"
                print(f"  插槽 {i+1}: 标称 {s} MT/s | 配置 {conf} MT/s")
            print("\n💡 Linux 下建议手动执行 `sudo dmidecode -t memory` 查看详细频率。")
        else:
            print("❌ 未获取到频率信息。")
    except Exception as e:
        print(f"❌ Linux 下获取失败: {e}")

def get_memory_info_macos():
    """macOS：显示频率，但自动判断较难，给出提示"""
    try:
        output = subprocess.check_output(['system_profiler', 'SPMemoryDataType'], text=True)
        for line in output.split('\n'):
            if 'Speed:' in line:
                print(f"  {line.strip()}")
        print("\n💡 macOS 上请对比系统报告中的频率数值。")
    except Exception as e:
        print(f"❌ macOS 获取失败: {e}")

# ============================================================
# 第三部分：主程序
# ============================================================

def main():
    print("=" * 50)
    print("            💻 内存频率自动诊断工具")
    print("=" * 50)
    
    # 系统总内存容量
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024**3)
    print(f"\n📊 总内存: {total_gb:.2f} GB")
    
    system = platform.system()
    if system == "Windows":
        get_memory_info_windows()
    elif system == "Linux":
        get_memory_info_linux()
    elif system == "Darwin":
        get_memory_info_macos()
    else:
        print(f"❌ 不支持的系统: {system}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。")
    except Exception as e:
        print(f"未知错误: {e}")
        sys.exit(1)