"""
Basic Usage Examples

Simple examples showing how to use the async web crawler tools directly.
"""

import asyncio
import tool


async def example_inspect_site():
    """Example: Inspect a website to understand its structure"""
    print("=" * 60)
    print("Example 1: Inspect Website")
    print("=" * 60)

    result = await tool.inspect_site("https://example.com")

    print(f"\n📋 Title: {result['metadata']['title']}")
    print(f"📝 Description: {result['metadata']['description']}")

    print(f"\n🧭 Navigation:")
    for section, links in result["navigation"].items():
        if links:
            print(f"  {section.title()}: {len(links)} links")

    print(f"\n🗺️  Sitemap: {result['sitemap_summary']['total_urls']} total URLs")


async def example_discover_links():
    """Example: Find relevant links based on keywords"""
    print("\n" + "=" * 60)
    print("Example 2: Discover Relevant Links")
    print("=" * 60)

    results = await tool.discover_links(
        url="https://python.org", keywords=["documentation", "tutorial", "download"]
    )

    print(f"\nFound {len(results)} relevant links:\n")
    for i, link in enumerate(results[:5], 1):
        print(f"{i}. {link['text']} (score: {link['score']})")
        print(f"   {link['url']}")
        print(f"   Matches: {', '.join(link['matches'])}\n")


async def example_extract_content():
    """Example: Extract clean content from a webpage"""
    print("=" * 60)
    print("Example 3: Extract Page Content")
    print("=" * 60)

    result = await tool.extract_content("https://example.com")

    print(f"\n📄 Title: {result['metadata']['title']}")
    print(f"🔗 URL: {result['metadata']['url']}")
    print(f"\n📝 Content (first 500 chars):")
    print("-" * 60)
    print(result["markdown"][:500])
    print("...")


async def example_crawl_links():
    """Example: Crawl a website to discover all pages"""
    print("\n" + "=" * 60)
    print("Example 4: Crawl Website")
    print("=" * 60)

    # Crawl small number of pages for demo
    urls = await tool.extract_links(
        url="https://example.com", topology="mesh", max_pages=5
    )

    print(f"\nDiscovered {len(urls)} pages:\n")
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")


async def example_concurrent_extraction():
    """Example: Extract content from multiple pages concurrently"""
    print("\n" + "=" * 60)
    print("Example 5: Concurrent Content Extraction")
    print("=" * 60)

    urls = ["https://example.com", "https://example.org", "https://example.net"]

    print(f"\nExtracting content from {len(urls)} sites concurrently...\n")

    # Fetch all concurrently!
    results = await asyncio.gather(*[tool.extract_content(url) for url in urls])

    for result in results:
        title = result["metadata"].get("title", "N/A")
        url = result["metadata"].get("url", "N/A")
        print(f"✓ {title}")
        print(f"  {url}\n")


async def main():
    """Run all examples"""
    print("\n" * 2)
    print("🕷️" * 30)
    print(" " * 20 + "Async Web Crawler Examples")
    print("🕷️" * 30)
    print()

    # Run examples
    await example_inspect_site()
    await example_extract_content()
    # await example_discover_links()  # Commented out - requires live site
    # await example_crawl_links()  # Commented out - requires network
    await example_concurrent_extraction()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
