from playwright.async_api import async_playwright
import asyncio


async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://developer.atlassian.com/cloud/jira/platform/rest/v3")
        print(await page.title())
        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
