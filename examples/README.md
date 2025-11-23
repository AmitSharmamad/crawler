# Examples

This directory contains examples demonstrating how to use the async web crawler tools in various scenarios.

## 📁 Files

### [basic_usage.py](./basic_usage.py)
**Basic Usage Examples** - Simple examples showing how to use each crawler function directly.

```bash
python examples/basic_usage.py
```

Examples include:
- Inspecting website structure
- Extracting page content
- Discovering relevant links
- Crawling websites
- Concurrent content extraction

### [concurrent_crawling.py](./concurrent_crawling.py)
**Performance Comparison** - Demonstrates the performance benefits of async/concurrent crawling vs sequential.

```bash
python examples/concurrent_crawling.py
```

Shows:
- Sequential vs concurrent crawling speed
- Performance metrics
- Best practices for concurrent operations

### [langchain_agent.py](./langchain_agent.py)
**LangChain Integration** - Shows how to integrate crawler tools with LangChain agents.

```bash
# Setup
pip install langchain langchain-openai
export OPENAI_API_KEY='your-key-here'

# Run
python examples/langchain_agent.py
```

Features:
- Custom LangChain tools wrapping crawler functions
- Agent-driven web research
- Autonomous website analysis
- Strategic tool usage by AI agent

### [crewai_agents.py](./crewai_agents.py)
**CrewAI Multi-Agent System** - Demonstrates specialized agents working together for comprehensive website research.

```bash
# Setup
pip install crewai crewai-tools

# Run
python examples/crewai_agents.py
```

Features:
- Multiple specialized agents (Analyzer, Researcher, Compiler)
- Custom CrewAI tools for web crawling
- Collaborative multi-agent workflow
- Comprehensive research reports

## 🚀 Quick Start

### Basic Usage
```python
import asyncio
import tool

async def main():
    # Inspect a website
    result = await tool.inspect_site("https://example.com")
    print(result['metadata']['title'])
    
    # Extract content
    content = await tool.extract_content("https://example.com")
    print(content['markdown'])

asyncio.run(main())
```

### Concurrent Crawling
```python
import asyncio
import tool

async def crawl_multiple():
    urls = ["https://site1.com", "https://site2.com", "https://site3.com"]
    
    # Fetch all concurrently
    results = await asyncio.gather(*[
        tool.extract_content(url) for url in urls
    ])
    
    return results

results = asyncio.run(crawl_multiple())
```

## 🤖 Agent Integration Patterns

### LangChain Pattern
```python
from langchain_core.tools import Tool

def make_tool(name, description, func):
    return Tool(name=name, description=description, func=func)

tools = [
    make_tool("inspect", "Inspect website", 
              lambda url: asyncio.run(tool.inspect_site(url))),
    make_tool("extract", "Extract content", 
              lambda url: asyncio.run(tool.extract_content(url)))
]
```

### CrewAI Pattern
```python
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class InspectInput(BaseModel):
    url: str = Field(..., description="URL to inspect")

class InspectTool(BaseTool):
    name: str = "Website Inspector"
    description: str = "Inspects website structure"
    args_schema: Type[BaseModel] = InspectInput
    
    def _run(self, url: str) -> str:
        result = asyncio.run(tool.inspect_site(url))
        return format_result(result)
```

## 📊 Example Output

### Website Inspection
```
Website: https://example.com

Title: Example Domain
Description: Example website

Navigation:
  Header: 0 links
  Nav: 1 links
    - Learn more: https://example.com/docs
  Footer: 3 links
    - Privacy: https://example.com/privacy

Sitemap: 150 total URLs
```

### Content Extraction
```
Title: Example Domain
URL: https://example.com

Content:
================================================================================
Example Domain
==============

This domain is for use in illustrative examples in documents.
You may use this domain in literature without prior coordination or asking...
```

## 💡 Tips

1. **Start with inspection** - Always inspect a site first to understand its structure
2. **Use keywords wisely** - Be specific with keywords for better link discovery
3. **Respect rate limits** - Use concurrent crawling responsibly
4. **Filter by scope** - Use `scope="subdomain"` to stay within a single domain
5. **Handle errors** - Always check for `'error'` key in results

## 🔧 Requirements

**Core:**
- Python 3.13+
- All dependencies in `pyproject.toml`

**Agent Integration:**
- LangChain: `pip install langchain langchain-openai`
- CrewAI: `pip install crewai crewai-tools`
- OpenAI API key for LLM features

## 📚 Learn More

- See [../README.md](../README.md) for full project documentation
- Check [../tool.py](../tool.py) for all available functions
- Review [../tests/](../tests/) for additional usage examples
