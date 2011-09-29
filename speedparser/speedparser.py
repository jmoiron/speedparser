#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""An attempt to be able to parse 80% of feeds that feedparser would parse
in about 1% of the time feedparser would parse them in.

LIMITATIONS:

 * result.feed.namespaces will only contain namespaces declaed on the
   root object, not those declared later in the file
 * general lack of support for many types of feeds
 * only things verified in test.py are guaranteed to be there;  many fields
   which were not considered important were skipped

"""

import re
import os
import sys
from lxml import etree, html
import feedparser

keymap = feedparser.FeedParserDict.keymap

xmlns_map = {
    'http://www.w3.org/2005/atom': 'atom10',
    'http://purl.org/rss/1.0/': 'rss10',
    'http://my.netscape.com/rdf/simple/0.9/': 'rss090',
}

def unicoder(txt, hint=None):
    if hint:
        try: return txt.decode(hint)
        except: return unicoder(txt)
    try:
        return txt.decode('utf-8')
    except:
        try: return txt.decode('latin-1')
        except: return txt

def first_text(xpath_result, default='', encoding='utf-8'):
    if xpath_result:
        return unicoder(xpath_result[0].text, encoding) or default
    return default

nsre = re.compile(r'xmlns=[\'"](.+?)[\'"]')
def strip_namespace(document):
    match = nsre.search(document)
    if match:
        return match.groups()[0], nsre.sub('', document)
    return None, document

class SpeedParserFeed(object):
    date_path = '''
        /rss/channel/lastBuildDate |
        /rss/channel/pubDate
    '''.strip()
    root_tag = 'rss'

    def __init__(self, root, namespaces={}, encoding='utf-8', type='rss20'):
        self.root = root
        self.nsmap = namespaces or root.nsmap
        self.encoding = encoding
        for k in self.nsmap.keys():
            if not k:
                # not allowed in xpath (grumble)
                del self.nsmap[k]
        feed = {}
        feed['title'], feed['subtitle'] = self.parse_title()
        feed['link'], feed['links'] = self.parse_links()
        feed['updated'], feed['updated_parsed'] = self.parse_updated()
        feed['generator'] = self.parse_generator()
        feed['language'] = self.parse_lang()
        # filter out crap we don't need
        for key in feed.keys():
            if feed[key] is None:
                del feed[key]
        self.feed = feed

    def xpath(self, query):
        try:
            return self.root.xpath(query, namespaces=self.nsmap)
        except:
            import traceback
            traceback.print_exc()

    def rq(self, query):
        return '/%s%s' % (self.root_tag, query)

    def parse_title(self):
        title = first_text(self.xpath(self.rq('/channel/title')))
        subtitle = first_text(self.xpath(self.rq('/channel/description')))
        return title, subtitle

    def parse_generator(self):
        return first_text(self.xpath('/rss/channel/generator'), None)

    def parse_lang(self):
        return first_text(self.xpath('/rss/channel/language'), None)

    def parse_updated(self):
        updated = first_text(self.xpath(self.date_path), None)
        updated_parsed = feedparser._parse_date(updated)
        return updated, updated_parsed

    def parse_links(self):
        elems = self.xpath(self.rq('/channel/*[local-name()="link"]'))
        link = ''
        links = []
        for e in elems:
            if e.tag == 'link':
                link = e.text
            else:
                links.append(e.attrib)
        return link, links

    def feed_dict(self):
        return self.feed

class SpeedParserRdf(SpeedParserFeed):
    root_tag = '/rdf:RDF'
    date_path = '''/rdf:RDF/channel/*[local-name()="date"]'''

    def __init__(self, root, namespaces={}, encoding='utf-8', type='rss20'):
        if None in namespaces:
            namespaces['rdf'] = namespaces[None]
            del namespaces[None]
        super(SpeedParserRdf, self).__init__(root, namespaces, type)

    def parse_lang(self):
        langkey = [k for k in self.root.keys() if k.endswith('lang')]
        if langkey:
            return self.root.attrib[langkey[0]]
        return super(SpeedParserRdf, self).parse_lang()

class SpeedParserAtom(SpeedParserFeed):
    root_tag = '/feed'
    date_path = '/feed/updated'

    def parse_title(self):
        title = first_text(self.xpath('/feed/title'))
        subtitle = first_text(self.xpath('/feed/subtitle'))
        return title, subtitle

    def parse_generator(self):
        return first_text(self.xpath('/feed/generator'))

    def parse_links(self):
        id = first_text(self.xpath('/feed/id'))
        elems = self.xpath('/feed/link')
        link = ''
        links = []
        for e in elems:
            links.append(e.attrib)
            if e.attrib.get('rel', '') == 'alternate':
                link = e.attrib['href']
        if id and not link:
            link = id
        return link, links

class SpeedParser(object):
    def __init__(self, content):
        self.xmlns, content = strip_namespace(content)
        tree = etree.fromstring(content)
        if isinstance(tree, etree._ElementTree):
            self.tree = tree
            self.root = tree.getroot()
        else:
            self.tree = tree.getroottree()
            self.root = tree
        self.encoding = self.parse_encoding()
        self.version = self.parse_version()
        self.namespaces = self.parse_namespaces()
        self.feed = self.parse_feed(self.version, self.encoding)

    def parse_version(self):
        r = self.root
        vers = 'unk'
        if self.xmlns and self.xmlns.lower() in xmlns_map:
            return xmlns_map[self.xmlns.lower()]
        elif self.xmlns:
            vers = self.xmlns.split('/')[-2].replace('.', '')
        if r.attrib.get('version', None):
            vers = r.attrib['version'].replace('.', '')
        tag = r.tag.split('}')[-1].lower()
        if tag in ('rss', 'rdf'):
            tag = 'rss'
        if tag in ('feed'):
            tag = 'atom'
        return '%s%s' % (tag, vers)

    def parse_namespaces(self):
        nsmap = self.root.nsmap.copy()
        for key in nsmap.keys():
            if key is None:
                nsmap[''] = nsmap[key]
                del nsmap[key]
                break
        return nsmap

    def parse_encoding(self):
        return self.tree.docinfo.encoding.lower()

    def parse_feed(self, version, encoding):
        if version == 'rss20':
            return SpeedParserFeed(self.root, encoding=encoding).feed_dict()
        if version == 'rss10':
            return SpeedParserRdf(self.root, namespaces=self.namespaces, encoding=encoding).feed_dict()
        if version == 'atom10':
            return SpeedParserAtom(self.root, namespaces=self.namespaces, encoding=encoding).feed_dict()
        return {}

    def update(self, result):
        if self.version:
            result['version'] = self.version
        if self.namespaces:
            result['namespaces'] = self.namespaces
        if self.feed:
            result.feed.update(self.feed)
        if self.encoding:
            result['encoding'] = self.encoding


def parse(document):
    result = feedparser.FeedParserDict()
    result['feed'] = feedparser.FeedParserDict()
    result['entries'] = []
    result['bozo'] = 0
    try:
        parser = SpeedParser(document)
        parser.update(result)
    except Exception, e:
        result['bozo'] = 1
        result['bozo_exception'] = e
        import traceback
        traceback.print_exc()
    return result



