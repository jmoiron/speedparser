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

