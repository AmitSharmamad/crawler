import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from fake_useragent import UserAgent
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET
from collections import deque
import json
import time
from readability import Document

def get_stealth_context(p):
    """
    Creates a browser context with stealth settings.
    """
    ua = UserAgent()
    user_agent = ua.random
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(user_agent=user_agent)
    return browser, context

def auto_scroll(page):
    """
    Scrolls to the bottom of the page to trigger lazy loading.
    """
    last_height = page.evaluate("document.body.scrollHeight")
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)  # Wait for content to load
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def extract_content(url: str) -> str:
    """
    Extracts content from a given URL and converts it to Markdown.
    Uses stealth, auto-scroll, and readability for better quality.
    """
    with sync_playwright() as p:
        browser, context = get_stealth_context(p)
        page = context.new_page()
        stealth = Stealth()
        stealth.apply_stealth_sync(page)
        
        try:
            page.goto(url, wait_until="networkidle")
            auto_scroll(page)
            
            content = page.content()
            doc = Document(content)
            cleaned_html = doc.summary()
            
            # Convert to Markdown
            markdown = md(cleaned_html)
            return markdown
        except Exception as e:
            return f"Error extracting content: {e}"
        finally:
            browser.close()

def get_sitemap_urls(url: str, allowed_domain: str) -> list[str]:
    """
    Extracts URLs from sitemaps, filtering by allowed domain.
    """
    urls = []
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    sitemap_urls = []
    
    # Check robots.txt
    try:
        robots_resp = requests.get(urljoin(base_url, "/robots.txt"), timeout=10)
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
            resp = requests.get(sm_url, timeout=10)
            if resp.status_code == 200:
                try:
                    root = ET.fromstring(resp.content)
                    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                    
                    if root.tag.endswith('sitemapindex'):
                         for sitemap in root.findall('ns:sitemap', namespaces):
                            loc = sitemap.find('ns:loc', namespaces)
                            if loc is not None:
                                try:
                                    sub_resp = requests.get(loc.text, timeout=10)
                                    if sub_resp.status_code == 200:
                                        sub_root = ET.fromstring(sub_resp.content)
                                        for url_tag in sub_root.findall('ns:url', namespaces):
                                            loc_tag = url_tag.find('ns:loc', namespaces)
                                            if loc_tag is not None and urlparse(loc_tag.text).netloc == allowed_domain:
                                                urls.append(loc_tag.text)
                                except Exception:
                                    pass
                    else:
                        for url_tag in root.findall('ns:url', namespaces):
                            loc = url_tag.find('ns:loc', namespaces)
                            if loc is not None and urlparse(loc.text).netloc == allowed_domain:
                                urls.append(loc.text)
                except ET.ParseError:
                    pass
        except Exception:
            pass
            
    return urls

def get_common_crawl_urls(url: str, allowed_domain: str) -> list[str]:
    """
    Queries Common Crawl for URLs, filtering by allowed domain.
    """
    urls = []
    index_url = "http://index.commoncrawl.org/CC-MAIN-2024-33-index"
    query_url = f"{index_url}?url={allowed_domain}/*&output=json"
    
    try:
        resp = requests.get(query_url, timeout=10)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                try:
                    data = json.loads(line)
                    if 'url' in data:
                        if urlparse(data['url']).netloc == allowed_domain:
                            urls.append(data['url'])
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
        
    return urls

def is_allowed_by_robots(url: str, user_agent: str = "*") -> bool:
    """
    Checks if a URL is allowed by robots.txt.
    """
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = urljoin(base_url, "/robots.txt")
    
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True # Fail open if robots.txt is unreachable or invalid

def extract_links(url: str, strategy: str = 'bfs', depth: int = 1, use_sitemap: bool = True, use_cc: bool = True) -> list[str]:
    """
    Extracts links from a given URL using specified strategies.
    Enforces strict domain scoping and robots.txt compliance.
    """
    start_domain = urlparse(url).netloc
    found_urls = set()
    
    # 1. Active Crawling (BFS/DFS)
    if depth > 0:
        with sync_playwright() as p:
            browser, context = get_stealth_context(p)
            
            queue = deque([(url, 0)])
            visited = set()
            
            while queue:
                current_url, current_depth = queue.popleft() if strategy == 'bfs' else queue.pop()
                
                if current_url in visited or current_depth > depth:
                    continue
                
                # Domain Check
                if urlparse(current_url).netloc != start_domain:
                    continue

                # Robots.txt Check (Optimized: check once per domain usually, but here simple)
                if not is_allowed_by_robots(current_url):
                    continue

                visited.add(current_url)
                found_urls.add(current_url)
                
                if current_depth < depth:
                    try:
                        page = context.new_page()
                        stealth = Stealth()
                        stealth.apply_stealth_sync(page)
                        page.goto(current_url, wait_until="domcontentloaded", timeout=10000)
                        
                        links = page.eval_on_selector_all("a", "elements => elements.map(e => e.href)")
                        page.close()
                        
                        for link in links:
                            # Normalize and filter
                            # Remove fragments
                            link = link.split('#')[0]
                            if link.startswith("http"):
                                if urlparse(link).netloc == start_domain:
                                    queue.append((link, current_depth + 1))
                    except Exception as e:
                        print(f"Error crawling {current_url}: {e}")
            
            browser.close()

    # 2. Sitemap
    if use_sitemap:
        sitemap_urls = get_sitemap_urls(url, start_domain)
        found_urls.update(sitemap_urls)

    # 3. Common Crawl
    if use_cc:
        cc_urls = get_common_crawl_urls(url, start_domain)
        found_urls.update(cc_urls)

    return list(found_urls)

if __name__ == "__main__":
    # Test
    target = "https://docs.github.com/en/rest"
    print(f"Extracting content from {target}...")
    print(extract_content(target)[:100])
    
    print(f"\nExtracting links from {target}...")
    links = extract_links(target, depth=1, use_sitemap=False, use_cc=False)
    print(f"Found {len(links)} links: {links}")
