"""
Test async functionality with a simple integration test
"""

import pytest
import tool


@pytest.mark.asyncio
async def test_extract_content():
    """Test that extract_content works with a real website"""
    print("Testing extract_content...")
    result = await tool.extract_content("https://example.com")

    # Verify structure
    assert "metadata" in result
    assert "markdown" in result

    # Verify content
    assert result["metadata"]["title"] == "Example Domain"
    assert "Example Domain" in result["markdown"]
    assert len(result["markdown"]) > 0

    print(f"✓ Title: {result['metadata'].get('title')}")
    print(f"✓ Content length: {len(result['markdown'])} chars")
