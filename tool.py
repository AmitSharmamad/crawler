from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from collections import deque
import util
import json
import httpx


async def inspect_site(url: str) -> dict:
    """
    Inspects the website to understand its structure and metadata.
    Returns:
        - metadata: Title, description, keywords.
        - navigation: Links found in header, nav, and footer.
        - sitemap_summary: Summary of sitemap contents (if available).
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
    Finds links matching specific keywords in URL or anchor text.
    Returns a list of objects: {url, text, score, context}.
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
    Extracts links based on topology and scope.
    Topology: 'mesh' (BFS), 'linear' (next/prev), 'hub_and_spoke' (depth 1), 'sidebar'.
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
    Extracts content from a URL.
    - Handles click_selectors to reveal content.
    - Returns Markdown, Screenshot (optional), and Metadata.
    - Checks Content-Type for PDF/JSON (basic implementation).
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
