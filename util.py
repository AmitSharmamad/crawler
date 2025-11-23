import httpx
from markdownify import markdownify as md
from playwright_stealth import Stealth
from fake_useragent import UserAgent
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
import json
import asyncio
from readability import Document


async def get_stealth_context(p, headless=True):
    """
    Creates a browser context with stealth settings.
    """
    ua = UserAgent()
    user_agent = ua.random
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(user_agent=user_agent)
    return browser, context


async def apply_stealth(page):
    """
    Applies stealth to a page.
    Note: playwright-stealth has sync API, but we run it in async context to avoid warnings
    """
    stealth = Stealth()
    # Run sync stealth in executor to avoid blocking
    await asyncio.to_thread(stealth.apply_stealth_sync, page)


async def auto_scroll(page):
    """
    Scrolls to the bottom of the page to trigger lazy loading.
    """
    last_height = await page.evaluate("document.body.scrollHeight")
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)  # Wait for content to load
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def clean_html(content: str) -> str:
    """
    Cleans HTML using readability-lxml.
    """
    try:
        doc = Document(content)
        return doc.summary()
    except Exception:
        return content


def convert_to_markdown(html: str) -> str:
    """
    Converts HTML to Markdown.
    """
    return md(html)


async def get_sitemap_urls(url: str, allowed_domain: str) -> list[str]:
    """
    Extracts URLs from sitemaps, filtering by allowed domain.
    """
    urls = []
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    sitemap_urls = []

    # Check robots.txt
    async with httpx.AsyncClient() as client:
        try:
            robots_resp = await client.get(urljoin(base_url, "/robots.txt"), timeout=10)
            if robots_resp.status_code == 200:
                for line in robots_resp.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemap_urls.append(line.split(":", 1)[1].strip())
        except Exception:
            pass

        if not sitemap_urls:
            sitemap_url = urljoin(base_url, "/sitemap.xml")
            sitemap_urls.append(sitemap_url)

        for sm_url in sitemap_urls:
            try:
                resp = await client.get(sm_url, timeout=10)
                if resp.status_code == 200:
                    try:
                        root = ET.fromstring(resp.content)
                        namespaces = {
                            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
                        }

                        if root.tag.endswith("sitemapindex"):
                            for sitemap in root.findall("ns:sitemap", namespaces):
                                loc = sitemap.find("ns:loc", namespaces)
                                if loc is not None:
                                    try:
                                        sub_resp = await client.get(
                                            loc.text, timeout=10
                                        )
                                        if sub_resp.status_code == 200:
                                            sub_root = ET.fromstring(sub_resp.content)
                                            for url_tag in sub_root.findall(
                                                "ns:url", namespaces
                                            ):
                                                loc_tag = url_tag.find(
                                                    "ns:loc", namespaces
                                                )
                                                if (
                                                    loc_tag is not None
                                                    and urlparse(loc_tag.text).netloc
                                                    == allowed_domain
                                                ):
                                                    urls.append(loc_tag.text)
                                    except Exception:
                                        pass
                        else:
                            for url_tag in root.findall("ns:url", namespaces):
                                loc = url_tag.find("ns:loc", namespaces)
                                if (
                                    loc is not None
                                    and urlparse(loc.text).netloc == allowed_domain
                                ):
                                    urls.append(loc.text)
                    except ET.ParseError:
                        pass
            except Exception:
                pass

    return urls


async def get_common_crawl_urls(url: str, allowed_domain: str) -> list[str]:
    """
    Queries Common Crawl for URLs, filtering by allowed domain.
    """
    urls = []
    index_url = "http://index.commoncrawl.org/CC-MAIN-2024-33-index"
    query_url = f"{index_url}?url={allowed_domain}/*&output=json"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(query_url, timeout=10)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    try:
                        data = json.loads(line)
                        if "url" in data:
                            if urlparse(data["url"]).netloc == allowed_domain:
                                urls.append(data["url"])
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    return urls


async def is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """
    Checks if a URL is allowed by robots.txt.
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")

    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        # RobotFileParser.read() is synchronous, but the HTTP request part needs async
        # For now, using synchronous read as it internally uses urllib
        # A better approach would be to fetch robots.txt with httpx and parse manually
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(robots_url, timeout=5)
                if resp.status_code == 200:
                    # Parse robots.txt content
                    rp.parse(resp.text.splitlines())
                    return rp.can_fetch(user_agent, url)
            except Exception:
                return True  # Fail open
    except Exception:
        return True  # Fail open

    return True
