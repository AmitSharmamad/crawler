import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import util


class TestUtil:
    def test_clean_html(self):
        html = "<html><body><nav>Menu</nav><div id='content'>Main Content</div><footer>Footer</footer></body></html>"
        cleaned = util.clean_html(html)
        assert "Main Content" in cleaned
        # Readability might keep some structure, but should remove nav/footer if clear
        # This is a loose test as readability behavior varies

    def test_convert_to_markdown(self):
        html = "<h1>Title</h1><p>Text</p>"
        md = util.convert_to_markdown(html)
        # markdownify defaults to Setext headers (Underlined) for H1/H2
        assert "Title\n=====" in md or "# Title" in md
        assert "Text" in md

    @pytest.mark.asyncio
    async def test_get_sitemap_urls(self):
        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock robots.txt
            mock_robots = MagicMock()
            mock_robots.status_code = 200
            mock_robots.text = "Sitemap: https://example.com/sitemap_index.xml"

            # Mock sitemap index
            mock_index = MagicMock()
            mock_index.status_code = 200
            mock_index.content = b"""
            <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <sitemap>
                    <loc>https://example.com/sitemap1.xml</loc>
                </sitemap>
            </sitemapindex>
            """

            # Mock sitemap 1
            mock_sitemap1 = MagicMock()
            mock_sitemap1.status_code = 200
            mock_sitemap1.content = b"""
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url>
                    <loc>https://example.com/page1</loc>
                </url>
            </urlset>
            """

            mock_client.get = AsyncMock(
                side_effect=[mock_robots, mock_index, mock_sitemap1]
            )

            urls = await util.get_sitemap_urls("https://example.com", "example.com")
            assert "https://example.com/page1" in urls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
