"""
async-web-crawler: Advanced async web crawler with AI agent integration

A powerful async web crawling toolkit that provides:
- Site inspection and structure analysis
- Keyword-based link discovery
- Flexible crawling strategies (mesh, linear, hub-and-spoke, sidebar)
- Clean content extraction in Markdown format
- AI agent integration (LangChain, CrewAI)
"""

__version__ = "0.1.0"
__author__ = "Madgula Amit"
__license__ = "MIT"

# Import main tools for easy access
from tool import (
    inspect_site,
    discover_links,
    extract_links,
    extract_content,
)

# Import utility functions that might be useful
from util import (
    get_stealth_context,
    apply_stealth,
    auto_scroll,
    clean_html,
    convert_to_markdown,
    get_sitemap_urls,
    is_allowed_by_robots,
)

__all__ = [
    # Main tools
    "inspect_site",
    "discover_links",
    "extract_links",
    "extract_content",
    # Utilities
    "get_stealth_context",
    "apply_stealth",
    "auto_scroll",
    "clean_html",
    "convert_to_markdown",
    "get_sitemap_urls",
    "is_allowed_by_robots",
    # Metadata
    "__version__",
    "__author__",
    "__license__",
]
