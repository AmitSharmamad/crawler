# Web Crawler

An advanced async web crawler toolkit with powerful scraping capabilities and AI agent integration.

## 🚀 Features

- **Async/Await Architecture** - Built with `asyncio` for high-performance concurrent crawling
- **Comprehensive Tools** - Inspect, discover, extract, and crawl websites
- **Stealth Mode** - Built-in stealth capabilities to avoid detection
- **Clean Content** - Automatic HTML cleaning and markdown conversion
- **AI Agent Ready** - Easy integration with LangChain and CrewAI
- **Flexible Scoping** - Control crawl scope (domain, subdomain, path)
- **Smart Discovery** - Keyword-based link discovery with relevance scoring

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd crawler

# Install dependencies with uv
uv sync

# Install Playwright browsers
playwright install chromium
```

## 🔧 Core Tools

### `inspect_site(url)`
Analyze website structure, metadata, navigation, and sitemap.

```python
result = await tool.inspect_site("https://example.com")
print(result['metadata']['title'])
print(result['sitemap_summary']['total_urls'])
```

### `discover_links(url, keywords, scope="domain")`
Find relevant links based on keywords with relevance scoring.

```python
links = await tool.discover_links(
    url="https://example.com",
    keywords=["documentation", "api", "tutorial"]
)
```

### `extract_links(url, topology="mesh", scope="subdomain", max_pages=50)`
Crawl website to discover all internal pages.

```python
urls = await tool.extract_links(
    url="https://example.com",
    topology="mesh",  # BFS crawling
    max_pages=100
)
```

### `extract_content(url, click_selectors=None, screenshot=False)`
Extract clean markdown content from any webpage.

```python
content = await tool.extract_content("https://example.com")
print(content['markdown'])
```

## 🎯 Quick Start

```python
import asyncio
import tool

async def main():
    # Extract content from a page
    result = await tool.extract_content("https://example.com")
    print(f"Title: {result['metadata']['title']}")
    print(f"Content:\n{result['markdown'][:500]}")

asyncio.run(main())
```

## 🚀 Concurrent Crawling

```python
import asyncio
import tool

async def crawl_multiple():
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net"
    ]
    
    # Fetch all concurrently for maximum speed
    results = await asyncio.gather(*[
        tool.extract_content(url) for url in urls
    ])
    
    return results

results = asyncio.run(crawl_multiple())
```

## 🤖 AI Agent Integration

### LangChain

```python
from langchain_core.tools import Tool
import asyncio
import tool

langchain_tools = [
    Tool(
        name="extract_content",
        description="Extract content from a webpage",
        func=lambda url: asyncio.run(tool.extract_content(url))
    )
]

# Use with any LangChain agent
```

See [examples/langchain_agent.py](./examples/langchain_agent.py) for complete example.

### CrewAI

```python
from crewai.tools import BaseTool
import asyncio
import tool

class CrawlerTool(BaseTool):
    name: str = "Web Crawler"
    description: str = "Crawls and extracts web content"
    
    def _run(self, url: str) -> str:
        result = asyncio.run(tool.extract_content(url))
        return result['markdown']

# Use with CrewAI agents
```

See [examples/crewai_agents.py](./examples/crewai_agents.py) for complete multi-agent example.

## 📁 Project Structure

```
crawler/
├── tool.py              # Main crawler tools
├── util.py              # Utility functions
├── main.py              # Simple example
├── tests/               # Test suite
│   ├── test_tool.py
│   ├── test_util.py
│   └── test_async.py
├── examples/            # Usage examples
│   ├── basic_usage.py
│   ├── concurrent_crawling.py
│   ├── langchain_agent.py
│   └── crewai_agents.py
└── pyproject.toml       # Dependencies
```

## 🧪 Testing

```bash
# Run all tests
make test
# or
pytest tests/ -v

# Run specific test file
pytest tests/test_tool.py -v
```

## 📚 Examples

All examples are in the [examples/](./examples/) directory:

- **[basic_usage.py](./examples/basic_usage.py)** - Simple usage of all tools
- **[concurrent_crawling.py](./examples/concurrent_crawling.py)** - Performance comparison
- **[langchain_agent.py](./examples/langchain_agent.py)** - LangChain integration
- **[crewai_agents.py](./examples/crewai_agents.py)** - Multi-agent CrewAI system

Run any example:
```bash
python examples/basic_usage.py
```

## 🛠️ Development

```bash
# Run main demo
make run

# Run tests
make test

# Format code
black .

# Type checking
mypy tool.py util.py
```

## 📝 API Reference

### Tool Functions

#### `async def inspect_site(url: str) -> dict`
**Returns:**
```python
{
    "metadata": {
        "title": str,
        "description": str,
        "keywords": str
    },
    "navigation": {
        "header": [{"text": str, "url": str}],
        "nav": [...],
        "footer": [...]
    },
    "sitemap_summary": {
        "total_urls": int,
        "structure_hint": dict
    }
}
```

#### `async def discover_links(url: str, keywords: list[str], scope: str = "domain") -> list[dict]`
**Returns:**
```python
[
    {
        "url": str,
        "text": str,
        "score": int,
        "matches": [str]
    }
]
```

#### `async def extract_links(url: str, topology: str = "mesh", scope: str = "subdomain", max_pages: int = 50) -> list[str]`
**Parameters:**
- `topology`: "mesh" (BFS), "linear", "hub_and_spoke", "sidebar"
- `scope`: "subdomain", "domain", "path"

**Returns:** List of discovered URLs

#### `async def extract_content(url: str, click_selectors: list[str] = None, screenshot: bool = False) -> dict`
**Returns:**
```python
{
    "markdown": str,
    "screenshot": str | None,
    "metadata": {
        "title": str,
        "url": str,
        "type": str  # html, pdf, json
    }
}
```

## 🔒 Features

- ✅ Async/await for concurrent operations
- ✅ Playwright stealth mode
- ✅ Automatic HTML cleaning
- ✅ Markdown conversion
- ✅ Sitemap parsing
- ✅ Robots.txt compliance
- ✅ Keyword-based discovery
- ✅ Multiple crawl topologies
- ✅ Scope control (domain/subdomain/path)
- ✅ Screenshot support
- ✅ Dynamic content handling
- ✅ PDF/JSON detection

## 📄 License

MIT License - See [LICENSE](./LICENSE)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📧 Support

For issues and questions, please open a GitHub issue.