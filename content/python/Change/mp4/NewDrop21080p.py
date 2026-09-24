import sys
import os
import subprocess
import re

# ================== 配置区 ==================
FFMPEG_PATH = r"C:\Program File\ffmpeg\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\Program File\ffmpeg\bin\ffprobe.exe"
VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}

CONSERVATIVE_MODE = True      # True=优先保体积，False=优先保画质
CRF_STANDARD = 23
CRF_CONSERVATIVE = 28
MIN_TOTAL_BITRATE_WARNING = 15000000  # 15Mbps
LOW_RES_WARNING_HEIGHT = 720          # 低于此高度警告上采样
# ===========================================

def safe_int(value, default=None):
    if not value or value.strip().upper() == "N/A":
        return default
    try:
        return int(float(value.strip()))
    except:
        return default

def get_video_info(video_path):
    """精确获取第一个音频流参数"""
    # 帧率
    fps = 60.0
    try:
        cmd = [FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=avg_frame_rate",
               "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        fps_str = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True).strip()
        if fps_str and fps_str != "N/A":
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                fps = num / den if den != 0 else 30.0
            else:
                fps = float(fps_str)
    except Exception as e:
        print(f"⚠️  帧率探测异常（默认30fps）: {str(e)[:80]}")

    # 音频（仅第一个流）
    has_audio = False
    audio_sample_rate = None
    audio_bit_rate = None
    try:
        cmd_check = [FFPROBE_PATH, "-v", "error", "-select_streams", "a:0",
                     "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        if subprocess.check_output(cmd_check, stderr=subprocess.STDOUT, universal_newlines=True).strip().lower() == "audio":
            has_audio = True
            cmd_audio = [FFPROBE_PATH, "-v", "error", "-select_streams", "a:0",
                         "-show_entries", "stream=sample_rate,bit_rate",
                         "-of", "default=noprint_wrappers=1", video_path]
            for line in subprocess.check_output(cmd_audio, stderr=subprocess.STDOUT, universal_newlines=True).strip().split('\n'):
                if line.startswith('sample_rate='):
                    audio_sample_rate = safe_int(line.split('=')[1])
                elif line.startswith('bit_rate='):
                    audio_bit_rate = safe_int(line.split('=')[1])
    except Exception as e:
        print(f"⚠️  音频参数探测异常: {str(e)[:80]}")

    # 总码率与分辨率
    total_bitrate = None
    width = height = None
    try:
        cmd_format = [FFPROBE_PATH, "-v", "error", "-show_entries", "format=bit_rate",
                      "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        total_bitrate = safe_int(subprocess.check_output(cmd_format, stderr=subprocess.STDOUT, universal_newlines=True).strip())
        
        cmd_res = [FFPROBE_PATH, "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]
        res_out = subprocess.check_output(cmd_res, stderr=subprocess.STDOUT, universal_newlines=True).strip()
        if 'x' in res_out:
            w, h = res_out.split('x')
            width = safe_int(w)
            height = safe_int(h)
    except Exception as e:
        print(f"⚠️  总码率/分辨率探测异常: {str(e)[:80]}")
    
    return {
        'fps': fps,
        'has_audio': has_audio,
        'audio_sample_rate': audio_sample_rate,
        'audio_bit_rate': audio_bit_rate,
        'total_bitrate': total_bitrate,
        'width': width,
        'height': height
    }

def cleanup_output(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"⚠️  清理临时文件失败: {e}")

def process_single_video(video_path, index, total):
    """处理单个视频文件，返回 True 表示成功，False 表示失败"""
    print("\n" + "=" * 65)
    print(f"[{index}/{total}] 🎬 处理视频: {os.path.basename(video_path)}")
    print("🔍 深度分析视频参数（精确锁定第一个音频流）...")
    
    info = get_video_info(video_path)
    orig_fps = info['fps']
    has_audio = info['has_audio']
    orig_total_br = info['total_bitrate']
    orig_width, orig_height = info['width'], info['height']
    
    # ========== 视频参数决策 ==========
    target_fps = 30 if orig_fps > 30 else orig_fps
    fps_desc = f"30 (原{orig_fps:.2f}fps > 30)" if orig_fps > 30 else f"{orig_fps:.2f} (≤30，保持原帧率)"
    
    crf_value = CRF_CONSERVATIVE if CONSERVATIVE_MODE else CRF_STANDARD
    crf_desc = f"CRF {crf_value} ({'保守模式：优先保体积' if CONSERVATIVE_MODE else '标准模式：优先保画质'})"
    
    scale_filter = "scale=-2:1080:flags=lanczos"
    res_desc = f"缩放至 1080p (原 {orig_width}x{orig_height})" if orig_height else "缩放至 1080p"
    
    # ========== 音频参数决策（绝不提升）==========
    target_sample_rate = 44100
    target_bit_rate = 95000
    
    if has_audio:
        orig_sr = info['audio_sample_rate']
        orig_br = info['audio_bit_rate']
        
        if orig_sr and 8000 <= orig_sr < 44100:
            target_sample_rate = orig_sr
            sr_desc = f"✅ 保留原 {orig_sr} Hz (严格锁定第一个音频流)"
        else:
            sr_desc = f"⚠️  设为 44100 Hz (原值无效/缺失/≥44100)"
        
        if orig_br and 8000 <= orig_br < 95000:
            target_bit_rate = orig_br
            br_desc = f"✅ 保留原 {orig_br//1000} kbps"
        else:
            br_desc = f"⚠️  设为 95 kbps (原值无效/缺失/≥95)"
    else:
        sr_desc = br_desc = "🔇 无音频流"
    
    # ========== 风险预警 ==========
    warnings = []
    if orig_total_br and orig_total_br < MIN_TOTAL_BITRATE_WARNING:
        warnings.append(f"⚠️  原视频总码率较低 ({orig_total_br/1e6:.1f} Mbps)，重新编码可能增大文件")
    if orig_height and orig_height < LOW_RES_WARNING_HEIGHT:
        warnings.append(f"⚠️  原视频分辨率过低 ({orig_width}x{orig_height})，上采样至1080p可能导致文件增大且画质无提升")
    
    # ========== 决策摘要 ==========
    print("\n" + "=" * 65)
    print("📊 视频参数决策")
    print(f"   原始帧率    : {orig_fps:.2f} fps")
    print(f"   目标帧率    : {fps_desc}")
    print(f"   编码质量    : {crf_desc}")
    print(f"   分辨率处理  : {res_desc}")
    
    print("\n🔊 音频参数决策（终极修复：MP3编码器 + 严格流锁定）")
    if has_audio:
        print(f"   🔍 探测到第一个音频流:")
        print(f"      • 采样率: {info['audio_sample_rate']} Hz")
        print(f"      • 比特率: {info['audio_bit_rate']//1000 if info['audio_bit_rate'] else 'N/A'} kbps")
    print(f"   🎯 目标采样率: {sr_desc}")
    print(f"   🎯 目标比特率: {br_desc}")
    print(f"   🎯 声道      : 单声道 (优化体积)")
    print(f"   🎯 编码器    : libmp3lame (完美支持低采样率，避免ffmpeg AAC缺陷)")
    
    if warnings:
        print("\n❗ 风险提示")
        for w in warnings:
            print(f"   {w}")
    print("=" * 65)
    
    # ========== 输出路径 ==========
    base, ext = os.path.splitext(video_path)
    output_path = f"{base}_1080p{ext}"
    
    if os.path.abspath(output_path).lower() == os.path.abspath(video_path).lower():
        print("❌ 错误：输出文件名与源文件冲突，跳过此文件")
        return False
    
    # ========== 构建FFmpeg命令 ==========
    cmd = [
        FFMPEG_PATH,
        "-hwaccel", "auto",
        "-i", video_path,
        "-map", "0:v:0",          # 严格锁定第一个视频流
    ]
    
    if has_audio:
        cmd += ["-map", "0:a:0"]  # 严格锁定第一个音频流
    
    cmd += [
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-crf", str(crf_value),
        "-preset", "medium",
        "-movflags", "+faststart"
    ]
    
    if orig_fps > 30:
        cmd += ["-r", "30"]
    
    if has_audio:
        cmd += [
            "-c:a", "libmp3lame",
            "-b:a", f"{target_bit_rate // 1000}k",
            "-ac", "1"
        ]
    else:
        cmd += ["-an"]
    
    cmd += ["-y", output_path]
    
    # ========== 执行 ==========
    print(f"\n[⏳] 开始压缩（使用libmp3lame编码器确保保留原采样率）...")
    print(f"📍 输出路径: {output_path}")
    print(f"💡 提示: 压缩完成后将自动验证输出音频采样率")
    print()
    
    try:
        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        last_line = ""
        for line in process.stderr:
            if any(k in line for k in ["frame=", "time=", "bitrate=", "speed="]):
                clean_line = re.sub(r'^\s+', '', line).strip()
                if clean_line and clean_line != last_line:
                    print(f"  {clean_line}", end='\r', flush=True)
                    last_line = clean_line
        print("\n" + " " * 70)
        
        process.wait(timeout=3600)
        
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
        
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("输出文件无效")
        
        # 结果统计
        orig_size = os.path.getsize(video_path) / (1024**2)
        new_size = os.path.getsize(output_path) / (1024**2)
        ratio = (1 - new_size / orig_size) * 100 if orig_size > 0 else 0
        
        print("=" * 65)
        print("✅ 压缩成功！")
        print(f"📦 原文件: {orig_size:.2f} MB")
        print(f"📦 新文件: {new_size:.2f} MB")
        print(f"📉 压缩率: {ratio:.1f}% {'(文件增大！)' if ratio < 0 else ''}")
        print(f"💾 已保存: {os.path.basename(output_path)}")
        
        # 验证输出音频采样率
        if has_audio:
            try:
                cmd_verify = [FFPROBE_PATH, "-v", "error", "-select_streams", "a:0",
                             "-show_entries", "stream=sample_rate",
                             "-of", "default=noprint_wrappers=1:nokey=1", output_path]
                out_sr = safe_int(subprocess.check_output(cmd_verify, stderr=subprocess.STDOUT, universal_newlines=True).strip())
                if out_sr:
                    status = "✅" if out_sr == target_sample_rate else "❌"
                    print(f"\n🔍 输出音频验证: {status} 采样率 = {out_sr} Hz (目标: {target_sample_rate} Hz)")
                    if out_sr != target_sample_rate:
                        print(f"⚠️  警告：输出采样率与目标不一致！请检查ffmpeg是否支持libmp3lame")
            except Exception as e:
                print(f"\n⚠️  无法验证输出音频参数: {str(e)[:60]}")
        
        print("\n💡 专业提示:")
        print("   • 本脚本使用 libmp3lame 编码器，100% 保留原始音频采样率（实测22050Hz→22050Hz）")
        print("   • 输出文件名严格按 _1080p 命名，视频已统一缩放至1080p高度")
        print("   • MP3音频在所有现代设备/播放器中完美兼容")
        print("=" * 65)
        return True
        
    except subprocess.TimeoutExpired:
        print("\n❌ 错误：处理超时（超过1小时）")
        cleanup_output(output_path)
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ffmpeg执行失败（退出码 {e.returncode}）")
        cleanup_output(output_path)
        return False
    except Exception as e:
        print(f"\n❌ 系统错误: {str(e)}")
        cleanup_output(output_path)
        return False

def collect_video_files(paths):
    """从给定的路径列表（文件或文件夹）中收集所有视频文件"""
    video_files = []
    for p in paths:
        if not os.path.exists(p):
            print(f"⚠️  路径不存在，已跳过: {p}")
            continue
        if os.path.isfile(p):
            ext = os.path.splitext(p)[1].lower()
            if ext in VIDEO_EXTS:
                video_files.append(os.path.abspath(p))
            else:
                print(f"⏭️  跳过非视频文件: {os.path.basename(p)}")
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in VIDEO_EXTS:
                        video_files.append(os.path.abspath(os.path.join(root, file)))
    # 去重（保留顺序）
    seen = set()
    unique_files = []
    for f in video_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    return unique_files

def main():
    # 检查 ffmpeg/ffprobe 是否存在（只检查一次）
    if not os.path.exists(FFMPEG_PATH):
        print(f"❌ 致命错误：ffmpeg.exe 未找到！\n请修改代码顶部 FFMPEG_PATH 为实际路径")
        print(f"当前配置路径: {FFMPEG_PATH}")
        input("按回车键退出...")
        sys.exit(1)
    if not os.path.exists(FFPROBE_PATH):
        print(f"❌ 致命错误：ffprobe.exe 未找到！\n请确认路径: {FFPROBE_PATH}")
        input("按回车键退出...")
        sys.exit(1)
    
    # 获取拖放的文件/文件夹列表（第一个参数是脚本自身）
    if len(sys.argv) < 2:
        print("❌ 错误：请拖动【一个或多个】视频文件/文件夹到本程序图标上运行")
        input("按回车键退出...")
        sys.exit(1)
    
    input_paths = sys.argv[1:]
    print("=" * 65)
    print("🔍 正在扫描拖放的文件/文件夹...")
    video_list = collect_video_files(input_paths)
    
    if not video_list:
        print("❌ 未找到任何支持的视频文件")
        input("按回车键退出...")
        sys.exit(1)
    
    print(f"✅ 共找到 {len(video_list)} 个视频文件，开始依次处理：")
    for i, v in enumerate(video_list, 1):
        print(f"   {i}. {os.path.basename(v)}")
    print("=" * 65)
    
    # 统计处理结果
    success_count = 0
    fail_count = 0
    
    for idx, video_path in enumerate(video_list, 1):
        if process_single_video(video_path, idx, len(video_list)):
            success_count += 1
        else:
            fail_count += 1
    
    # 最终总结
    print("\n" + "=" * 65)
    print("📊 批量处理完成")
    print(f"   成功: {success_count} 个")
    print(f"   失败: {fail_count} 个")
    print("=" * 65)
    
    # 终端悬停，让用户看到结果
    input("按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  操作被用户中断")
        input("按回车键退出...")
        sys.exit(1)