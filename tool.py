from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from collections import deque
import util
import json
import httpx


async def inspect_site(url: str) -> dict:
    """
    Inspects a website to understand its structure, metadata, and organization.

    This function performs a comprehensive analysis of a website by:
    - Extracting metadata (title, description, keywords)
    - Analyzing navigation structure (header, nav, footer links)
    - Parsing sitemap to understand site structure

    Args:
        url (str): The website URL to inspect. Must include protocol (http/https).

    Returns:
        dict: A dictionary containing:
            - metadata (dict): Page metadata
                - title (str): Page title
                - description (str | None): Meta description
                - keywords (str | None): Meta keywords
            - navigation (dict): Navigation links by section
                - header (list): Links in <header> tags
                - nav (list): Links in <nav> tags
                - footer (list): Links in <footer> tags
                Each link is: {"text": str, "url": str}
            - sitemap_summary (dict): Sitemap analysis
                - total_urls (int): Total URLs in sitemap
                - structure_hint (dict): URL path prefixes and counts
            - error (str): Error message if inspection failed (optional)

    Example:
        >>> result = await inspect_site("https://example.com")
        >>> print(result['metadata']['title'])
        'Example Domain'
        >>> print(result['sitemap_summary']['total_urls'])
        150

    Note:
        - Uses stealth mode to avoid detection
        - Respects robots.txt for sitemap discovery
        - Timeout is 15 seconds for page load
    """
    result = {"metadata": {}, "navigation": {}, "sitemap_summary": {}}

    async with async_playwright() as p:
        browser, context = await util.get_stealth_context(p)
        page = await context.new_page()
        await util.apply_stealth(page)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Metadata
            result["metadata"]["title"] = await page.title()
            try:
                result["metadata"]["description"] = await page.locator(
                    'meta[name="description"]'
                ).get_attribute("content")
            except Exception:
                result["metadata"]["description"] = None
            try:
                result["metadata"]["keywords"] = await page.locator(
                    'meta[name="keywords"]'
                ).get_attribute("content")
            except Exception:
                result["metadata"]["keywords"] = None

            # Navigation
            for section in ["header", "nav", "footer"]:
                links = []
                try:
                    elements = await page.locator(section).all()
                    for el in elements:
                        anchors = await el.locator("a").all()
                        for a in anchors:
                            href = await a.get_attribute("href")
                            text = (await a.inner_text()).strip()
                            if href and text:
                                links.append({"text": text, "url": urljoin(url, href)})
                except Exception:
                    pass
                result["navigation"][section] = links

        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()

    # Sitemap Summary
    domain = urlparse(url).netloc
    sitemap_urls = await util.get_sitemap_urls(url, domain)
    result["sitemap_summary"]["total_urls"] = len(sitemap_urls)
    # Simple heuristic to guess structure from sitemap
    paths = [urlparse(u).path for u in sitemap_urls]
    common_prefixes = {}
    for path in paths:
        prefix = "/" + path.strip("/").split("/")[0]
        common_prefixes[prefix] = common_prefixes.get(prefix, 0) + 1
    result["sitemap_summary"]["structure_hint"] = common_prefixes

    return result


async def discover_links(
    url: str, keywords: list[str], scope: str = "domain"
) -> list[dict]:
    """
    Discovers and ranks links on a webpage based on keyword relevance.

    Searches through all links on a page and scores them based on keyword matches
    in both the URL and anchor text. Results are ranked by relevance score.

    Args:
        url (str): The webpage URL to search for links.
        keywords (list[str]): List of keywords to search for. Case-insensitive.
        scope (str, optional): Link scope filter. Defaults to "domain".
            - "domain": Allow links from any subdomain of the main domain
            - "subdomain": Only exact subdomain matches

    Returns:
        list[dict]: Sorted list of matching links (highest score first):
            - url (str): Full URL of the link
            - text (str): Anchor text
            - score (int): Relevance score (URL match=5, text match=10)
            - matches (list[str]): List of match descriptions (e.g., ["url:api", "text:docs"])

    Example:
        >>> links = await discover_links(
        ...     "https://python.org",
        ...     keywords=["documentation", "tutorial", "download"]
        ... )
        >>> for link in links[:3]:
        ...     print(f"{link['score']}: {link['text']} - {link['url']}")
        15: Download Python - https://python.org/downloads
        10: Documentation - https://python.org/docs

    Note:
        - Empty links are automatically filtered out
        - Links are deduplicated by URL
        - Scoring: URL keyword match = +5 points, text match = +10 points
        - Uses stealth mode to avoid bot detection
    """
    discovered = []
    start_domain = urlparse(url).netloc

    async with async_playwright() as p:
        browser, context = await util.get_stealth_context(p)
        page = await context.new_page()
        await util.apply_stealth(page)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            anchors = await page.locator("a").all()

            for a in anchors:
                try:
                    href = await a.get_attribute("href")
                    text = (await a.inner_text()).strip()

                    if not href:
                        continue

                    full_url = urljoin(url, href)
                    parsed_href = urlparse(full_url)

                    # Scope check
                    if scope == "domain" and start_domain not in parsed_href.netloc:
                        continue
                    if (
                        scope == "subdomain" and parsed_href.netloc != start_domain
                    ):  # Strict subdomain
                        continue

                    score = 0
                    matches = []

                    # Keyword matching
                    for kw in keywords:
                        kw_lower = kw.lower()
                        if kw_lower in full_url.lower():
                            score += 5
                            matches.append(f"url:{kw}")
                        if kw_lower in text.lower():
                            score += 10
                            matches.append(f"text:{kw}")

                    if score > 0:
                        discovered.append(
                            {
                                "url": full_url,
                                "text": text,
                                "score": score,
                                "matches": matches,
                            }
                        )

                except Exception:
                    continue

        except Exception as e:
            print(f"Error in discover_links: {e}")
        finally:
            await browser.close()

    return sorted(discovered, key=lambda x: x["score"], reverse=True)


async def extract_links(
    url: str,
    topology: str = "mesh",
    scope: str = "subdomain",
    ignore_queries: bool = True,
    max_pages: int = 50,
) -> list[str]:
    """
    Crawls a website to discover internal links using various crawling strategies.

    Performs breadth-first or specialized crawling based on topology parameter.
    Respects robots.txt and applies scope restrictions.

    Args:
        url (str): Starting URL for the crawl.
        topology (str, optional): Crawling strategy. Defaults to "mesh".
            - "mesh": Breadth-first search, discovers all connected pages
            - "linear": Follows next/previous links (pagination)
            - "hub_and_spoke": Only crawls direct links from start page (depth 1)
            - "sidebar": Focuses on sidebar and navigation links
        scope (str, optional): URL scope restriction. Defaults to "subdomain".
            - "subdomain": Only exact subdomain match (e.g., www.example.com)
            - "domain": Allow all subdomains (e.g., *.example.com)
            - "path": Stay within same path prefix (not yet implemented)
        ignore_queries (bool, optional): Strip query parameters from URLs. Defaults to True.
        max_pages (int, optional): Maximum pages to crawl. Defaults to 50.

    Returns:
        list[str]: List of discovered URLs (unique).

    Example:
        >>> # Crawl entire site
        >>> urls = await extract_links(
        ...     "https://example.com",
        ...     topology="mesh",
        ...     max_pages=100
        ... )
        >>> print(f"Found {len(urls)} pages")

        >>> # Only get direct links
        >>> urls = await extract_links(
        ...     "https://example.com/docs",
        ...     topology="hub_and_spoke"
        ... )

    Note:
        - Depth limit: mesh=3, hub_and_spoke=1
        - Automatically checks robots.txt compliance
        - Removes fragment identifiers (#) from URLs
        - Query parameters removed if ignore_queries=True
        - Uses stealth mode to avoid detection
        - Stops when max_pages reached or no more links
    """
    start_domain = urlparse(url).netloc
    found_urls = set()
    queue = deque([(url, 0)])
    visited = set()

    depth_limit = 1 if topology == "hub_and_spoke" else 3  # Default depth

    async with async_playwright() as p:
        browser, context = await util.get_stealth_context(p)

        while queue and len(found_urls) < max_pages:
            current_url, current_depth = queue.popleft()

            # Normalize for visited check
            visit_url = current_url
            if ignore_queries:
                visit_url = visit_url.split("?")[0]

            if visit_url in visited or current_depth > depth_limit:
                continue

            # Scope Check
            if scope == "subdomain" and urlparse(current_url).netloc != start_domain:
                continue
            if scope == "domain" and start_domain not in urlparse(current_url).netloc:
                continue
            # (Add 'path' scope logic if needed)

            # Robots.txt Check
            if not await util.is_allowed_by_robots(current_url):
                continue

            visited.add(visit_url)
            found_urls.add(current_url)

            if current_depth < depth_limit:
                try:
                    page = await context.new_page()
                    await util.apply_stealth(page)
                    await page.goto(
                        current_url, wait_until="domcontentloaded", timeout=10000
                    )

                    links = []
                    if topology == "linear":
                        # Heuristic for next/prev
                        links = await page.eval_on_selector_all(
                            "a[rel='next'], a:text('Next'), a:text('Previous')",
                            "elements => elements.map(e => e.href)",
                        )
                    elif topology == "sidebar":
                        # Heuristic for sidebar
                        links = await page.eval_on_selector_all(
                            "aside a, .sidebar a, nav a",
                            "elements => elements.map(e => e.href)",
                        )
                    else:
                        links = await page.eval_on_selector_all(
                            "a", "elements => elements.map(e => e.href)"
                        )

                    await page.close()

                    for link in links:
                        link = link.split("#")[0]
                        if ignore_queries:
                            link = link.split("?")[0]

                        if link.startswith("http"):
                            if (
                                scope == "subdomain"
                                and urlparse(link).netloc == start_domain
                            ):
                                queue.append((link, current_depth + 1))
                            elif (
                                scope == "domain"
                                and start_domain in urlparse(link).netloc
                            ):
                                queue.append((link, current_depth + 1))

                except Exception as e:
                    print(f"Error crawling {current_url}: {e}")

        await browser.close()

    return list(found_urls)


async def extract_content(
    url: str, click_selectors: list[str] = None, screenshot: bool = False
) -> dict:
    """
    Extracts clean, readable content from a webpage in Markdown format.

    Downloads and processes webpage content with automatic HTML cleaning,
    markdown conversion, and support for dynamic content. Can handle
    PDFs and JSON responses.

    Args:
        url (str): URL of the webpage to extract content from.
        click_selectors (list[str], optional): CSS selectors to click before extraction.
            Useful for revealing hidden content, accepting cookies, etc.
            Example: ["#accept-cookies", ".show-more-button"]
        screenshot (bool, optional): Capture page screenshot. Defaults to False.

    Returns:
        dict: Extracted content and metadata:
            - markdown (str): Page content in Markdown format
            - screenshot (str | None): Hex-encoded PNG screenshot if requested
            - metadata (dict): Page metadata
                - title (str): Page title
                - url (str): Final URL after redirects
                - type (str): Content type ("html", "pdf", "json")
            - error (str): Error message if extraction failed (optional)

    Example:
        >>> # Basic extraction
        >>> result = await extract_content("https://example.com")
        >>> print(result['metadata']['title'])
        >>> print(result['markdown'][:500])

        >>> # Handle dynamic content
        >>> result = await extract_content(
        ...     "https://example.com/article",
        ...     click_selectors=["#show-full-article"],
        ...     screenshot=True
        ... )

    Note:
        - Automatically detects and handles PDF/JSON content types
        - Uses readability algorithm to extract main content
        - Removes ads, navigation, and boilerplate
        - Auto-scrolls page to trigger lazy-loaded content
        - Waits for network idle before extraction
        - Uses stealth mode to avoid bot detection
        - Click selectors executed with 2s timeout each
        - Timeout: 30 seconds for page load
    """
    result = {"markdown": None, "screenshot": None, "metadata": {}}

    # Basic Content-Type check (HEAD request)
    async with httpx.AsyncClient() as client:
        try:
            head = await client.head(url, follow_redirects=True, timeout=5)
            content_type = head.headers.get("Content-Type", "").lower()

            if "application/pdf" in content_type:
                result["markdown"] = "[PDF Content - Extraction not implemented yet]"
                result["metadata"]["type"] = "pdf"
                return result
            elif "application/json" in content_type:
                resp = await client.get(url)
                result["markdown"] = (
                    f"```json\n{json.dumps(resp.json(), indent=2)}\n```"
                )
                result["metadata"]["type"] = "json"
                return result
        except Exception:
            pass

    async with async_playwright() as p:
        browser, context = await util.get_stealth_context(p)
        page = await context.new_page()
        await util.apply_stealth(page)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Handle Clicks
            if click_selectors:
                for selector in click_selectors:
                    try:
                        await page.click(selector, timeout=2000)
                        await page.wait_for_load_state("networkidle", timeout=2000)
                    except Exception:
                        pass  # Selector might not exist or be clickable

            await util.auto_scroll(page)

            if screenshot:
                result["screenshot"] = (
                    await page.screenshot(type="png")
                ).hex()  # Returning hex for simplicity in text output

            content = await page.content()
            cleaned_html = util.clean_html(content)
            result["markdown"] = util.convert_to_markdown(cleaned_html)
            result["metadata"]["title"] = await page.title()
            result["metadata"]["url"] = page.url

        except Exception as e:
            result["error"] = str(e)
        finally:
            await browser.close()

    return result


if __name__ == "__main__":
    import asyncio

    # Test inspect_site
    async def main():
        print("Inspecting example.com...")
        result = await inspect_site(
            "https://developer.atlassian.com/cloud/jira/platform/rest/v3"
        )
        print(json.dumps(result, indent=2))

    asyncio.run(main())
