#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" """

from unittest import TestCase
from pprint import pprint, pformat
from speedparser import parse


class UnixTimestampError(TestCase):
    def test_unix_timestamp_failure(self):
        """This tests for a bug where a non-existant timestamp is used to
        create a unix timestamp (from None) and throws an exception."""
        feed = '<?xml version="1.0" encoding="UTF-8"?> \n<rss version="2.0"\n\txmlns:content="http://purl.org/rss/1.0/modules/content/"\n\txmlns:wfw="http://wellformedweb.org/CommentAPI/"\n\txmlns:dc="http://purl.org/dc/elements/1.1/"\n\txmlns:atom="http://www.w3.org/2005/Atom"\n\txmlns:sy="http://purl.org/rss/1.0/modules/syndication/"\n\txmlns:slash="http://purl.org/rss/1.0/modules/slash/"\n\t> \n \n<channel>\n<title>betamax - Svpply</title> \n\t<link>http://svpply.com</link> \n\t<description>Svpply is a retail bookmarking and recommendation service.</description> \n\t<lastBuildDate>1323107774</lastBuildDate> \n\t<language>en</language> \n\t<sy:updatePeriod>hourly</sy:updatePeriod> \n\t<sy:updateFrequency>1</sy:updateFrequency> \n\t</channel> \n</rss>'
        result = parse(feed, unix_timestamp=True)
        self.assertTrue('bozo_exception' not in result, str(result))

class NonCleanedTitle(TestCase):
    def test_non_cleaned_title(self):
        """This tests for a bug where titles were not stripped of html despite
        a cleaner being supplied to speedparser."""
        from lxml.html.clean import Cleaner
        feed = '''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>scribble.yuyat.jp</title><link href="http://scribble.yuyat.jp/"/><link type="application/atom+xml" rel="self" href="http://scribble.yuyat.jp/atom.xml"/><updated>2012-01-08T18:34:39-08:00</updated><id>http://scribble.yuyat.jp/</id><author><name>Yuya Takeyama</name></author><entry><id>http://scribble.yuyat.jp/2012/01/07/this-is-just-a-scribble</id><link type="text/html" rel="alternate" href="http://scribble.yuyat.jp/2012/01/07/this-is-just-a-scribble.html"/><title>scribble 始めます &lt;script&gt;alert(1)&lt;/script&gt;</title><updated>2012-01-07T00:00:00-08:00</updated><author><name>Yuya Takeyama</name></author><content type="html">&lt;p&gt;今まで書いて来た &lt;a href='http://blog.yuyat.jp/'&gt;Born Too Late&lt;/a&gt; の住み分けとしては, あっちがいろいろ調べてからまとめる用, こっちはもっと殴り書いていく感じにしたい.&lt;/p&gt;&lt;div class='highlight'&gt;&lt;pre&gt;&lt;code class='ruby'&gt;&lt;span class='lineno'&gt;1&lt;/span&gt; &lt;span class='k'&gt;class&lt;/span&gt; &lt;span class='nc'&gt;Foo&lt;/span&gt;&lt;span class='lineno'&gt;2&lt;/span&gt;   &lt;span class='k'&gt;def&lt;/span&gt; &lt;span class='nf'&gt;bar&lt;/span&gt;&lt;span class='lineno'&gt;3&lt;/span&gt;     &lt;span class='ss'&gt;:baz&lt;/span&gt;&lt;span class='lineno'&gt;4&lt;/span&gt;   &lt;span class='k'&gt;end&lt;/span&gt;&lt;span class='lineno'&gt;5&lt;/span&gt; &lt;span class='k'&gt;end&lt;/span&gt;&lt;/code&gt;&lt;/pre&gt;&lt;/div&gt;</content></entry></feed>'''
        cleaner = Cleaner(comments=True, javascript=True, scripts=True,
            safe_attrs_only=True, page_structure=True, style=True, embedded=False,
            remove_tags=['body'])
        result = parse(feed, unix_timestamp=True, clean_html=cleaner)
        self.assertTrue('bozo_exception' not in result, str(result))
        for e in result.entries:
            self.assertTrue('alert(1)' not in e.title, e.title)
            self.assertTrue(not e.title.startswith('<p>'), e.title)

class NoneTypeNoStrip(TestCase):
    def test_nonetype_no_strip_regression(self):
        """This tests for a bug in 0.1.6 where the strip_outer_tag function
        would be called on None and raise an exception."""
        feed = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Instapaper: Starred</title><link>http://www.instapaper.com/starred</link><description></description><item><title>Toronto News: Flipped Junction homes taken on a wild real estate ride ending in fraud allegations - thestar.com</title><link>http://www.thestar.com/news/article/1111810--flipped-junction-homes-taken-on-a-wild-real-estate-ride-ending-in-fraud-allegations</link><description></description><pubDate>Sat, 07 Jan 2012 18:46:18 EST</pubDate></item></channel></rss>"""
        self.assertTrue(parse(feed).feed.title == "Instapaper: Starred")

class InvalidEntityRecovery(TestCase):
    def test_invalid_entity_recovery(self):
        feed = """<?xml version="1.0"?><rss xmlns:itunes="http://www.itunes.com/DTDs/Podcast-1.0.dtd" version="2.0"><channel><title>Faith Promise Church Podcast</title><description>Weekly message Podcast from Faith Promise Church.  Faith Promise church is an exciting church located in Knoxville, Tennessee. For information about the church, please visit our website at faithpromise.org.  We hope you enjoy and are blessed by our podcast.</description><link>http://faithpromise.org</link><language>en-us</language><item><title>T C & B (Taking Care of Busine</title><link>http://faithpromise.org/media/20111112-13.mp3</link><description>T C & B (Taking Care of Busine - Faith Promise Church Podcasts - Dr. Chris Stephens</description><pubDate>Mon, 14 Nov 2011 11:53:23 -0500</pubDate><enclosure url="http://faithpromise.org/media/20111112-13.mp3" length="36383475" type="audio/mpeg"/></item></channel></rss>"""
        self.assertTrue(parse(feed).bozo == 0)
        self.assertTrue(len(parse(feed).entries) == 1)

class SupportRssVersion2NoZero(TestCase):
    def test_support_rss_version_2_no_zero(self):
        feed = """<?xml version="1.0" encoding="UTF-8"?><rss version="2"><channel><title>Australian Canoeing</title><link>http://canoe.org.au</link><description>Latest News</description><language>en</language><ttl>480</ttl><pubDate>Sat, 21 Jan 2012 14:00:02 UTC</pubDate><item><title>Lifestart Kayak for Kids 2012</title><link>http://canoe.org.au/default.asp?Page=23196</link><description>Kayak for Kids is a unique paddling challenge on beautiful Sydney Harbour for everyone from beginner to serious kayaker.</description><enclosure url="http://canoe.org.au/site/canoeing/image/fullsize/35576.jpg" type="image/jpeg" /><pubDate>Thu, 19 Jan 2012 14:00:00 UTC</pubDate><guid>http://canoe.org.au/default.asp?Page=23196</guid></item></channel></rss>"""
        self.assertTrue(parse(feed).bozo == 0)
        self.assertTrue(len(parse(feed).entries) == 1)

class DetectCharsets(TestCase):
    def test_detect_charsets(self):
        feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel><title>"ismb2010" - Google Blogs�gning</title><link>http://www.google.com/search?hl=da&amp;lr=&amp;q=%22ismb2010%22&amp;ie=utf-8&amp;tbm=blg</link><description>S�geresultaterne &lt;b&gt;1&lt;/b&gt; - &lt;b&gt;10&lt;/b&gt; ud af ca. &lt;b&gt;59&lt;/b&gt; for &lt;b&gt;&amp;quot;ismb2010&amp;quot;&lt;/b&gt;.</description><opensearch:totalResults>59</opensearch:totalResults><opensearch:startIndex>1</opensearch:startIndex><opensearch:itemsPerPage>10</opensearch:itemsPerPage><item><title>Beyond DNA: &lt;b&gt;ISMB2010&lt;/b&gt; Boston</title><link>http://xiazheng.blogspot.com/2010/07/ismb2010-boston.html</link><description>ISMB of this year was held at Boston on July 10-14. I&amp;#39;m so happy to meet big guys in Bioinformatics whose papers I have ever read, especially Dr. Ratsch from MPI. One information this conference delivered this year is that &lt;b&gt;...&lt;/b&gt;</description><dc:publisher>Beyond DNA</dc:publisher><dc:creator>Zheng Xia</dc:creator><dc:date>Sat, 17 Jul 2010 13:56:00 GMT</dc:date></item></channel></rss>"""
        self.assertTrue(parse(feed, encoding=True).bozo == 0)
        self.assertTrue(len(parse(feed, encoding=True).entries) == 1)

class TextHeartParserError(TestCase):
    def test_text_heart_parser_error(self):
        """This is a placeholder test.  LXML punts because the title trips an
        unrecoverable parser error, and we have no way of cleaning it.  This
        would be a big issue, but FeedParser apparently cannot figure this out
        either as it breaks SAXParser."""
        import feedparser
        feed = """<?xml version="1.0" encoding="UTF-8"?><rss version="2"><channel><title>&lt;3</title><link>http://canoe.org.au</link><description>Latest News</description><language>en</language><ttl>480</ttl><pubDate>Sat, 21 Jan 2012 14:00:02 UTC</pubDate><item><title>&lt;3</title><link>http://canoe.org.au/default.asp?Page=23196</link><description>Kayak for Kids is a unique paddling challenge on beautiful Sydney Harbour for everyone from beginner to serious kayaker.</description><enclosure url="http://canoe.org.au/site/canoeing/image/fullsize/35576.jpg" type="image/jpeg" /><pubDate>Thu, 19 Jan 2012 14:00:00 UTC</pubDate><guid>http://canoe.org.au/default.asp?Page=23196</guid></item></channel></rss>"""
        self.assertTrue(parse(feed).bozo == 1)
        self.assertTrue(feedparser.parse(feed).bozo == 0)


class RdfRss090Support(TestCase):
    def test_rdf_rss_090_support(self):
        feed = """<?xml version="1.0" encoding="utf-8"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://my.netscape.com/rdf/simple/0.9/"><channel><title>heise online News</title><link>http://www.heise.de/newsticker/</link><description>Nachrichten nicht nur aus der Welt der Computer</description></channel><item><title>Am 6. Juni ist World IPv6 Launch Day</title><link>http://www.heise.de/newsticker/meldung/Am-6-Juni-ist-World-IPv6-Launch-Day-1415071.html/from/rss09</link><description>Am 6. Juni 2012 veranstaltet die Internet Society den IPv6 World Launch Day, an dem teilnehmende Internet Service Provider, Netzwerkhersteller und Service-Anbieter dauerhaft IPv6 schalten werden.</description></item></rdf:RDF>"""
        self.assertTrue(parse(feed).bozo == 0)
        self.assertTrue(len(parse(feed).entries) == 1)

class XmlnsSpaceSupport(TestCase):
    def test_xmlns_space_support(self):
        from os import path
        import ipdb; ipdb.set_trace();
        feed = open(path.join(path.dirname(__file__), "test-feeds/co.atom")).read()
        res = parse(feed)
        self.assertTrue(res.bozo == 0)
        self.assertTrue(len(res.entries) == 3)

