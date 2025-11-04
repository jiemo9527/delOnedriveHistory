import asyncio
import os
import contextlib
import shutil
import time
from datetime import datetime
from playwright.async_api import async_playwright, BrowserContext, Dialog

# --- 浏览器路径配置 (来自 demo) ---
THORIUM_PATH = r"C:\Users\Administrator\AppData\Local\Thorium\Application\thorium.exe"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


# --- 浏览器会话管理函数 (来自 demo) ---
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


# --- 新的链接处理函数 (使用 Playwright) ---
async def open_link_and_trigger_delete(
        url: str,
        browser_context: BrowserContext,
        index: int,
        total: int,
        counter_lock: asyncio.Lock,
        semaphore: asyncio.Semaphore
) -> int:
    """
    使用 Playwright 打开链接，触发 deleteOnClick()，并自动处理弹窗。
    """
    page = None
    try:
        # 在创建页面前获取信号量
        async with semaphore:
            print(f'\033[2K\r正在处理链接：第{index}/{total}条 (等待信号量...)', end='', flush=True)
            page = await browser_context.new_page()

            # --- 关键: 设置事件监听器以自动接受弹窗 ---
            async def handle_dialog(dialog: Dialog):
                # --- MODIFIED: 添加 try/except 来处理 "No dialog is showing" 错误 ---
                try:
                    await dialog.accept()
                except Exception as e:
                    # 忽略 "No dialog is showing" 错误，这可能在竞态条件下发生
                    print(f'\n[警告] 尝试 accept() 一个已消失的弹窗 (已忽略): {e}')

            page.on('dialog', handle_dialog)

            # 访问网页
            print(f'\033[2K\r正在处理链接：第{index}/{total}条 (正在打开 {url[:50]}...)', end='', flush=True)
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')

            # 直接触发deleteOnClick函数
            await page.evaluate("deleteOnClick();")

            # 等待弹窗处理和后续操作
            await asyncio.sleep(3)  # 等待删除操作完成

            print(f'\033[2K\r已处理链接：第{index}/{total}条', end='', flush=True)
            await page.close()

        # 更新计数器
        async with counter_lock:
            return 1  # 表示成功处理 1 个

    except Exception as e:
        print(f'\n处理链接 {url} 时发生错误：{e}')
        return 0  # 表示处理失败 0 个
    finally:
        if page and not page.is_closed():
            await page.close()  # 确保页面在出错时也能关闭


# --- 新的主函数 ---
async def main(file_path):
    total_processed = 0
    links = []

    # 1. 读取链接文件
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            links = [line.strip() for line in file.readlines() if line.strip()]
        total_links = len(links)
        if total_links == 0:
            print(f"文件 {file_path} 为空，无需处理。")
            return
    except FileNotFoundError:
        print(f"错误: 未找到链接文件 {file_path}")
        return
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {e}")
        return

    print(f"文件读取完毕，共 {total_links} 条链接待处理。")

    try:
        async with async_playwright() as p:
            print("正在启动 Playwright 并获取浏览器会话...")
            async with get_async_browser_session(p) as browser_context:
                print("浏览器会话已获取，开始处理链接...")

                counter_lock = asyncio.Lock()

                # 设置并发上限
                concurrency_limit = 15
                semaphore = asyncio.Semaphore(concurrency_limit)
                print(f"并发标签页上限设置为: {concurrency_limit}")

                tasks = []
                for i, url in enumerate(links, 1):
                    tasks.append(asyncio.create_task(
                        open_link_and_trigger_delete(url, browser_context, i, total_links, counter_lock, semaphore)
                    ))

                # 等待所有任务完成
                results = await asyncio.gather(*tasks)
                total_processed = sum(results)

    except Exception as e:
        print(f"\n发生致命错误: {e}")

    print(f'\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 清除完毕！')
    print(f"总共成功处理了 {total_processed} / {total_links} 个链接。")


# --- 启动器 ---
if __name__ == "__main__":
    # 文件路径
    file_path = 'links.txt'

    # 运行主函数
    # 注意: user_data_dirs 列表不再需要，因为 get_async_browser_session 会自动处理
    asyncio.run(main(file_path))

