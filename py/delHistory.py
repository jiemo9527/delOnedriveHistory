import asyncio
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import multiprocessing


async def open_link_and_trigger_delete(url, browser, index,total, counter):
    try:
        # 访问网页
        browser.get(url)
        # 等待页面加载
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        print(f'\033[2K\r当前处理链接：第{index}/{total}条', end='', flush=True)
        # 直接触发deleteOnClick函数
        browser.execute_script("deleteOnClick();")
        # 等待弹出框并确认
        WebDriverWait(browser, 10).until(EC.alert_is_present())
        browser.switch_to.alert.accept()
        await asyncio.sleep(3)  # 使用asyncio.sleep而不是time.sleep
        with counter.get_lock():
            counter.value += 1

    except Exception as e:
        print(f'发生错误：{e}')
        time.sleep(5)


async def main(file_path, user_data_dirs):
    tasks = []
    browsers = []
    total_links = 0

    # 创建浏览器实例和任务
    for user_data_dir in user_data_dirs:
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'  # 修改为你的Chrome路径
        browser = webdriver.Chrome(options=options)
        browsers.append(browser)

    # 读取链接文件
    with open(file_path, 'r', encoding='utf-8') as file:
        links = [line.strip() for line in file.readlines()]
        total_links = len(links)

    # 创建计数器
    counter = multiprocessing.Value('i', 0)

    # 分配链接给每个浏览器
    for i, url in enumerate(links, 1):
        browser_index = (i - 1) % len(browsers)  # 确定当前链接应该分配给哪个浏览器
        browser = browsers[browser_index]
        tasks.append(asyncio.create_task(open_link_and_trigger_delete(url, browser, i,total_links, counter)))

    # 等待所有任务完成
    await asyncio.gather(*tasks)


    # 关闭所有浏览器实例
    for browser in browsers:
        browser.quit()


# 文件路径
file_path = 'links.txt'
# 每个浏览器实例的用户数据目录
user_data_dirs = [
    r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data',
    # r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data1',
]

# 运行主函数
asyncio.run(main(file_path, user_data_dirs))
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f'\n{current_time} 清除完毕！')
