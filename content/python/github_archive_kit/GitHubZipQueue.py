"""
GitHub 仓库 ZIP 下载工具（终端交互版）
运行后直接在终端输入 GitHub 链接，支持多个链接排队下载
下载文件命名规则：{owner}_{repo}@{short_sha}.zip
下载目录：程序所在目录
"""

import sys
import os
import time
import queue
import threading
from urllib.parse import urlparse

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("❌ 缺少 requests 库，请执行：pip install requests")
    input("\n按回车键退出...")
    sys.exit(1)


class GitHubZipDownloader:
    PROMPT = "🔗 > "

    def __init__(self):
        # 下载目录 = 程序所在目录（保持与原程序一致）
        self.script_dir = os.path.dirname(os.path.abspath(sys.argv[0] if sys.argv[0] else __file__))

        self.max_retries = 3
        self.retry_delay = 5
        self.download_timeout = 60

        self.branch_cache = {}
        self.github_token = self._get_github_token()

        self.task_queue = queue.Queue()
        self.print_lock = threading.Lock()
        self.stop_event = threading.Event()

    # ---------------- 基础工具 ----------------
    def _get_github_token(self):
        token = os.environ.get('GITHUB_TOKEN', '')
        if token:
            return token
        token_file = os.path.join(self.script_dir, '.github_token')
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r', encoding='utf-8') as f:
                    return f.read().strip() or None
            except Exception:
                pass
        return None

    def log(self, message):
        """线程安全的终端输出，会擦除当前行并重绘提示符"""
        with self.print_lock:
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.write(message + '\n')
            sys.stdout.write(self.PROMPT)
            sys.stdout.flush()

    # ---------------- GitHub API ----------------
    def _get_api_headers(self):
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers

    def extract_repo_info(self, url):
        try:
            url = url.strip().rstrip('/')
            if url.endswith('.git'):
                url = url[:-4]
            parsed = urlparse(url)
            if 'github.com' not in parsed.netloc:
                return None, None
            path = parsed.path.strip('/')
            parts = path.split('/')
            if len(parts) >= 2:
                return parts[0], parts[1].replace('.git', '')
            return None, None
        except Exception:
            return None, None

    def get_default_branch(self, owner, repo):
        cache_key = f"{owner}/{repo}"
        if cache_key in self.branch_cache:
            return self.branch_cache[cache_key]

        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            resp = requests.get(api_url, headers=self._get_api_headers(), timeout=15)
            if resp.status_code == 200:
                branch = resp.json().get('default_branch')
                if branch:
                    self.branch_cache[cache_key] = branch
                    return branch
            elif resp.status_code == 403 and 'X-RateLimit-Remaining' in resp.headers:
                reset_time = int(resp.headers.get('X-RateLimit-Reset', 0))
                wait = max(reset_time - int(time.time()), 0) + 5
                self.log(f"⚠️ GitHub API 速率限制，等待 {wait} 秒")
                time.sleep(wait)
                return self.get_default_branch(owner, repo)
        except Exception as e:
            self.log(f"⚠️ API 获取分支失败: {e}")

        # 回退：直接尝试 main / master
        for candidate in ('main', 'master'):
            test_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{candidate}.zip"
            try:
                resp = requests.head(test_url, allow_redirects=True, timeout=10)
                if resp.status_code == 200:
                    self.branch_cache[cache_key] = candidate
                    return candidate
            except Exception:
                continue

        self.branch_cache[cache_key] = None
        return None

    def get_latest_commit_sha(self, owner, repo, branch):
        api_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
        try:
            resp = requests.get(api_url, headers=self._get_api_headers(), timeout=15)
            if resp.status_code == 200:
                sha = resp.json().get('commit', {}).get('sha')
                if sha:
                    return sha
            elif resp.status_code == 403:
                reset_time = int(resp.headers.get('X-RateLimit-Reset', 0))
                wait = max(reset_time - int(time.time()), 0) + 5
                self.log(f"⚠️ GitHub API 速率限制，等待 {wait} 秒")
                time.sleep(wait)
                return self.get_latest_commit_sha(owner, repo, branch)
            else:
                self.log(f"⚠️ 获取 commit SHA 失败 HTTP {resp.status_code}: {owner}/{repo}")
        except Exception as e:
            self.log(f"⚠️ 获取 commit SHA 异常: {e}")
        return None

    @staticmethod
    def get_zip_url(owner, repo, branch):
        return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    # ---------------- 下载 ----------------
    def download_zip(self, url, dest_path, label):
        try:
            if os.path.exists(dest_path):
                os.remove(dest_path)

            response = requests.get(url, stream=True, timeout=(10, self.download_timeout))
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            last_report = 0.0
            start = time.time()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_report >= 2:
                            if total_size > 0:
                                pct = downloaded * 100.0 / total_size
                                self.log(f"   ⬇️  {label}: {pct:5.1f}% "
                                         f"({downloaded / 1048576:.1f}MB / {total_size / 1048576:.1f}MB)")
                            else:
                                self.log(f"   ⬇️  {label}: {downloaded / 1048576:.1f}MB")
                            last_report = now

            if total_size > 0 and os.path.getsize(dest_path) != total_size:
                raise Exception("下载文件大小与 Content-Length 不匹配")

            elapsed = max(time.time() - start, 0.001)
            self.log(f"   ⬆️  传输完成 {downloaded / 1048576:.1f}MB / {elapsed:.1f}s "
                     f"({downloaded / 1048576 / elapsed:.2f} MB/s)")
            return True, None
        except Exception as e:
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except Exception:
                    pass
            return False, str(e)

    @staticmethod
    def should_retry_error(error_msg):
        if not error_msg:
            return False
        keywords = ('timeout', 'timed out', 'connection', 'network', 'unreachable',
                    'refused', 'reset', 'broken pipe', 'eof', 'rate limit', 'ssl')
        return any(k in error_msg.lower() for k in keywords)

    # ---------------- 单个任务处理 ----------------
    def process_url(self, url):
        owner, repo = self.extract_repo_info(url)
        if not owner or not repo:
            self.log(f"❌ 无效的 GitHub 链接: {url}")
            return False

        self.log(f"📦 正在处理: {owner}/{repo}")

        branch = self.get_default_branch(owner, repo)
        if not branch:
            self.log(f"❌ 无法获取默认分支: {url}")
            return False

        latest_sha = self.get_latest_commit_sha(owner, repo, branch)
        if not latest_sha:
            self.log(f"❌ 无法获取最新 commit SHA: {url}")
            return False

        short_sha = latest_sha[:7]
        zip_name = f"{owner}_{repo}@{short_sha}.zip"
        zip_path = os.path.join(self.script_dir, zip_name)

        # 同名文件已存在则跳过（避免重复下载）
        if os.path.exists(zip_path):
            self.log(f"✅ 文件已存在，跳过: {zip_name}")
            return True

        zip_url = self.get_zip_url(owner, repo, branch)

        last_error = None
        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                self.log(f"🔄 重试 #{attempt}/{self.max_retries}: {owner}/{repo}")
                time.sleep(self.retry_delay)

            success, err = self.download_zip(zip_url, zip_path, zip_name)
            if success:
                self.log(f"✅ 下载完成: {zip_name}")
                return True

            last_error = err
            if not self.should_retry_error(err):
                self.log(f"❌ 下载失败（不可重试）: {err}")
                break

        self.log(f"❌ 下载失败: {url} ({last_error})")
        return False

    # ---------------- 工作线程 ----------------
    def _worker_loop(self):
        """后台消费队列，串行下载"""
        while not self.stop_event.is_set():
            try:
                url = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.process_url(url)
            except Exception as e:
                self.log(f"💥 处理出错: {url} - {e}")
            finally:
                self.task_queue.task_done()

    # ---------------- 主流程 ----------------
    def print_banner(self):
        print("=" * 60)
        print("🚀 GitHub ZIP 下载工具（终端交互版）")
        print("=" * 60)
        print(f"📁 下载目录: {self.script_dir}")
        print("💡 输入 GitHub 仓库链接后回车即可加入下载队列")
        print("💡 支持一次粘贴多个链接（空格/换行分隔）")
        print("💡 输入 exit / quit / q 退出程序")
        print("=" * 60)

    def run(self):
        self.print_banner()
        self.stop_event.clear()

        worker = threading.Thread(target=self._worker_loop, daemon=True)
        worker.start()

        try:
            while True:
                try:
                    line = input(self.PROMPT)
                except EOFError:
                    break

                line = line.strip()
                if not line:
                    continue
                if line.lower() in ('exit', 'quit', 'q'):
                    break

                tokens = line.split()
                if not tokens:
                    continue
                for token in tokens:
                    self.task_queue.put(token)
                self.log(f"📥 已加入 {len(tokens)} 个链接到队列 "
                         f"(待处理: {self.task_queue.qsize()})")
        except KeyboardInterrupt:
            print()
        finally:
            self._shutdown()

    def _shutdown(self):
        """退出前等待队列清空（可 Ctrl+C 强制退出）"""
        if self.task_queue.unfinished_tasks > 0:
            print(f"⏳ 队列中还有 {self.task_queue.unfinished_tasks} 个任务，等待完成...（按 Ctrl+C 强制退出）")
            try:
                self.task_queue.join()
            except KeyboardInterrupt:
                print("\n🛑 强制退出")
                os._exit(1)

        self.stop_event.set()
        print("👋 程序退出")


def main():
    try:
        downloader = GitHubZipDownloader()
        downloader.run()
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
    except Exception as e:
        print(f"💥 程序发生严重错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()