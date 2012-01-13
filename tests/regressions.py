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

    def test_nonetype_no_strip_regression(self):
        """This tests for a bug in 0.1.6 where the strip_outer_tag function
        would be called on None and raise an exception."""
        feed = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Instapaper: Starred</title><link>http://www.instapaper.com/starred</link><description></description><item><title>Toronto News: Flipped Junction homes taken on a wild real estate ride ending in fraud allegations - thestar.com</title><link>http://www.thestar.com/news/article/1111810--flipped-junction-homes-taken-on-a-wild-real-estate-ride-ending-in-fraud-allegations</link><description></description><pubDate>Sat, 07 Jan 2012 18:46:18 EST</pubDate></item></channel></rss>"""
        self.assertTrue(parse(feed).feed.title == "Instapaper: Starred")

