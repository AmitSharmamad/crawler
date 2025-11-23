"""
LangChain Agent Integration Example

This example shows how to integrate the async web crawler tools with LangChain agents.
The crawler tools are wrapped as LangChain tools so agents can use them for web research.
"""

import asyncio
from typing import Optional
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
import sys
import os

# Add parent directory to path to import our crawler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tool as crawler


# Wrapper functions to make async crawler tools synchronous for LangChain
def inspect_website(url: str) -> str:
    """
    Inspect a website to understand its structure and metadata.
    Returns metadata, navigation links, and sitemap summary.

    Args:
        url: The website URL to inspect
    """
    result = asyncio.run(crawler.inspect_site(url))

    # Format result for agent consumption
    output = f"Website: {url}\n\n"
    output += f"Title: {result['metadata'].get('title', 'N/A')}\n"
    output += f"Description: {result['metadata'].get('description', 'N/A')}\n\n"

    output += "Navigation:\n"
    for section, links in result["navigation"].items():
        if links:
            output += f"  {section.title()}: {len(links)} links\n"
            for link in links[:3]:  # Show first 3
                output += f"    - {link['text']}: {link['url']}\n"

    output += (
        f"\nSitemap: {result['sitemap_summary'].get('total_urls', 0)} total URLs\n"
    )

    return output


def discover_relevant_links(url: str, keywords: str) -> str:
    """
    Find links on a webpage matching specific keywords.
    Returns ranked links by relevance score.

    Args:
        url: The webpage URL to search
        keywords: Comma-separated keywords to search for
    """
    keyword_list = [k.strip() for k in keywords.split(",")]
    results = asyncio.run(crawler.discover_links(url, keyword_list))

    output = f"Found {len(results)} relevant links for keywords: {keywords}\n\n"
    for i, link in enumerate(results[:5], 1):  # Top 5 results
        output += f"{i}. {link['text']} (score: {link['score']})\n"
        output += f"   URL: {link['url']}\n"
        output += f"   Matches: {', '.join(link['matches'])}\n\n"

    return output


def extract_page_content(url: str) -> str:
    """
    Extract clean content from a webpage as markdown.
    Returns the page title and markdown content.

    Args:
        url: The webpage URL to extract content from
    """
    result = asyncio.run(crawler.extract_content(url))

    if "error" in result:
        return f"Error extracting content: {result['error']}"

    output = f"Title: {result['metadata'].get('title', 'N/A')}\n"
    output += f"URL: {result['metadata'].get('url', url)}\n\n"
    output += "Content:\n"
    output += result["markdown"][:2000]  # Limit to 2000 chars

    if len(result["markdown"]) > 2000:
        output += f"\n\n... (truncated, total {len(result['markdown'])} characters)"

    return output


def crawl_website_links(url: str, max_pages: int = 10) -> str:
    """
    Crawl a website and extract all internal links using BFS.

    Args:
        url: The starting URL to crawl
        max_pages: Maximum number of pages to crawl (default 10)
    """
    try:
        max_pages_int = int(max_pages)
    except:
        max_pages_int = 10

    results = asyncio.run(
        crawler.extract_links(
            url, topology="mesh", scope="subdomain", max_pages=max_pages_int
        )
    )

    output = f"Crawled {len(results)} pages from {url}\n\n"
    output += "Discovered URLs:\n"
    for i, page_url in enumerate(results[:20], 1):  # Show first 20
        output += f"{i}. {page_url}\n"

    if len(results) > 20:
        output += f"\n... and {len(results) - 20} more URLs"

    return output


# Create LangChain tools
langchain_tools = [
    Tool(
        name="inspect_website",
        description="Inspect a website to understand its structure, metadata, navigation, and sitemap. Use this first when analyzing a new website.",
        func=inspect_website,
    ),
    Tool(
        name="discover_relevant_links",
        description="Find links on a webpage matching specific keywords. Useful for finding relevant content sections. Input should be URL and comma-separated keywords.",
        func=lambda inp: discover_relevant_links(*inp.split("|", 1))
        if "|" in inp
        else "Error: Format as 'URL|keywords'",
    ),
    Tool(
        name="extract_page_content",
        description="Extract clean markdown content from a webpage. Use this to read the actual content of a page.",
        func=extract_page_content,
    ),
    Tool(
        name="crawl_website_links",
        description="Crawl a website and discover all internal links. Use this to map out a website's structure. Input should be URL.",
        func=crawl_website_links,
    ),
]


async def main():
    """
    Example: Using the crawler tools with a LangChain agent
    """

    # Set up the LLM (requires OPENAI_API_KEY environment variable)
    llm = ChatOpenAI(model="gpt-4", temperature=0)

    # Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a web research assistant with access to powerful web crawling tools.
        
        You can:
        - Inspect websites to understand their structure
        - Find relevant links based on keywords
        - Extract and read page content
        - Crawl websites to discover all pages
        
        Use these tools strategically to gather comprehensive information about websites.
        Always start by inspecting a website before diving deeper.""",
            ),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    # Create the agent
    agent = create_openai_functions_agent(llm, langchain_tools, prompt)
    agent_executor = AgentExecutor(
        agent=agent, tools=langchain_tools, verbose=True, max_iterations=5
    )

    # Example query
    print("=" * 70)
    print("LangChain Agent with Web Crawler Tools")
    print("=" * 70)

    result = await agent_executor.ainvoke(
        {
            "input": """Analyze the website https://example.com. 
        First inspect it, then extract its main content and summarize what the website is about."""
        }
    )

    print("\n" + "=" * 70)
    print("Agent Response:")
    print("=" * 70)
    print(result["output"])


if __name__ == "__main__":
    # Note: Requires OPENAI_API_KEY environment variable
    # export OPENAI_API_KEY='your-key-here'

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        print("\nTo run this example:")
        print("1. Install: pip install langchain langchain-openai")
        print("2. Set: export OPENAI_API_KEY='your-key-here'")
        print("3. Run: python examples/langchain_agent.py")
