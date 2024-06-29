import asyncio
from pyppeteer import launch

async def get_feature_links(url, browser):
    # 打开新页面
    page = await browser.newPage()
    # 访问网页
    await page.goto(url)
    await page.waitForSelector('tr', timeout=120000)  # 等待2分钟

    # 收集所有文件夹链接
    folder_links = await page.evaluate('''() => {
        const links = [];
        const rows = document.querySelectorAll('tr');
        rows.forEach(row => {
            const folderLink = row.querySelector('td:nth-child(2) a');
            if (folderLink) {
                links.push(folderLink.href);
            }
        });
        return links;
    }''')
    # 收集特征链接
    feature_links = await page.evaluate('''() => {
        const links = [];
        const featureLinks = document.querySelectorAll('a');
        featureLinks.forEach(link => {
            if (link.textContent === '版本历史记录') {
                links.push(link.href);
            }
        });
        return links;
    }''')
    # 检查是否存在内容为“下一个”的a标签，并在收集完当前页特征链接后判断
    next_page_link = await page.evaluate('''() => {
        const nextPageLink = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes('下一个'));
        return nextPageLink ? nextPageLink.href : null;
    }''')
    # 如果存在“下一个”链接，则递归调用函数处理下一页
    if next_page_link:
        feature_links += await get_feature_links(next_page_link, browser)
    # 关闭当前页面
    await page.close()
    # 对每个文件夹链接递归调用当前函数
    for link in folder_links:
        feature_links += await get_feature_links(link, browser)
    return feature_links

async def main(url):
    # 启动浏览器，指定Chrome的可执行文件路径
    browser = await launch(headless=False,
                           executablePath=r'C:\Program Files\Google\Chrome\Application\chrome.exe',  # 修改为你的Chrome路径
                           userDataDir=r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data')
    # 获取特征链接
    feature_links = await get_feature_links(url, browser)
    # 关闭浏览器
    await browser.close()
    # 将链接写入文件
    with open('links.txt', 'w', encoding='utf-8') as file:
        for link in feature_links:
            file.write(link + '\n')
    print('over over!!!')

# 调用main函数
start_url = input('输入sharepoint地址:')
start_url = start_url + '/_layouts/15/storman.aspx?root=Documents'
asyncio.get_event_loop().run_until_complete(main(start_url))
