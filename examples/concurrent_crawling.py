"""
Example demonstrating concurrent crawling with the async web crawler
"""

import asyncio
import tool
import time


async def crawl_single():
    """Crawl sites sequentially"""
    urls = ["https://example.com", "https://example.org", "https://example.net"]

    print("🔄 Sequential crawling...")
    start = time.time()

    results = []
    for url in urls:
        result = await tool.extract_content(url)
        results.append(result)
        print(f"  ✓ Crawled {url}")

    elapsed = time.time() - start
    print(f"⏱️  Sequential time: {elapsed:.2f}s\n")
    return results


async def crawl_concurrent():
    """Crawl sites concurrently"""
    urls = ["https://example.com", "https://example.org", "https://example.net"]

    print("🚀 Concurrent crawling...")
    start = time.time()

    # Fetch all URLs concurrently!
    results = await asyncio.gather(*[tool.extract_content(url) for url in urls])

    elapsed = time.time() - start
    print(f"  ✓ Crawled all {len(urls)} sites concurrently")
    print(f"⏱️  Concurrent time: {elapsed:.2f}s\n")
    return results


async def main():
    print("=" * 60)
    print("Async Web Crawler - Concurrent Execution Demo")
    print("=" * 60 + "\n")

    # Sequential
    seq_results = await crawl_single()

    # Concurrent
    conc_results = await crawl_concurrent()

    print("📊 Results:")
    print(f"   Sequential: {len(seq_results)} pages")
    print(f"   Concurrent: {len(conc_results)} pages")
    print("\n✅ Concurrent execution is much faster!")


if __name__ == "__main__":
    asyncio.run(main())
