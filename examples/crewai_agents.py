"""
CrewAI Agent Integration Example

This example shows how to integrate the async web crawler tools with CrewAI agents.
Multiple specialized agents work together to comprehensively analyze websites.
"""

import asyncio
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import sys
import os

# Add parent directory to path to import our crawler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tool as crawler


# Custom CrewAI Tools using our async crawler


class WebsiteInspectorInput(BaseModel):
    """Input schema for WebsiteInspectorTool"""

    url: str = Field(..., description="The website URL to inspect")


class WebsiteInspectorTool(BaseTool):
    name: str = "Website Inspector"
    description: str = """Inspects a website to understand its structure, metadata, 
    navigation menu, and sitemap. Returns comprehensive information about the website's organization."""
    args_schema: Type[BaseModel] = WebsiteInspectorInput

    def _run(self, url: str) -> str:
        result = asyncio.run(crawler.inspect_site(url))

        output = f"🔍 Website Inspection Report for {url}\n\n"
        output += f"📋 Metadata:\n"
        output += f"  • Title: {result['metadata'].get('title', 'N/A')}\n"
        output += f"  • Description: {result['metadata'].get('description', 'N/A')}\n"
        output += f"  • Keywords: {result['metadata'].get('keywords', 'N/A')}\n\n"

        output += f"🧭 Navigation Structure:\n"
        for section, links in result["navigation"].items():
            if links:
                output += f"  {section.title()} ({len(links)} links):\n"
                for link in links[:5]:
                    output += f"    • {link['text']}\n"

        output += f"\n📊 Sitemap Summary:\n"
        output += f"  • Total URLs: {result['sitemap_summary'].get('total_urls', 0)}\n"
        structure = result["sitemap_summary"].get("structure_hint", {})
        if structure:
            output += f"  • Main sections: {', '.join(list(structure.keys())[:5])}\n"

        return output


class ContentExtractorInput(BaseModel):
    """Input schema for ContentExtractorTool"""

    url: str = Field(..., description="The webpage URL to extract content from")


class ContentExtractorTool(BaseTool):
    name: str = "Content Extractor"
    description: str = """Extracts clean markdown content from a webpage. 
    Returns the page title and full content in markdown format."""
    args_schema: Type[BaseModel] = ContentExtractorInput

    def _run(self, url: str) -> str:
        result = asyncio.run(crawler.extract_content(url))

        if "error" in result:
            return f"❌ Error extracting content: {result['error']}"

        output = f"📄 Content from {url}\n\n"
        output += f"Title: {result['metadata'].get('title', 'N/A')}\n"
        output += f"\nContent:\n{'-' * 50}\n"
        output += result["markdown"][:3000]  # First 3000 chars

        if len(result["markdown"]) > 3000:
            output += f"\n\n... (Content continues, total {len(result['markdown'])} characters)"

        return output


class LinkDiscoveryInput(BaseModel):
    """Input schema for LinkDiscoveryTool"""

    url: str = Field(..., description="The webpage URL to search")
    keywords: str = Field(..., description="Comma-separated keywords to search for")


class LinkDiscoveryTool(BaseTool):
    name: str = "Link Discovery"
    description: str = """Discovers relevant links on a webpage based on keywords. 
    Returns ranked links by relevance score."""
    args_schema: Type[BaseModel] = LinkDiscoveryInput

    def _run(self, url: str, keywords: str) -> str:
        keyword_list = [k.strip() for k in keywords.split(",")]
        results = asyncio.run(crawler.discover_links(url, keyword_list))

        output = f"🔗 Discovered {len(results)} relevant links for: {keywords}\n\n"

        for i, link in enumerate(results[:10], 1):
            output += f"{i}. {link['text']} (Score: {link['score']})\n"
            output += f"   URL: {link['url']}\n"
            output += f"   Matches: {', '.join(link['matches'])}\n\n"

        return output


class SiteCrawlerInput(BaseModel):
    """Input schema for SiteCrawlerTool"""

    url: str = Field(..., description="The starting URL to crawl")
    max_pages: int = Field(default=20, description="Maximum pages to crawl")


class SiteCrawlerTool(BaseTool):
    name: str = "Site Crawler"
    description: str = """Crawls a website to discover all internal pages. 
    Uses breadth-first search to map the site structure."""
    args_schema: Type[BaseModel] = SiteCrawlerInput

    def _run(self, url: str, max_pages: int = 20) -> str:
        results = asyncio.run(
            crawler.extract_links(
                url, topology="mesh", scope="subdomain", max_pages=max_pages
            )
        )

        output = f"🕷️ Crawled {len(results)} pages from {url}\n\n"
        output += "Discovered pages:\n"

        for i, page_url in enumerate(results[:30], 1):
            output += f"{i}. {page_url}\n"

        if len(results) > 30:
            output += f"\n... and {len(results) - 30} more pages"

        return output


# Define specialized agents


def create_research_crew(website_url: str):
    """
    Creates a crew of specialized agents for comprehensive website research
    """

    # Tools
    inspector = WebsiteInspectorTool()
    extractor = ContentExtractorTool()
    discoverer = LinkDiscoveryTool()
    crawler = SiteCrawlerTool()

    # Agent 1: Website Analyzer
    analyzer_agent = Agent(
        role="Website Structure Analyst",
        goal=f"Analyze the structure and organization of {website_url}",
        backstory="""You are an expert at understanding website architecture. 
        You examine site structure, navigation, and organization to create 
        comprehensive overview reports.""",
        tools=[inspector, crawler],
        verbose=True,
        allow_delegation=False,
    )

    # Agent 2: Content Researcher
    content_agent = Agent(
        role="Content Research Specialist",
        goal=f"Extract and analyze the main content from {website_url}",
        backstory="""You specialize in extracting and understanding web content. 
        You can quickly identify key information and summarize website content.""",
        tools=[extractor, discoverer],
        verbose=True,
        allow_delegation=False,
    )

    # Agent 3: Report Compiler
    compiler_agent = Agent(
        role="Research Report Compiler",
        goal="Compile findings into a comprehensive research report",
        backstory="""You are skilled at synthesizing information from multiple 
        sources into clear, actionable reports. You organize findings logically 
        and highlight key insights.""",
        tools=[],
        verbose=True,
        allow_delegation=False,
    )

    # Tasks

    task1 = Task(
        description=f"""Analyze the structure of {website_url}:
        1. Inspect the website to understand its organization
        2. Crawl the site to discover all pages (max 15 pages)
        3. Document the navigation structure and main sections
        
        Provide a clear summary of the website's architecture.""",
        agent=analyzer_agent,
        expected_output="A detailed analysis of the website structure including navigation, sections, and page organization",
    )

    task2 = Task(
        description=f"""Research the content of {website_url}:
        1. Extract content from the main page
        2. Identify key topics and themes
        3. Discover relevant internal links using keywords from the content
        
        Summarize what the website is about and its main purpose.""",
        agent=content_agent,
        expected_output="A comprehensive summary of the website's content, purpose, and key topics",
    )

    task3 = Task(
        description="""Compile a comprehensive research report combining:
        1. Website structure analysis
        2. Content summary and purpose
        3. Key findings and insights
        4. Recommendations for further exploration
        
        Create a well-organized, actionable report.""",
        agent=compiler_agent,
        expected_output="A complete research report with structure analysis, content summary, and actionable insights",
        context=[task1, task2],
    )

    # Create the crew
    crew = Crew(
        agents=[analyzer_agent, content_agent, compiler_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
    )

    return crew


async def main():
    """
    Example: Using the crawler tools with CrewAI agents
    """

    print("=" * 70)
    print("CrewAI Multi-Agent Web Research System")
    print("=" * 70)
    print()

    # Target website to research
    website = "https://example.com"

    print(f"🎯 Target: {website}")
    print(f"🤖 Deploying specialized research crew...\n")

    # Create and run the crew
    crew = create_research_crew(website)
    result = crew.kickoff()

    print("\n" + "=" * 70)
    print("📊 Final Research Report")
    print("=" * 70)
    print(result)


if __name__ == "__main__":
    # Note: Requires CrewAI installation
    # pip install crewai crewai-tools

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        print("\nTo run this example:")
        print("1. Install: pip install crewai crewai-tools")
        print("2. Optional: Set OPENAI_API_KEY for better LLM")
        print("3. Run: python examples/crewai_agents.py")
