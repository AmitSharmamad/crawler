import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import tool


class TestTool:
    @pytest.mark.asyncio
    @patch("tool.async_playwright")
    @patch("tool.util")
    async def test_inspect_site(self, mock_util, mock_playwright):
        # Setup util mocks
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_util.get_stealth_context = AsyncMock(
            return_value=(mock_browser, mock_context)
        )
        mock_util.apply_stealth = AsyncMock()
        mock_util.get_sitemap_urls = AsyncMock(return_value=[])

        # Setup playwright mocks
        mock_p = MagicMock()
        mock_playwright.return_value.__aenter__.return_value = mock_p
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Setup page mocks
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Site")

        # Mock meta description
        desc_locator = AsyncMock()
        desc_locator.get_attribute = AsyncMock(return_value="Test Description")

        # Mock keywords
        keywords_locator = AsyncMock()
        keywords_locator.get_attribute = AsyncMock(return_value="test,keywords")

        # Mock navigation
        nav_anchor = AsyncMock()
        nav_anchor.get_attribute = AsyncMock(return_value="/about")
        nav_anchor.inner_text = AsyncMock(return_value="About")

        nav_element = AsyncMock()
        nav_anchor_locator = AsyncMock()
        nav_anchor_locator.all = AsyncMock(return_value=[nav_anchor])
        nav_element.locator = MagicMock(return_value=nav_anchor_locator)

        nav_section_locator = AsyncMock()
        nav_section_locator.all = AsyncMock(return_value=[nav_element])

        locator_calls = []

        def locator_side_effect(selector):
            locator_calls.append(selector)
            if "description" in selector:
                return desc_locator
            elif "keywords" in selector:
                return keywords_locator
            else:
                # For header/nav/footer
                return nav_section_locator

        mock_page.locator = MagicMock(side_effect=locator_side_effect)

        result = await tool.inspect_site("https://example.com")

        assert result["metadata"]["title"] == "Test Site"
        assert result["navigation"]["header"][0]["text"] == "About"
        assert result["navigation"]["header"][0]["url"] == "https://example.com/about"

    @pytest.mark.asyncio
    @patch("tool.async_playwright")
    @patch("tool.util")
    async def test_discover_links(self, mock_util, mock_playwright):
        # Setup util mocks
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_util.get_stealth_context = AsyncMock(
            return_value=(mock_browser, mock_context)
        )
        mock_util.apply_stealth = AsyncMock()

        # Setup playwright mocks
        mock_p = MagicMock()
        mock_playwright.return_value.__aenter__.return_value = mock_p
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Setup page mocks
        mock_page.goto = AsyncMock()

        # Mock anchors
        mock_a1 = AsyncMock()
        mock_a1.get_attribute = AsyncMock(return_value="/docs/api")
        mock_a1.inner_text = AsyncMock(return_value="API Reference")

        mock_a2 = AsyncMock()
        mock_a2.get_attribute = AsyncMock(return_value="/blog/post")
        mock_a2.inner_text = AsyncMock(return_value="Blog Post")

        mock_locator = AsyncMock()
        mock_locator.all = AsyncMock(return_value=[mock_a1, mock_a2])
        mock_page.locator = MagicMock(return_value=mock_locator)

        results = await tool.discover_links("https://example.com", ["api"])

        assert len(results) == 1
        assert results[0]["url"] == "https://example.com/docs/api"
        assert results[0]["score"] == 15  # 5 for URL + 10 for text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
