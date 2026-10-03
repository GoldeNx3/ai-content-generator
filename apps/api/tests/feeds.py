# Rola pliku: Przykładowe RSS/Atom zapisane jako tekst: testy parsera używają tych danych zamiast
# pobierać prawdziwe feedy.

RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example</title>
    <link>https://example.com</link>
    <description>Example feed</description>
    <item>
      <title>OpenAI releases a new model</title>
      <link>https://example.com/posts/1</link>
      <description>&lt;p&gt;Big &lt;b&gt;release&lt;/b&gt; today.&lt;/p&gt;</description>
      <pubDate>Wed, 01 Oct 2025 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Entry without date and summary</title>
      <link>https://example.com/posts/2</link>
    </item>
    <item>
      <title>Duplicate inside the same feed</title>
      <link>https://example.com/posts/1</link>
    </item>
  </channel>
</rss>
"""

ATOM_FEED = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Example</title>
  <id>urn:example</id>
  <updated>2025-10-01T12:00:00Z</updated>
  <entry>
    <title>Anthropic adds a feature</title>
    <link href="https://example.com/atom/1"/>
    <id>urn:example:1</id>
    <updated>2025-10-01T12:00:00Z</updated>
    <summary>Short atom summary</summary>
  </entry>
</feed>
"""

BROKEN_FEED = b"<html><body>this is <not a feed"
