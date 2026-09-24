import requests
import time
import json
import sys
from datetime import datetime, timedelta

# 配置
USERNAME = "i12cu2"
OUTPUT_FILE = f"github_stars_{USERNAME}_all_api.txt"
MAX_PAGES = 10
MAX_RETRIES = 500  # 最大重试次数
RETRY_DELAY = 5  # 重试等待时间（秒）
RATE_LIMIT_WAIT = 3600  # 被限速时等待1小时

print("=== GitHub Stars爬虫 - 完整重试版 ===")
print(f"🎯 目标用户: {USERNAME}")
print(f"💾 结果文件: {OUTPUT_FILE}")
print(f"🔄 支持自动重试，智能处理API限制")
print("=" * 60)

def get_stars_with_retry(username, max_pages=10, max_retries=MAX_RETRIES):
    """使用GitHub API获取用户的所有stars，包含重试机制"""
    all_repos = []
    seen_repos = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # 建议用户添加个人访问令牌
    print("\n💡 重要提示: 为避免API限制，建议在代码中添加个人访问令牌(PAT)")
    print("   在GitHub → Settings → Developer settings → Personal access tokens 创建")
    print("   然后在headers中添加: headers['Authorization'] = 'token YOUR_TOKEN_HERE'\n")
    
    page = 1
    retry_count = 0
    
    while page <= max_pages and retry_count < max_retries:
        url = f"https://api.github.com/users/{username}/starred?per_page=100&page={page}"
        
        print(f"\n🔄 请求第 {page} 页: {url}")
        print(f"⏱️  当前时间: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"✅ 状态码: {response.status_code}")
            
            if response.status_code == 200:
                repos = response.json()
                print(f"⭐ 第 {page} 页: 找到 {len(repos)} 个仓库")
                
                if not repos:
                    print("🔚 没有更多仓库，停止爬取")
                    break
                
                new_count = 0
                for repo in repos:
                    repo_url = repo.get('html_url', '')
                    if repo_url and repo_url not in seen_repos:
                        seen_repos.add(repo_url)
                        all_repos.append(repo_url)
                        new_count += 1
                
                print(f"   ✅ 新增: {new_count} 个唯一仓库，总计: {len(all_repos)}")
                
                # 检查是否是最后一页
                if len(repos) < 100:
                    print("🔚 检测到最后一页")
                    break
                
                # 重置重试计数器
                retry_count = 0
                
                # 速率限制处理 - 每次请求后等待0.5秒
                time.sleep(0.5)
                page += 1
                
            elif response.status_code == 403:
                # 处理GitHub API速率限制
                retry_count += 1
                remaining = response.headers.get('X-RateLimit-Remaining', '未知')
                reset_time = response.headers.get('X-RateLimit-Reset', '未知')
                
                print(f"❌ 被GitHub API限制访问 (剩余请求: {remaining})")
                print(f"⏰ 重置时间: {datetime.fromtimestamp(int(reset_time)).strftime('%H:%M:%S') if reset_time != '未知' else '未知'}")
                print(f"🔄 第 {retry_count} 次重试，等待 {RATE_LIMIT_WAIT} 秒...")
                
                if retry_count >= max_retries:
                    print(f"❌ 已达到最大重试次数 ({max_retries})，停止爬取")
                    break
                
                # 智能等待 - 根据重置时间等待
                if reset_time != '未知':
                    reset_timestamp = int(reset_time)
                    current_timestamp = int(time.time())
                    wait_time = max(reset_timestamp - current_timestamp + 5, RATE_LIMIT_WAIT)
                else:
                    wait_time = RATE_LIMIT_WAIT
                
                print(f"⏳ 等待 {wait_time} 秒后重试...")
                
                for i in range(wait_time):
                    time.sleep(1)
                    if i % 30 == 0 and i > 0:
                        print(f"   ⏳ 已等待 {i} 秒，还需 {wait_time - i} 秒...")
                
            elif response.status_code == 404:
                print(f"❌ 用户 {username} 不存在或没有公开stars")
                break
            else:
                retry_count += 1
                print(f"❌ API错误: {response.status_code}")
                print(f"   响应内容: {response.text[:200]}...")
                
                if retry_count >= max_retries:
                    print(f"❌ 已达到最大重试次数 ({max_retries})，停止爬取")
                    break
                
                print(f"🔄 第 {retry_count} 次重试，等待 {RETRY_DELAY} 秒...")
                time.sleep(RETRY_DELAY)
                
        except requests.exceptions.RequestException as e:
            retry_count += 1
            print(f"❌ 网络请求错误: {str(e)}")
            
            if retry_count >= max_retries:
                print(f"❌ 已达到最大重试次数 ({max_retries})，停止爬取")
                break
            
            print(f"🔄 第 {retry_count} 次重试，等待 {RETRY_DELAY} 秒...")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            retry_count += 1
            print(f"❌ 未知错误: {str(e)}")
            
            if retry_count >= max_retries:
                print(f"❌ 已达到最大重试次数 ({max_retries})，停止爬取")
                break
            
            print(f"🔄 第 {retry_count} 次重试，等待 {RETRY_DELAY} 秒...")
            time.sleep(RETRY_DELAY)
    
    return all_repos

def save_results(repos, filename):
    """保存结果到文件"""
    if not repos:
        print("❌ 没有仓库可以保存")
        return False
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for url in repos:
                f.write(f"{url}\n")
        print(f"✅ 成功保存 {len(repos)} 个仓库到 {filename}")
        return True
    except Exception as e:
        print(f"❌ 保存文件错误: {str(e)}")
        return False

def main():
    print("\n🚀 开始使用GitHub API获取stars...")
    print("🔄 智能重试机制已启用，自动处理API限制")
    
    # 获取所有stars
    all_repos = get_stars_with_retry(USERNAME, MAX_PAGES, MAX_RETRIES)
    
    print(f"\n{'='*60}")
    print(f"🎉 获取完成！")
    print(f"📊 总仓库数: {len(all_repos)}")
    print(f"{'='*60}")
    
    if all_repos:
        # 排序
        all_repos.sort()
        
        # 保存结果
        save_results(all_repos, OUTPUT_FILE)
        
        # 显示统计信息
        print(f"\n📊 详细统计:")
        print(f"   - 总仓库数: {len(all_repos)}")
        print(f"   - 文件大小: {len(all_repos) * 100:,} 字节（约）")
        
        # 显示前10个
        print("\n📋 前10个仓库:")
        for i, url in enumerate(all_repos[:10], 1):
            print(f"{i:2d}. {url}")
        
        if len(all_repos) > 10:
            print(f"... 等 {len(all_repos)-10} 个仓库")
        
        print(f"\n🔍 完整列表请查看: {OUTPUT_FILE}")
        
        # 生成统计摘要
        summary_file = OUTPUT_FILE.replace('.txt', '_summary.txt')
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"GitHub Stars 爬取报告\n")
            f.write(f"=======================\n")
            f.write(f"用户名: {USERNAME}\n")
            f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总仓库数: {len(all_repos)}\n")
            f.write(f"结果文件: {OUTPUT_FILE}\n")
            f.write(f"重试次数: {MAX_RETRIES}\n")
            f.write(f"\n前10个仓库:\n")
            for i, url in enumerate(all_repos[:10], 1):
                f.write(f"{i}. {url}\n")
        print(f"📊 统计摘要已保存到: {summary_file}")
    else:
        print("\n❌ 未找到任何仓库！")
        print("🔧 可能原因和解决方案:")
        print(f"1. 用户 {USERNAME} 不存在或没有公开stars")
        print("2. GitHub API限制 - 建议添加个人访问令牌(PAT)")
        print("   方法: 在headers中添加: headers['Authorization'] = 'token YOUR_TOKEN_HERE'")
        print("3. 网络连接问题 - 检查网络连接")
        print("4. 频率限制 - 程序会自动重试，但可能需要等待")
    
    print(f"\n{'='*60}")
    print("✅ 程序执行完毕！")
    print("💡 最佳实践建议:")
    print("   1. 为GitHub API创建个人访问令牌(PAT) - 这是最有效的解决方案")
    print("   2. 如果频繁使用，考虑使用缓存机制")
    print("   3. 尊重GitHub的API使用政策")
    print(f"{'='*60}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户中断程序")
        print("⏰ 程序将在10秒后退出，以便保存当前进度...")
        time.sleep(10)
    except Exception as e:
        print(f"\n❌ 严重错误: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n🔧 建议解决方案:")
        print("1. 检查网络连接")
        print("2. 确认GitHub用户名正确")
        print("3. 添加个人访问令牌(PAT)")
        print("4. 降低请求频率")