"""
Git仓库批量更新工具
功能：自动检测并更新指定路径下的所有Git仓库
特点：多线程、冲突处理、断点继续、详细日志、支持自定义路径（变量形式）
"""

import os
import sys
import json
import time
import subprocess
import threading
import queue
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse

# ==================== 配置区域 - 直接修改这里的变量 ====================
# 设置要扫描和更新的Git仓库路径
TARGET_PATH = r"D:\0lib" # None 表示使用当前目录，例如: "/home/user/projects" 或 "D:/repos"
MAX_WORKERS = 4     # 最大线程数
MAX_RETRIES = 999   # 最大重试次数
RETRY_DELAY = 5     # 重试间隔（秒）
# ====================================================================

class GitRepoUpdater:
    def __init__(self, target_path=TARGET_PATH, max_workers=MAX_WORKERS, 
                 max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
        """
        初始化更新器
        
        Args:
            target_path (str): 要扫描的目标路径，None表示使用当前目录
            max_workers (int): 最大线程数
            max_retries (int): 最大重试次数
            retry_delay (int): 重试间隔（秒）
        """
        # 获取目标目录
        if target_path:
            self.target_dir = os.path.abspath(target_path)
            if not os.path.exists(self.target_dir):
                raise ValueError(f"指定的路径不存在: {self.target_dir}")
            if not os.path.isdir(self.target_dir):
                raise ValueError(f"指定的路径不是目录: {self.target_dir}")
        else:
            self.target_dir = os.path.abspath(os.getcwd())
        
        # 当前工作目录（用于存放状态文件和日志）
        self.current_dir = os.path.abspath(os.getcwd())
        
        # 配置文件路径（在当前工作目录，与目标路径区分）
        self.status_file = os.path.join(self.current_dir, 'git_update_status.json')
        self.temp_status_file = os.path.join(self.current_dir, 'git_update_status.temp.json')
        self.log_file = os.path.join(self.current_dir, 'git_update_log.txt')
        
        # 配置参数
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 状态数据
        self.status = {
            'completed': {},    # {repo_path: {last_update: timestamp, success: bool, message: str}}
            'failed': {},       # {repo_path: {error: str, retry_count: int, last_attempt: timestamp}}
            'last_run': '',
            'target_path': self.target_dir  # 记录目标路径
        }
        
        # 线程安全队列
        self.result_queue = queue.Queue()
        self.log_lock = threading.Lock()
        
        # 加载状态
        self.load_status()
        
        # 初始化日志
        self.init_log()
    
    def init_log(self):
        """初始化日志文件"""
        header = f"""
{'='*80}
Git仓库批量更新工具 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标扫描路径: {self.target_dir}
当前工作目录: {self.current_dir}
最大线程数: {self.max_workers}
最大重试次数: {self.max_retries}
{'='*80}
"""
        self.log_message(header, log_to_file=False)
    
    def load_status(self):
        """加载更新状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    loaded_status = json.load(f)
                    self.status['completed'] = loaded_status.get('completed', {})
                    self.status['failed'] = loaded_status.get('failed', {})
                    self.status['last_run'] = loaded_status.get('last_run', '')
                    
                    # 检查目标路径是否改变
                    saved_target_path = loaded_status.get('target_path', '')
                    if saved_target_path and saved_target_path != self.target_dir:
                        self.log_message(f"⚠️  目标路径已改变: {saved_target_path} -> {self.target_dir}", level='WARNING')
                        # 路径改变时清空状态，避免混淆
                        if not any(k.startswith(self.target_dir) for k in self.status['completed'].keys()):
                            self.status['completed'] = {}
                            self.status['failed'] = {}
                            self.log_message("🔄 目标路径改变，已清空历史状态", level='WARNING')
                
                completed_count = len(self.status['completed'])
                self.log_message(f"✅ 已加载状态文件，记录了 {completed_count} 个已完成仓库")
        except Exception as e:
            self.log_message(f"⚠️  加载状态文件失败: {e}，将创建新状态文件")
    
    def save_status_atomic(self):
        """原子性保存状态文件"""
        try:
            self.status['last_run'] = datetime.now().isoformat()
            self.status['target_path'] = self.target_dir
            
            # 先写入临时文件
            with open(self.temp_status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2, ensure_ascii=False)
            
            # 原子性替换
            if os.path.exists(self.status_file):
                os.remove(self.status_file)
            os.rename(self.temp_status_file, self.status_file)
            
            self.log_message(f"💾 状态文件已更新 (时间: {self.status['last_run']})")
        except Exception as e:
            self.log_message(f"❌ 保存状态文件失败: {e}")
            try:
                if os.path.exists(self.temp_status_file):
                    os.remove(self.temp_status_file)
            except:
                pass
    
    def log_message(self, message, log_to_file=True, level='INFO'):
        """线程安全的日志记录"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # 控制台输出
        if level == 'ERROR':
            print(f"\033[91m{log_entry}\033[0m")  # 红色
        elif level == 'WARNING':
            print(f"\033[93m{log_entry}\033[0m")  # 黄色
        elif level == 'SUCCESS':
            print(f"\033[92m{log_entry}\033[0m")  # 绿色
        else:
            print(log_entry)
        
        # 文件记录
        if log_to_file:
            with self.log_lock:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        f.write(log_entry + '\n')
                except Exception as e:
                    print(f"写入日志文件失败: {e}")
    
    def find_git_repos(self):
        """查找目标路径下的所有Git仓库"""
        git_repos = []
        
        self.log_message(f"🔍 开始搜索Git仓库 (目录: {self.target_dir})")
        
        try:
            for root, dirs, files in os.walk(self.target_dir):
                # 跳过.git目录本身
                if '.git' in dirs:
                    # 使用相对路径（相对于目标目录）
                    repo_path = os.path.relpath(root, self.target_dir)
                    git_repos.append(repo_path)
                    self.log_message(f"📁 发现Git仓库: {repo_path}")
                    # 跳过子目录，避免重复
                    dirs[:] = []
        
            self.log_message(f"✅ 找到 {len(git_repos)} 个Git仓库")
            return git_repos
        except Exception as e:
            self.log_message(f"❌ 搜索Git仓库失败: {e}", level='ERROR')
            return []
    
    def is_network_available(self):
        """检查网络连接"""
        try:
            import socket
            socket.gethostbyname('github.com')
            return True
        except:
            return False
    
    def get_default_branch(self, repo_path):
        """获取仓库的默认分支"""
        try:
            result = subprocess.run(
                ['git', '-C', repo_path, 'symbolic-ref', '--short', 'HEAD'],
                capture_output=True, text=True, timeout=10
            )
            branch = result.stdout.strip()
            if branch:
                return branch
        except:
            pass
        
        # 尝试检测远程分支
        try:
            result = subprocess.run(
                ['git', '-C', repo_path, 'remote', 'show', 'origin'],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.lower()
            if 'head branch: main' in output or 'default branch: main' in output:
                return 'main'
            elif 'head branch: master' in output or 'default branch: master' in output:
                return 'master'
        except:
            pass
        
        return 'main'  # 默认使用main
    
    def update_repo(self, repo_path, max_retries=None):
        """
        更新单个仓库
        
        Args:
            repo_path (str): 仓库相对路径（相对于目标目录）
            max_retries (int): 重试次数，None表示使用类默认值
        
        Returns:
            dict: 更新结果
        """
        if max_retries is None:
            max_retries = self.max_retries
        
        # 完整路径（基于目标目录）
        full_path = os.path.join(self.target_dir, repo_path)
        repo_name = os.path.basename(repo_path)
        
        # 检查是否已完成（使用完整路径作为key）
        repo_key = os.path.normpath(full_path)
        if repo_key in self.status['completed']:
            last_update = self.status['completed'][repo_key]['last_update']
            self.log_message(f"⏭️  跳过已更新仓库: {repo_name} (上次更新: {last_update})", level='INFO')
            return {
                'repo_path': repo_path,
                'success': True,
                'skipped': True,
                'message': f'已跳过，上次更新时间: {last_update}'
            }
        
        # 检查失败记录
        if repo_key in self.status['failed']:
            fail_info = self.status['failed'][repo_key]
            if fail_info.get('retry_count', 0) >= max_retries:
                self.log_message(f"⏭️  跳过达到最大重试次数的仓库: {repo_name}", level='WARNING')
                return {
                    'repo_path': repo_path,
                    'success': False,
                    'skipped': True,
                    'message': f'达到最大重试次数 ({max_retries})'
                }
        
        # 检查网络
        if not self.is_network_available():
            self.log_message(f"🌐 仓库 {repo_name} 网络不可用，等待 {self.retry_delay} 秒重试...", level='WARNING')
            time.sleep(self.retry_delay)
            if not self.is_network_available():
                self.log_message(f"❌ 仓库 {repo_name} 网络仍然不可用，跳过更新", level='ERROR')
                return {
                    'repo_path': repo_path,
                    'success': False,
                    'error': 'network_unavailable',
                    'message': '网络不可用'
                }
        
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    self.log_message(f"🔄 仓库 {repo_name} 重试 #{retry_count}/{max_retries}", level='WARNING')
                    time.sleep(self.retry_delay)
                
                # 获取当前分支
                current_branch = self.get_default_branch(full_path)
                self.log_message(f"📋 仓库 {repo_name} 当前分支: {current_branch}", level='INFO')
                
                # 执行git pull命令，使用--autostash处理本地更改
                cmd = [
                    'git', '-C', full_path,
                    'pull', '--autostash', '--rebase',
                    'origin', current_branch
                ]
                
                self.log_message(f"⬇️  正在更新仓库: {repo_name}", level='INFO')
                
                start_time = time.time()
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5分钟超时
                )
                end_time = time.time()
                
                execution_time = end_time - start_time
                
                if result.returncode == 0:
                    # 检查是否有更新
                    output = result.stdout.lower()
                    if 'already up to date' in output or '已经是最新的' in output:
                        status = 'already_up_to_date'
                        message = '仓库已是最新'
                    else:
                        status = 'success'
                        message = f'更新成功 (耗时: {execution_time:.1f}秒)'
                    
                    self.log_message(f"✅ {message}: {repo_name}", level='SUCCESS')
                    
                    # 更新状态（使用完整路径作为key）
                    if repo_key in self.status['failed']:
                        del self.status['failed'][repo_key]
                    
                    self.status['completed'][repo_key] = {
                        'last_update': datetime.now().isoformat(),
                        'status': status,
                        'execution_time': execution_time,
                        'message': message,
                        'repo_name': repo_name
                    }
                    
                    self.save_status_atomic()
                    
                    return {
                        'repo_path': repo_path,
                        'success': True,
                        'status': status,
                        'execution_time': execution_time,
                        'message': message
                    }
                
                else:
                    # 分析错误类型
                    error_output = (result.stderr + result.stdout).strip()
                    error_type = self.analyze_git_error(error_output)
                    
                    self.log_message(f"❌ 仓库 {repo_name} 更新失败 (尝试 {retry_count + 1}/{max_retries + 1})", level='ERROR')
                    self.log_message(f"   错误详情: {error_output[:200]}...", level='ERROR')
                    
                    last_error = {
                        'error': error_output,
                        'error_type': error_type,
                        'retry_count': retry_count
                    }
                    
                    # 不可重试的错误直接返回
                    if not self.should_retry(error_type):
                        self.log_message(f"🚨 仓库 {repo_name} 遇到不可重试错误: {error_type}", level='ERROR')
                        
                        self.status['failed'][repo_key] = {
                            'error': error_output,
                            'error_type': error_type,
                            'retry_count': retry_count,
                            'last_attempt': datetime.now().isoformat(),
                            'final': True,
                            'repo_name': repo_name
                        }
                        
                        self.save_status_atomic()
                        
                        return {
                            'repo_path': repo_path,
                            'success': False,
                            'error': error_output,
                            'error_type': error_type,
                            'final': True,
                            'message': f'不可重试错误: {error_type}'
                        }
            
            except subprocess.TimeoutExpired:
                self.log_message(f"⏱️  仓库 {repo_name} 更新超时 (超过5分钟)", level='ERROR')
                last_error = {'error': 'timeout', 'error_type': 'timeout', 'retry_count': retry_count}
            
            except Exception as e:
                self.log_message(f"💥 仓库 {repo_name} 意外错误: {str(e)}", level='ERROR')
                last_error = {'error': str(e), 'error_type': 'exception', 'retry_count': retry_count}
            
            retry_count += 1
        
        # 达到最大重试次数
        self.log_message(f"❌ 仓库 {repo_name} 达到最大重试次数 ({max_retries})，放弃更新", level='ERROR')
        
        self.status['failed'][repo_key] = {
            'error': last_error['error'],
            'error_type': last_error['error_type'],
            'retry_count': max_retries,
            'last_attempt': datetime.now().isoformat(),
            'final': True,
            'repo_name': repo_name
        }
        
        self.save_status_atomic()
        
        return {
            'repo_path': repo_path,
            'success': False,
            'error': last_error['error'],
            'error_type': last_error['error_type'],
            'final': True,
            'message': f'达到最大重试次数 ({max_retries})'
        }
    
    def analyze_git_error(self, error_output):
        """分析Git错误类型"""
        error_output = error_output.lower()
        
        # 网络相关错误
        if any(keyword in error_output for keyword in [
            'timeout', 'timed out', 'connection refused', 'network is unreachable',
            'couldn\'t connect', 'failed to connect', 'unable to access',
            'rpc failed', 'early eof', 'broken pipe', 'reset by peer', 'ssl'
        ]):
            return 'network_error'
        
        # 权限错误
        if any(keyword in error_output for keyword in [
            'permission denied', 'fatal: could not read', 'authentication failed',
            'username', 'password', 'credentials'
        ]):
            return 'permission_error'
        
        # 仓库不存在或路径错误
        if any(keyword in error_output for keyword in [
            'repository not found', 'does not exist', 'not a git repository',
            'no such file or directory'
        ]):
            return 'repository_error'
        
        # 冲突错误（虽然我们用了--autostash，但还是可能遇到）
        if any(keyword in error_output for keyword in [
            'conflict', 'merge conflict', 'unmerged files',
            'cannot rebase', 'needs merge'
        ]):
            return 'conflict_error'
        
        return 'unknown_error'
    
    def should_retry(self, error_type):
        """判断错误类型是否应该重试"""
        retryable_errors = ['network_error', 'timeout', 'exception']
        return error_type in retryable_errors
    
    def worker(self, repo_queue):
        """工作线程函数"""
        while not repo_queue.empty():
            try:
                repo_path = repo_queue.get_nowait()
                result = self.update_repo(repo_path)
                self.result_queue.put(result)
                repo_queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                self.log_message(f"🚨 工作线程异常: {str(e)}", level='ERROR')
    
    def run_update(self, specific_repos=None):
        """执行批量更新"""
        start_time = time.time()
        
        self.log_message("🚀 开始批量更新Git仓库", level='INFO')
        
        # 查找所有Git仓库
        all_repos = self.find_git_repos()
        
        if not all_repos:
            self.log_message("❌ 没有找到任何Git仓库，程序退出", level='ERROR')
            return
        
        # 过滤特定仓库（如果指定了）
        if specific_repos:
            filtered_repos = []
            for repo in all_repos:
                repo_name = os.path.basename(repo)
                if repo_name in specific_repos or repo in specific_repos:
                    filtered_repos.append(repo)
            all_repos = filtered_repos
            
            self.log_message(f"🎯 仅更新指定的 {len(all_repos)} 个仓库: {', '.join(specific_repos)}", level='INFO')
        
        # 创建任务队列
        repo_queue = queue.Queue()
        for repo in all_repos:
            repo_queue.put(repo)
        
        # 创建线程池
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for _ in range(min(self.max_workers, repo_queue.qsize())):
                future = executor.submit(self.worker, repo_queue)
                futures.append(future)
            
            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    future.result()  # 获取结果，会抛出异常
                except Exception as e:
                    self.log_message(f"🧵 线程执行异常: {str(e)}", level='ERROR')
        
        # 收集结果
        results = []
        while not self.result_queue.empty():
            try:
                results.append(self.result_queue.get_nowait())
            except:
                break
        
        # 生成总结报告
        total = len(all_repos)
        successful = sum(1 for r in results if r.get('success') and not r.get('skipped'))
        skipped = sum(1 for r in results if r.get('skipped'))
        failed = total - successful - skipped
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 保存最终状态
        self.save_status_atomic()
        
        # 打印总结
        summary = f"""
{'='*80}
更新完成总结
{'='*80}
扫描路径: {self.target_dir}
总仓库数: {total}
✅ 成功更新: {successful}
⏭️  已跳过: {skipped} (已更新或达到重试上限)
❌ 失败: {failed}
⏱️  总耗时: {total_time:.1f} 秒
{'='*80}
"""
        
        self.log_message(summary, level='SUCCESS')
        
        # 详细失败报告
        if failed > 0:
            self.log_message("❌ 失败仓库详情:", level='ERROR')
            for result in results:
                if not result.get('success') and not result.get('skipped'):
                    repo_name = os.path.basename(result['repo_path'])
                    error_type = result.get('error_type', 'unknown')
                    message = result.get('message', '未知错误')
                    self.log_message(f"   • {repo_name}: [{error_type}] {message}", level='ERROR')
        
        self.log_message("🎉 批量更新完成！", level='SUCCESS')
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_status_file):
                os.remove(self.temp_status_file)
        except:
            pass

def parse_arguments():
    """解析命令行参数（可选，用于覆盖配置）"""
    parser = argparse.ArgumentParser(description='Git仓库批量更新工具')
    parser.add_argument('--path', '-p', type=str, default=None, 
                       help='覆盖配置中的路径（可选）')
    parser.add_argument('--workers', type=int, default=None, 
                       help='覆盖配置中的线程数（可选）')
    parser.add_argument('--retries', type=int, default=None, 
                       help='覆盖配置中的重试次数（可选）')
    parser.add_argument('--repos', nargs='+', 
                       help='指定要更新的仓库名称（多个用空格分隔）')
    parser.add_argument('--force', action='store_true', 
                       help='强制更新所有仓库（忽略已更新状态）')
    parser.add_argument('--clean', action='store_true', 
                       help='清理状态文件（重新开始）')
    
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    
    # 清理状态文件（如果指定）
    if args.clean:
        status_file = os.path.join(os.getcwd(), 'git_update_status.json')
        if os.path.exists(status_file):
            os.remove(status_file)
            print(f"🧹 已清理状态文件: {status_file}")
    
    try:
        # 使用配置变量，但允许命令行参数覆盖
        target_path = args.path if args.path is not None else TARGET_PATH
        max_workers = args.workers if args.workers is not None else MAX_WORKERS
        max_retries = args.retries if args.retries is not None else MAX_RETRIES
        
        updater = GitRepoUpdater(
            target_path=target_path,
            max_workers=max_workers,
            max_retries=max_retries
        )
        
        # 强制更新所有仓库
        if args.force:
            updater.status['completed'] = {}
            updater.status['failed'] = {}
            updater.log_message("🔄 强制更新模式：将更新所有仓库", level='WARNING')
        
        # 运行更新
        updater.run_update(specific_repos=args.repos)
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断程序执行")
    except Exception as e:
        print(f"💥 程序发生严重错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理
        try:
            updater.cleanup()
        except:
            pass

if __name__ == "__main__":
    main()