import asyncio
import os
import contextlib
import shutil
import time  # 保留 time 只是为了打印日志，睡眠已改为 asyncio.sleep
from playwright.async_api import async_playwright
from playwright.async_api import BrowserContext  # 明确导入类型

# --- 浏览器路径配置 (来自 thoriumDebugDemo.py) ---
THORIUM_PATH = r"C:\Users\Administrator\AppData\Local\Thorium\Application\thorium.exe"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


# --- 浏览器会话管理函数 (已重构为 ASYNC) ---
@contextlib.asynccontextmanager
async def get_async_browser_session(playwright: async_playwright) -> BrowserContext:
    """
    一个 ASYNC 上下文管理器，用于：
    1. 优先尝试连接 Thorium(9222)，失败则尝试 Chrome(9223)。
    2. 如果使用 Chrome，则异步复制默认 User Data 到 User Data2 (如果不存在) 并使用。
    3. 如果连接失败，则异步启动对应的浏览器新实例。
    4. 自动关闭由本脚本启动的浏览器进程。
    """
    browser_process = None
    context = None
    launch_user_data_dir = None

    # 1. 确定要使用的浏览器和端口
    if os.path.exists(THORIUM_PATH):
        exec_path = THORIUM_PATH
        debug_port = 9222
        browser_name = "Thorium"
    elif os.path.exists(CHROME_PATH):
        exec_path = CHROME_PATH
        debug_port = 9223
        browser_name = "Chrome"

        # --- MODIFIED: Chrome User Data 复制逻辑 (使用 asyncio.to_thread) ---
        try:
            default_user_data_src = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Google', 'Chrome',
                                                 'User Data')
            copied_user_data_dest = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Google', 'Chrome',
                                                 'User Data2')

            if not os.path.exists(copied_user_data_dest):
                print(f"未找到 'User Data2' 目录。")
                print(f"正在从默认配置复制，这可能需要几分钟时间...")
                print(f"源: {default_user_data_src}")
                print(f"目标: {copied_user_data_dest}")

                # <--- MODIFIED: 使用 to_thread 运行阻塞的 I/O 操作 ---
                start_copy_time = time.time()
                await asyncio.to_thread(
                    shutil.copytree,
                    default_user_data_src,
                    copied_user_data_dest,
                    ignore=shutil.ignore_patterns('lockfile', '*.lock')
                )
                end_copy_time = time.time()
                print(f"复制完成。耗时: {end_copy_time - start_copy_time:.2f} 秒")
            else:
                print(f"已找到 'User Data2' 目录，将直接使用。")

            launch_user_data_dir = copied_user_data_dest

        except Exception as copy_error:
            print(f"\n[严重错误] 复制 Chrome User Data 失败: {copy_error}")
            print("请确保 Chrome 浏览器已完全关闭 (包括任务管理器中的后台进程)，然后删除 'User Data2' 目录重试。")
            raise copy_error
        # --- 复制逻辑结束 ---

    else:
        print(f"错误: Thorium 和 Chrome 路径均未找到。")
        print(f"Thorium 路径: {THORIUM_PATH}")
        print(f"Chrome 路径: {CHROME_PATH}")
        raise FileNotFoundError("未找到 Thorium 或 Chrome 浏览器。")

    print(f"将使用 {browser_name} (端口: {debug_port})")

    try:
        # 2. 优先尝试连接
        try:
            print(f"正在尝试连接到 http://localhost:{debug_port}...")
            # <--- MODIFIED: 使用 async 版本的 connect_over_cdp ---
            browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            context = browser.contexts[0]
            print("连接成功！将使用已打开的浏览器实例。")

        except Exception as e:
            # 3. 连接失败，则启动新实例
            print(f"连接失败 ({e})。")
            print(f"（提示：如果浏览器已打开，请确保它是用 --remote-debugging-port={debug_port} 启动的）")
            print(f"正在启动一个新的 {browser_name} 实例...")

            # <--- MODIFIED: 准备启动参数 ---
            launch_args = [exec_path, f"--remote-debugging-port={debug_port}"]

            if browser_name == "Chrome" and launch_user_data_dir:
                launch_args.append(f"--user-data-dir={launch_user_data_dir}")
                print(f"使用复制的用户数据目录: {launch_user_data_dir}")

            # <--- MODIFIED: 使用 asyncio.create_subprocess_exec 启动进程 ---
            browser_process = await asyncio.create_subprocess_exec(*launch_args)

            print("等待浏览器启动...")
            # <--- MODIFIED: 使用 asyncio.sleep ---
            await asyncio.sleep(3)  # 等待进程启动

            # 再次尝试连接
            browser = await playwright.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
            context = browser.contexts[0]
            print(f"新实例连接成功！")

        # 4. 'yield' 上下文，供 with 语句块使用
        yield context

    except Exception as e:
        print(f"\n[浏览器管理错误] 连接或启动 {browser_name} 时失败: {e}")
        raise

    finally:
        # 5. 自动关闭 *由本脚本启动* 的浏览器进程
        if browser_process:
            print(f"\n任务结束，正在关闭由脚本启动的 {browser_name} 浏览器...")
            browser_process.terminate()  # 终止浏览器进程
            # <--- MODIFIED: 使用 await browser_process.wait() ---
            await browser_process.wait()
            print("浏览器已关闭。")
        else:
            print("\n任务结束。由于连接到的是现有浏览器实例，故不关闭浏览器。")


# --- 爬虫函数 (修改为接受 file_handle, lock 和 semaphore, 并立即写入) ---
async def get_feature_links(url: str, browser: BrowserContext, file_handle, lock: asyncio.Lock,
                            semaphore: asyncio.Semaphore) -> int:
    """
    递归爬取 SharePoint 页面以获取所有“版本历史记录”链接, 并立即写入文件。

    Args:
        url: 要爬取的起始 URL。
        browser: Playwright 的 BrowserContext 实例 (由 get_async_browser_session 提供)。
        file_handle: 已打开的可写文件句柄。
        lock: 用于同步文件写入的 asyncio.Lock。
        semaphore: 用于控制并发标签页数量的 asyncio.Semaphore。

    Returns:
        一个整数，表示在此分支中找到的链接数量。
    """
    links_found_count = 0
    page = None  # 在 try 外部定义 page 以便在 finally 中使用
    try:
        # --- MODIFIED: 在创建页面前获取信号量 ---
        print(f"[{url}] 等待信号量...")
        async with semaphore:
            print(f"[{url}] 已获取信号量，正在打开页面...")
            page = await browser.new_page()
            print(f"正在处理: {url}")
            await page.goto(url, timeout=120000)
            await page.wait_for_selector('tr', timeout=120000)

            folder_links = await page.evaluate('''() => {
                const links = [];
                const rows = document.querySelectorAll('tr');
                rows.forEach(row => {
                    const folderLink = row.querySelector('td:nth-child(2) a');
                    if (folderLink && folderLink.href.includes('/storman.aspx?root=')) { // 确保是文件夹链接
                        links.push(folderLink.href);
                    }
                });
                return links;
            }''')

            feature_links_on_page = await page.evaluate('''() => {
                const links = [];
                const featureLinks = document.querySelectorAll('a');
                featureLinks.forEach(link => {
                    if (link.textContent === '版本历史记录') {
                        links.push(link.href);
                    }
                });
                return links;
            }''')

            # --- MODIFIED: 立即写入文件 ---
            if feature_links_on_page:
                async with lock:  # 文件锁
                    for link in feature_links_on_page:
                        file_handle.write(link + '\n')
                links_found_count += len(feature_links_on_page)
                print(f"在 {url} 找到 {len(feature_links_on_page)} 个链接并已写入。")
            # --- 写入结束 ---

            next_page_link = await page.evaluate('''() => {
                const nextPageLink = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes('下一个'));
                return nextPageLink ? nextPageLink.href : null;
            }''')

            await page.close()
            print(f"[{url}] 页面已关闭，释放信号量。")
        # --- 信号量在此自动释放 ---

        # 递归调用在信号量块之外发起
        # 递归处理下一页
        if next_page_link:
            print(f"找到下一页: {next_page_link}")
            # --- MODIFIED: 传递 file_handle, lock 和 semaphore ---
            links_found_count += await get_feature_links(next_page_link, browser, file_handle, lock, semaphore)

        # 递归处理子文件夹
        # 使用 asyncio.gather 并发处理所有子文件夹
        # --- MODIFIED: 传递 file_handle, lock 和 semaphore ---
        folder_tasks = [get_feature_links(link, browser, file_handle, lock, semaphore) for link in folder_links]
        results = await asyncio.gather(*folder_tasks)

        # results 现在是链接数量的列表 [int, int, ...]
        links_found_count += sum(results)

        print(f"在 {url} 及其子项中完成处理。")
        return links_found_count

    except Exception as e:
        print(f"处理 {url} 时出错: {e}")
        if page and not page.is_closed():
            await page.close()  # 确保页面关闭
        # async with 会自动处理异常并释放信号量
        return 0  # 返回0以继续执行


# --- 主函数 (修改后使用新的 context manager) ---
async def main(url):
    total_links_found = 0
    try:
        async with async_playwright() as p:
            print("正在启动 Playwright 并获取浏览器会话...")
            # <--- MODIFIED: 使用新的 async context manager ---
            # 它会返回一个 BrowserContext，这与 launch_persistent_context 的返回类型一致
            async with get_async_browser_session(p) as browser_context:
                print("浏览器会话已获取，开始爬取...")

                # --- MODIFIED: 在爬取前打开文件并创建锁和信号量 ---
                file_lock = asyncio.Lock()

                # --- NEW: 创建并发信号量 ---
                concurrency_limit = 15
                semaphore = asyncio.Semaphore(concurrency_limit)
                print(f"并发标签页上限设置为: {concurrency_limit}")

                output_filename = 'links.txt'

                with open(output_filename, 'w', encoding='utf-8') as file:
                    print(f"将实时写入链接到 {output_filename}...")

                    # --- MODIFIED: 传递文件句柄、锁和信号量, 并接收总数 ---
                    total_links_found = await get_feature_links(url, browser_context, file, file_lock, semaphore)

            # <--- MODIFIED: 移除了 await browser.close() ---
            # context manager 会自动处理进程关闭
            # <--- MODIFIED: 移除了文件写入逻辑 (已在内部完成) ---

            print(f"\n爬取完成。总共找到并写入 {total_links_found} 个链接。")
            print('写入 links.txt 完成！ over over!!!')

    except Exception as e:
        print(f"发生致命错误: {e}")


# --- 启动器 (来自您的原始脚本) ---
if __name__ == "__main__":
    # start_url = 'https://brecenmoqi-my.sharepoint.com/personal/jiemo_todesign_cn/_layouts/15/storman.aspx?root=Documents'
    start_url = 'https://brecenmoqi.sharepoint.com/sites/jiemo/_layouts/15/storman.aspx?root=Shared%20Documents'

    print(f"起始 URL: {start_url}")
    asyncio.run(main(start_url))

