import asyncio
from playwright.async_api import async_playwright

async def get_feature_links(url, browser):
    try:
        page = await browser.new_page()
        await page.goto(url, timeout=120000)  # 设置超时时间为2分钟
        await page.wait_for_selector('tr', timeout=120000)  # 等待2分钟

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

        next_page_link = await page.evaluate('''() => {
            const nextPageLink = Array.from(document.querySelectorAll('a')).find(el => el.innerText.includes('下一个'));
            return nextPageLink ? nextPageLink.href : null;
        }''')

        if next_page_link:
            feature_links += await get_feature_links(next_page_link, browser)

        for link in folder_links:
            feature_links += await get_feature_links(link, browser)

        await page.close()
        print(len(feature_links))
        return feature_links

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []

async def main(url):
    try:
        async with async_playwright() as p:
            user_data_dir = r'C:\Users\Administrator\AppData\Local\Google\Chrome\User Data1'  # 修改为你的路径
            browser = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
            feature_links = await get_feature_links(url, browser)
            await browser.close()

            with open('links.txt', 'w', encoding='utf-8') as file:
                for link in feature_links:
                    file.write(link + '\n')

            print('over over!!!')
    except Exception as e:
        print(f"发生错误: {e}")

# start_url = input('输入sharepoint地址:')
start_url = 'https://brecenmoqi-my.sharepoint.com' + '/personal/jiemo_todesign_cn/_layouts/15/storman.aspx?root=Documents'
asyncio.run(main(start_url))

# start_url = start_url + '/_layouts/15/storman.aspx?root=Documents'

