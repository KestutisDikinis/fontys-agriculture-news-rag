from app.scraper import parse_feed_xml
from app.sources import Source


RSS = """
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>New pesticide rule applies from 2026-03-15</title>
      <link>https://example.test/rule</link>
      <description><![CDATA[Farmers must comply with the new rule.]]></description>
      <pubDate>Mon, 01 Jan 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

ATOM = """
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Draft fertiliser proposal published</title>
    <link href="https://example.test/proposal" />
    <summary>Consultation is open.</summary>
    <updated>2026-01-02T10:00:00Z</updated>
  </entry>
</feed>
"""


def test_parse_rss_feed():
    source = Source("test", "Test", "https://example.test/rss", "EU")
    items = parse_feed_xml(source, RSS)
    assert len(items) == 1
    assert items[0].title.startswith("New pesticide")
    assert items[0].url == "https://example.test/rule"
    assert items[0].summary == "Farmers must comply with the new rule."


def test_parse_atom_feed():
    source = Source("test", "Test", "https://example.test/atom", "EU")
    items = parse_feed_xml(source, ATOM)
    assert len(items) == 1
    assert items[0].title == "Draft fertiliser proposal published"
    assert items[0].url == "https://example.test/proposal"
