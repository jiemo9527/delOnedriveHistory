import sys
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import asyncio


async def open_link_and_trigger_delete(url, driver):
    # 打开新页面
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])

    try:
        # 访问网页
        driver.get(url)
        # 等待页面加载
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        # 直接触发deleteOnClick函数
        driver.execute_script("deleteOnClick();")
        # 等待弹出框并确认
        WebDriverWait(driver, 10).until(EC.alert_is_present())
        driver.switch_to.alert.accept()
        time.sleep(3)
    except Exception as e:
        print(f'发生错误：{e}')
    finally:
        # 关闭页面
        driver.close()
        driver.switch_to.window(driver.window_handles[0])


async def main(file_path):
    # 启动Chrome浏览器
    options = webdriver.ChromeOptions()
    options.add_argument(r"user-data-dir=C:\Users\Administrator\AppData\Local\Google\Chrome\User Data")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    # 读取文件中的链接
    with open(file_path, 'r', encoding='utf-8') as file:
        links = [line.strip() for line in file.readlines()]

    total_links = len(links)
    current_link = 0

    # 遍历链接并执行操作
    for url in links:
        current_link += 1
        await open_link_and_trigger_delete(url, driver)
        time.sleep(2)
        sys.stdout.write(f'\r处理进度: {current_link}/{total_links}')
        sys.stdout.flush()
    # 关闭浏览器
    driver.quit()


# 文件路径
file_path = 'links.txt'
# 运行主函数
asyncio.get_event_loop().run_until_complete(main(file_path))
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f'\n{current_time} 清除完毕！')

